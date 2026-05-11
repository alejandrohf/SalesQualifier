"""Módulo `tools/pdf_loader.py` de la plataforma Sales Qualification Agent."""

# tools/pdf_loader.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass(frozen=True)
class Chunk:
    """Define `Chunk` dentro de este modulo."""
    index: int
    text: str


def extract_text_from_pdf(pdf_path: str, max_pages: Optional[int] = None) -> str:
    """Ejecuta `extract_text_from_pdf` dentro de este modulo."""
    reader = PdfReader(pdf_path)
    texts: list[str] = []

    pages = reader.pages[:max_pages] if max_pages else reader.pages
    for p in pages:
        t = p.extract_text() or ""
        t = t.strip()
        if t:
            texts.append(t)

    return "\n\n".join(texts)


def chunk_text(text: str, chunk_size: int = 900, chunk_overlap: int = 120) -> List[Chunk]:
    """Ejecuta `chunk_text` dentro de este modulo."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    return [Chunk(i, c.strip()) for i, c in enumerate(chunks) if c.strip()]