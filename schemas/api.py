"""Módulo `schemas/api.py` de la plataforma Sales Qualification Agent."""

# schemas/api.py
from __future__ import annotations

from typing import Optional
from pydantic import Field

from .common import AppBaseModel, Metadata
from .opportunity import OpportunityInput
from .meddicc import MeddiccReport
from .scoring import ScoringSummary
from .reference_match import ReferenceMatchesReport

class QualifyRequest(AppBaseModel):
    """Define `QualifyRequest` dentro de este modulo."""
    opportunity: OpportunityInput
    metadata: Metadata = Field(default_factory=Metadata)

class QualifyResponse(AppBaseModel):
    """Define `QualifyResponse` dentro de este modulo."""
    opportunity: OpportunityInput
    meddicc_report: MeddiccReport| None = None
    scoring: ScoringSummary
    reference_matches: Optional[ReferenceMatchesReport] = None
    metadata: Metadata = Field(default_factory=Metadata)

class ErrorResponse(AppBaseModel):
    """Define `ErrorResponse` dentro de este modulo."""
    error: str
    detail: Optional[str] = None
    metadata: Metadata = Field(default_factory=Metadata)
