"""Endpoints para gestionar el catálogo de referencias y su búsqueda semántica."""

# interfaces/api/routes_references.py
from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from schemas.reference import CustomerReferenceCreate, CustomerReferenceOut, Industry, Area, Cloud, Size
from interfaces.api.auth_dependencies import require_sales_or_engineering
from tools.vectorstore import (
    create_reference,
    get_reference,
    list_references,
    reindex_reference,
    replace_reference_pdf,
    update_reference_metadata,
    delete_reference,
    search_references,
    ReferenceSearchFilters,
)

router = APIRouter(prefix="/api/references", tags=["references"])


@router.get("", response_model=list[CustomerReferenceOut])
def api_list_references(limit: int = 50, offset: int = 0, _: Dict[str, Any] = Depends(require_sales_or_engineering())):
    """Devuelve el catálogo paginado de referencias corporativas."""
    refs = list_references(limit=limit, offset=offset)
    return [
        CustomerReferenceOut(
            id=UUID(str(r.id)),
            title=r.title,
            customer=r.customer,
            industry=Industry(r.industry),
            area=Area(r.area),
            cloud=Cloud(r.cloud),
            size=Size(r.size),
            document_path=r.document_path,
            document_version=r.document_version,
            indexed_at=r.indexed_at,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in refs
    ]


@router.post("", response_model=dict)
async def api_create_reference(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    customer: str = Form(...),
    industry: Industry = Form(...),
    area: Area = Form(...),
    cloud: Cloud = Form(...),
    size: Size = Form(...),
    document: UploadFile = File(...),
    _: Dict[str, Any] = Depends(require_sales_or_engineering()),
):
    """Crea una referencia nueva y programa su indexación vectorial en segundo plano."""
    pdf = await document.read()
    meta = CustomerReferenceCreate(
        title=title,
        customer=customer,
        industry=industry,
        area=area,
        cloud=cloud,
        size=size,
    )
    ref_id = create_reference(meta, pdf)

    # Index async
    background_tasks.add_task(reindex_reference, ref_id)

    return {"status": "created", "reference_id": str(ref_id), "indexing": "scheduled"}


@router.post("/{reference_id}/reindex", response_model=dict)
def api_reindex_reference(reference_id: UUID, background_tasks: BackgroundTasks, _: Dict[str, Any] = Depends(require_sales_or_engineering())):
    """Relanza la indexación semántica de una referencia existente."""
    try:
        # programa la reindexación async para no bloquear API
        background_tasks.add_task(reindex_reference, reference_id)
        return {"status": "scheduled", "reference_id": str(reference_id)}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/search", response_model=dict)
def api_search_references(payload: Dict[str, Any], _: Dict[str, Any] = Depends(require_sales_or_engineering())):
    """Ejecuta una búsqueda semántica en el repositorio de referencias."""
    query = (payload.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=422, detail="Missing 'query'")

    filters = payload.get("filters") or {}
    f = ReferenceSearchFilters(
        industry=filters.get("industry"),
        area=filters.get("area"),
        cloud=filters.get("cloud"),
        size=filters.get("size"),
    )

    hits = search_references(query=query, top_k=int(payload.get("top_k", 5)), filters=f)
    return {
        "query": query,
        "hits": [
            {
                "reference_id": str(h.reference_id),
                "title": h.title,
                "customer": h.customer,
                "similarity": h.similarity,
                "chunk_text": h.chunk_text[:1200],
                "document_url": f"/api/references/{h.reference_id}/download",
            }
            for h in hits
        ],
    }


@router.put("/{reference_id}", response_model=dict)
def api_update_reference(reference_id: UUID, patch: Dict[str, Any], _: Dict[str, Any] = Depends(require_sales_or_engineering())):
    """Actualiza la metadata de una referencia sin sustituir el documento."""
    try:
        update_reference_metadata(reference_id, patch)
        return {"status": "updated", "reference_id": str(reference_id)}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{reference_id}/document", response_model=dict)
async def api_replace_reference_document(reference_id: UUID, background_tasks: BackgroundTasks, document: UploadFile = File(...), _: Dict[str, Any] = Depends(require_sales_or_engineering())):
    """Sustituye el PDF de una referencia y fuerza su futura reindexación."""
    pdf = await document.read()
    try:
        replace_reference_pdf(reference_id, pdf)
        background_tasks.add_task(reindex_reference, reference_id)
        return {"status": "document_replaced", "reference_id": str(reference_id), "indexing": "scheduled"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{reference_id}/download")
def api_download_reference(reference_id: UUID, _: Dict[str, Any] = Depends(require_sales_or_engineering())):
    """Sirve el documento PDF asociado a una referencia concreta."""
    try:
        ref = get_reference(reference_id)
        return FileResponse(ref.document_path, media_type="application/pdf", filename=f"{reference_id}.pdf")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{reference_id}", response_model=dict)
def api_delete_reference(reference_id: UUID, _: Dict[str, Any] = Depends(require_sales_or_engineering())):
    """Elimina una referencia y sus embeddings asociados."""
    try:
        delete_reference(reference_id)
        return {"status": "deleted", "reference_id": str(reference_id)}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
