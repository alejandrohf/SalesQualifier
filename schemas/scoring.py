"""Schemas relacionados con el resultado determinista del motor de scoring."""

from __future__ import annotations

from typing import Dict

from pydantic import Field, confloat

from .common import AppBaseModel, QualificationLevel, RecommendedAction


class ScoringSummary(AppBaseModel):
    """Resumen del resultado final calculado por el motor de scoring determinista."""
    base_total_score: confloat(ge=0.0, le=10.0)
    total_score: confloat(ge=0.0, le=10.0)

    qualification_level: QualificationLevel
    recommended_action: RecommendedAction

    # Ajustes estratégicos aplicados sobre la puntuación base.
    adjustments: Dict[str, float] = Field(default_factory=dict)

    # Indica si la oportunidad presenta un riesgo crítico.
    has_critical_risk: bool = False