"""Módulo `schemas/reference_match.py` de la plataforma Sales Qualification Agent."""

# schemas/reference_match.py
from __future__ import annotations

from typing import List
from uuid import UUID

from pydantic import Field

from schemas.common import AppBaseModel


class ReferenceMatch(AppBaseModel):
    """Define `ReferenceMatch` dentro de este modulo."""
    reference_id: UUID
    title: str
    customer: str
    similarity: float = Field(..., ge=0.0, le=1.0)

    # “RAG payload” útil al comercial
    best_chunk_snippet: str = Field(..., max_length=1200)
    why_similar: List[str] = Field(default_factory=list, max_length=3)

    # link (filesystem-served via API)
    document_url: str


class ReferenceMatchesReport(AppBaseModel):
    """Define `ReferenceMatchesReport` dentro de este modulo."""
    query_used: str
    top_k: int = 5
    matches: List[ReferenceMatch] = Field(default_factory=list)

    # Para scoring determinista (bonus)
    bonus_applied: float = Field(0.0, ge=0.0, le=0.5)
