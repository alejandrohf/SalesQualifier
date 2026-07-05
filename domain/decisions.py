# domain/decisions.py
"""
Decisiones deterministas separadas para reutilización.

Nota: En tu scoring.py ya existen determine_qualification_level y
determine_recommended_action. Este módulo es útil si quieres centralizar
políticas y evitar duplicidad en el futuro.

Si decides centralizar, en scoring.py podrías importar estas funciones
en lugar de redefinirlas.
"""

from __future__ import annotations

from typing import Literal


QualificationLevel = Literal["high", "medium", "low"]
RecommendedAction = Literal["invest_pre_sales", "request_more_info", "do_not_prioritize"]

THRESHOLDS = {
    "high": 8.0,
    "medium": 6.0,
}


def determine_qualification_level(total_score: float) -> QualificationLevel:
    """Clasifica una oportunidad en high, medium o low según su score total."""
    if total_score >= THRESHOLDS["high"]:
        return "high"
    if total_score >= THRESHOLDS["medium"]:
        return "medium"
    return "low"


def determine_recommended_action(
    qualification_level: QualificationLevel,
    has_critical_risk: bool = False,
) -> RecommendedAction:
    """Propone la acción comercial a partir del nivel de cualificación y del riesgo crítico."""
    if qualification_level == "high" and not has_critical_risk:
        return "invest_pre_sales"
    if qualification_level == "medium":
        return "request_more_info"
    return "do_not_prioritize"