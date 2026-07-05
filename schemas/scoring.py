"""Schemas relacionados con el resultado determinista del motor de scoring."""

# schemas/scoring.py
from __future__ import annotations

from typing import Dict

from pydantic import Field, confloat

from .common import AppBaseModel, QualificationLevel, RecommendedAction


class ScoringSummary(AppBaseModel):
    """
    Resultado determinista (fuente de verdad) calculado por domain/scoring.py
    """
    base_total_score: confloat(ge=0.0, le=10.0)
    total_score: confloat(ge=0.0, le=10.0)

    qualification_level: QualificationLevel
    recommended_action: RecommendedAction

    # desglose de ajustes aplicados
    adjustments: Dict[str, float] = Field(default_factory=dict)

    # opcional: para auditoría/debug
    has_critical_risk: bool = False