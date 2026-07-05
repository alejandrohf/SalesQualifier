"""Schemas del resultado de recuperación semántica de referencias similares."""

from __future__ import annotations

from typing import List
from uuid import UUID

from pydantic import Field

from schemas.common import AppBaseModel


class ReferenceMatch(AppBaseModel):
    """Referencia recuperada por similitud semántica para apoyar la cualificación."""
    reference_id: UUID
    title: str
    customer: str
    similarity: float = Field(..., ge=0.0, le=1.0)

    best_chunk_snippet: str = Field(..., max_length=1200)
    why_similar: List[str] = Field(default_factory=list, max_length=3)
    document_url: str


class ReferenceMatchesReport(AppBaseModel):
    """Conjunto de referencias sugeridas y bonus aplicado al scoring por reutilización de conocimiento."""
    query_used: str
    top_k: int = 5
    matches: List[ReferenceMatch] = Field(default_factory=list)
    bonus_applied: float = Field(0.0, ge=0.0, le=0.5)
