"""Esquemas de entrada y salida utilizados por los endpoints de la API para el proceso de Qualify"""

from __future__ import annotations

from typing import Optional
from pydantic import Field

from .common import AppBaseModel, Metadata
from .opportunity import OpportunityInput
from .meddicc import MeddiccReport
from .scoring import ScoringSummary
from .reference_match import ReferenceMatchesReport

class QualifyRequest(AppBaseModel):
    """Payload de entrada para lanzar la cualificación completa de una oportunidad."""
    opportunity: OpportunityInput
    metadata: Metadata = Field(default_factory=Metadata)

class QualifyResponse(AppBaseModel):
    """Respuesta consolidada del proceso de cualificación con análisis, scoring y referencias."""
    opportunity: OpportunityInput
    meddicc_report: MeddiccReport | None = None
    scoring: ScoringSummary
    reference_matches: Optional[ReferenceMatchesReport] = None
    metadata: Metadata = Field(default_factory=Metadata)

class ErrorResponse(AppBaseModel):
    """Formato homogéneo de error expuesto por la API."""
    error: str
    detail: Optional[str] = None
    metadata: Metadata = Field(default_factory=Metadata)
