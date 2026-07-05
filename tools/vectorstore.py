"""Gestión del repositorio vectorial de referencias sobre PostgreSQL y pgvector.

Incluye alta de referencias, reindexación, persistencia de embeddings y
búsqueda semántica usada por el workflow y por la API.
"""

# tools/vectorstore.py
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from langchain_openai import OpenAIEmbeddings

from infrastructure.db.session import SessionLocal
from infrastructure.db.models import CustomerReferenceORM, ReferenceEmbeddingORM

from schemas.reference import CustomerReferenceCreate
from tools.pdf_loader import extract_text_from_pdf, chunk_text


# -------------------------
# Config
# -------------------------

EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dims
DATA_DIR = os.getenv("REFERENCES_DATA_DIR", os.path.abspath("data/references"))

os.makedirs(DATA_DIR, exist_ok=True)

_embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)


# -------------------------
# Types
# -------------------------

@dataclass(frozen=True)
class ReferenceSearchFilters:
    """Filtros opcionales aplicables a la búsqueda de referencias semánticas."""
    industry: Optional[str] = None
    area: Optional[str] = None
    cloud: Optional[str] = None
    size: Optional[str] = None


@dataclass(frozen=True)
class ReferenceSearchHit:
    """Resultado elemental de una búsqueda vectorial sobre el catálogo de referencias."""
    reference_id: UUID
    title: str
    customer: str
    similarity: float
    chunk_text: str
    document_path: str


# -------------------------
# Helpers
# -------------------------

def _now():
    return datetime.now(timezone.utc)


def _pdf_path(reference_id: UUID, version: int = 1) -> str:
    # para MVP: un único fichero por id (si quieres versionado real, añade sufijo _v{version})
    return os.path.join(DATA_DIR, f"{reference_id}.pdf")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _get_db() -> Session:
    return SessionLocal()


# -------------------------
# CRUD: References (customer_references)
# -------------------------

def create_reference(meta: CustomerReferenceCreate, pdf_bytes: bytes) -> UUID:
    """
    1) Guarda PDF en filesystem
    2) INSERT en customer_references
    """
    ref_id = uuid4()
    path = _pdf_path(ref_id)

    with open(path, "wb") as f:
        f.write(pdf_bytes)

    with _get_db() as db:
        ref = CustomerReferenceORM(
            id=ref_id,
            title=meta.title,
            customer=meta.customer,
            industry=meta.industry.value if hasattr(meta.industry, "value") else str(meta.industry),
            area=meta.area.value if hasattr(meta.area, "value") else str(meta.area),
            cloud=meta.cloud.value if hasattr(meta.cloud, "value") else str(meta.cloud),
            size=meta.size.value if hasattr(meta.size, "value") else str(meta.size),
            document_path=path,
            document_version=1,
            indexed_at=None,
        )
        db.add(ref)
        db.commit()

    return ref_id


def get_reference(reference_id: UUID) -> CustomerReferenceORM:
    """Recupera una referencia concreta por su identificador."""
    with _get_db() as db:
        ref = db.get(CustomerReferenceORM, reference_id)
        if not ref:
            raise ValueError(f"Reference not found: {reference_id}")
        return ref


def list_references(limit: int = 50, offset: int = 0) -> List[CustomerReferenceORM]:
    """Lista referencias ordenadas por fecha de actualización."""
    with _get_db() as db:
        stmt = (
            select(CustomerReferenceORM)
            .order_by(CustomerReferenceORM.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(db.scalars(stmt).all())


def update_reference_metadata(reference_id: UUID, patch: Dict[str, Any]) -> None:
    """Actualiza los metadatos editables de una referencia existente."""
    allowed = {"title", "customer", "industry", "area", "cloud", "size"}
    patch = {k: v for k, v in patch.items() if k in allowed}

    with _get_db() as db:
        ref = db.get(CustomerReferenceORM, reference_id)
        if not ref:
            raise ValueError(f"Reference not found: {reference_id}")

        for k, v in patch.items():
            setattr(ref, k, v)

        ref.updated_at = _now()
        db.commit()


def replace_reference_pdf(reference_id: UUID, pdf_bytes: bytes) -> None:
    """
    Reemplaza documento y sube document_version.
    """
    with _get_db() as db:
        ref = db.get(CustomerReferenceORM, reference_id)
        if not ref:
            raise ValueError(f"Reference not found: {reference_id}")

        # sobrescribe pdf (MVP)
        with open(ref.document_path, "wb") as f:
            f.write(pdf_bytes)

        ref.document_version += 1
        ref.updated_at = _now()
        ref.indexed_at = None  # obligará a reindex
        db.commit()


def delete_reference(reference_id: UUID) -> None:
    """Elimina una referencia del catálogo y limpia su documento local si existe."""
    with _get_db() as db:
        ref = db.get(CustomerReferenceORM, reference_id)
        if not ref:
            raise ValueError(f"Reference not found: {reference_id}")

        # borra fichero
        try:
            if ref.document_path and os.path.exists(ref.document_path):
                os.remove(ref.document_path)
        except Exception:
            pass

        db.delete(ref)
        db.commit()


# -------------------------
# Indexación: reference_embeddings
# -------------------------

def reindex_reference(reference_id: UUID) -> None:
    """
    Background task:
      - Lee PDF
      - Chunking
      - Embeddings (1536)
      - Borra embeddings previos
      - Inserta embeddings nuevos
      - Actualiza indexed_at
    """
    with _get_db() as db:
        ref = db.get(CustomerReferenceORM, reference_id)
        if not ref:
            raise ValueError(f"Reference not found: {reference_id}")

        pdf_path = ref.document_path

    text = extract_text_from_pdf(pdf_path)
    chunks = chunk_text(text)

    if not chunks:
        # marca como "indexado" pero sin embeddings
        with _get_db() as db:
            ref2 = db.get(CustomerReferenceORM, reference_id)
            if ref2:
                ref2.indexed_at = _now()
                ref2.updated_at = _now()
                db.commit()
        return

    chunk_texts = [c.text for c in chunks]
    vectors = _embeddings.embed_documents(chunk_texts)

    with _get_db() as db:
        # 1) delete prev embeddings
        db.execute(delete(ReferenceEmbeddingORM).where(ReferenceEmbeddingORM.reference_id == reference_id))

        # 2) insert new
        for c, vec in zip(chunks, vectors):
            db.add(
                ReferenceEmbeddingORM(
                    reference_id=reference_id,
                    chunk_index=c.index,
                    chunk_text=c.text,
                    chunk_hash=_sha256(c.text),
                    token_count=None,
                    embedding=vec,
                )
            )

        # 3) update reference
        ref3 = db.get(CustomerReferenceORM, reference_id)
        if ref3:
            ref3.indexed_at = _now()
            ref3.updated_at = _now()

        db.commit()


# -------------------------
# Search: pgvector
# -------------------------

def search_references(
    *,
    query: str,
    top_k: int = 5,
    filters: Optional[ReferenceSearchFilters] = None,
) -> List[ReferenceSearchHit]:
    """
    Query → embedding → ANN over pgvector.
    similarity = 1 - cosine_distance
    """
    qvec = _embeddings.embed_query(query)

    with _get_db() as db:
        # cosine_distance: menor = más similar
        similarity_expr = (1 - ReferenceEmbeddingORM.embedding.cosine_distance(qvec)).label("similarity")

        stmt = (
            select(
                ReferenceEmbeddingORM.reference_id,
                ReferenceEmbeddingORM.chunk_text,
                similarity_expr,
                CustomerReferenceORM.title,
                CustomerReferenceORM.customer,
                CustomerReferenceORM.document_path,
            )
            .join(CustomerReferenceORM, CustomerReferenceORM.id == ReferenceEmbeddingORM.reference_id)
        )

        if filters:
            if filters.industry:
                stmt = stmt.where(CustomerReferenceORM.industry == filters.industry)
            if filters.area:
                stmt = stmt.where(CustomerReferenceORM.area == filters.area)
            if filters.cloud:
                stmt = stmt.where(CustomerReferenceORM.cloud == filters.cloud)
            if filters.size:
                stmt = stmt.where(CustomerReferenceORM.size == filters.size)

        stmt = stmt.order_by(ReferenceEmbeddingORM.embedding.cosine_distance(qvec)).limit(top_k)

        rows = db.execute(stmt).all()

    hits: List[ReferenceSearchHit] = []
    for reference_id, chunk_text_value, sim, title, customer, doc_path in rows:
        hits.append(
            ReferenceSearchHit(
                reference_id=reference_id,
                title=title,
                customer=customer,
                similarity=float(sim) if sim is not None else 0.0,
                chunk_text=chunk_text_value,
                document_path=doc_path,
            )
        )

    return hits


# -------------------------
# Tool wrapper (LangChain tool)
# -------------------------

from langchain.tools import tool  # keep at end to avoid import cycles


@tool
def vectorstore_search_references(query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Herramienta para agentes: consulta top_k referencias similares.
    filters opcional: {"industry": "...", "area": "...", "cloud": "...", "size": "..."}
    """
    f = None
    if filters:
        f = ReferenceSearchFilters(
            industry=filters.get("industry"),
            area=filters.get("area"),
            cloud=filters.get("cloud"),
            size=filters.get("size"),
        )

    hits = search_references(query=query, top_k=top_k, filters=f)

    return {
        "query": query,
        "top_k": top_k,
        "hits": [
            {
                "reference_id": str(h.reference_id),
                "title": h.title,
                "customer": h.customer,
                "similarity": float(h.similarity),
                "chunk_text": h.chunk_text,
                "document_path": h.document_path,
            }
            for h in hits
        ],
    }