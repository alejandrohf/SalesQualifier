"""Schemas del análisis MEDDICC y del contexto enriquecido del cliente."""

# schemas/meddicc.py
from __future__ import annotations

from typing import List, Optional

from pydantic import Field, conint, confloat

from .common import (
    AppBaseModel,
    ClientContextSource,
    QualificationLevel,
    RecommendedAction,
    Status,
)

class MeddiccDimension(AppBaseModel):
    """Resultado estructurado de una dimensión individual del análisis MEDDICC."""
    status: Status
    score: float = Field(..., ge=0.0)
    evidence: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    questions: List[str] = Field(default_factory=list)


class ClientContext(AppBaseModel):
    """Contexto del cliente combinado a partir del formulario y del enriquecimiento externo."""
    source: ClientContextSource
    client_name: str
    is_new_client: bool

    sector: Optional[str] = None
    company_summary: Optional[str] = None
    multinational: Optional[bool] = None
    employee_count: Optional[conint(ge=0)] = None
    revenue_info: Optional[str] = None
    notes: Optional[str] = None


class Meddicc(AppBaseModel):
    """Agrupa las siete dimensiones del framework MEDDICC para una oportunidad."""
    metrics: MeddiccDimension
    economic_buyer: MeddiccDimension
    decision_criteria: MeddiccDimension
    decision_process: MeddiccDimension
    identify_pain: MeddiccDimension
    champion: MeddiccDimension
    competition: MeddiccDimension


class MeddiccLLMSummary(AppBaseModel):
    """Resumen generado por el LLM antes del recálculo determinista del scoring."""
    total_score: confloat(ge=0.0, le=10.0)
    qualification_level: Optional[QualificationLevel] = None
    recommended_action: Optional[RecommendedAction] = None
    score_justification: Optional[str] = None
    critical_risks_top3: List[str] = Field(default_factory=list, max_length=3)
    next_steps: List[str] = Field(default_factory=list)


class MeddiccReport(AppBaseModel):
    """Informe completo del análisis MEDDICC, incluyendo contexto y resumen final."""
    client_context: ClientContext
    meddicc: Meddicc
    summary: MeddiccLLMSummary
