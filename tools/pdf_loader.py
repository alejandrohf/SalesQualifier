"""Extracción de texto y fragmentación de documentos PDF para indexación semántica."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass(frozen=True)
class Chunk:
    """Fragmento numerado de texto extraído de un documento para su posterior indexación."""
    index: int
    text: str


def extract_text_from_pdf(pdf_path: str, max_pages: Optional[int] = None) -> str:
    """Extrae el texto legible de un PDF, opcionalmente limitando el número de páginas."""
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
    """Divide un texto en fragmentos solapados usando un splitter basado en caracteres."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    return [Chunk(i, c.strip()) for i, c in enumerate(chunks) if c.strip()]
