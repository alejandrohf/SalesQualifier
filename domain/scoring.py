"""Motor de scoring determinista para oportunidades evaluadas con MEDDICC.

Este módulo valida las puntuaciones por dimensión, calcula la nota final y
aplica ajustes estratégicos de forma trazable y testeable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Tuple


# ----------------------------
# Configuración de scoring
# ----------------------------

Dimension = Literal[
    "metrics",
    "economic_buyer",
    "decision_criteria",
    "decision_process",
    "identify_pain",
    "champion",
    "competition",
]

QualificationLevel = Literal["high", "medium", "low"]
RecommendedAction = Literal["invest_pre_sales", "request_more_info", "do_not_prioritize"]

MAX_SCORES: Dict[Dimension, float] = {
    "metrics": 2.0,
    "economic_buyer": 2.0,
    "decision_criteria": 1.5,
    "decision_process": 1.5,
    "identify_pain": 1.5,
    "champion": 1.0,
    "competition": 0.5,
}

THRESHOLDS = {
    "high": 8.0,
    "medium": 6.0,
}

# Ajustes estratégicos aplicados sobre la puntuación base.
ADJUSTMENTS = {
    "new_client_no_strong_champion": -0.5,   # Nuevo cliente sin champion fuerte
    "fixed_price_without_scope": -0.5,       # Fixed price sin scope definido
    "rfp_no_access_to_economic_buyer": -1.0, # RFP sin acceso al decisor económico
    "strategic_vertical": 0.5,               # Vertical estratégica
    "references_bonus": 0.0,                 # Bonus por referencias encontradas (valor dinámico)
}


# ----------------------------
# Excepciones
# ----------------------------

class ScoringError(ValueError):
    """Error de validación de scoring."""


# ----------------------------
# Flags de negocio (inputs del ajuste)
# ----------------------------

@dataclass(frozen=True)
class StrategicFlags:
    """Indicadores de negocio que modifican el resultado base del scoring."""
    # Penalizaciones
    new_client_no_strong_champion: bool = False
    fixed_price_without_scope: bool = False
    rfp_no_access_to_economic_buyer: bool = False

    # Bonus
    strategic_vertical: bool = False


# ----------------------------
# Validación y scoring base
# ----------------------------

def validate_dimension_scores(dimension_scores: Dict[Dimension, float]) -> None:
    """
    Valida que:
    - Todas las dimensiones existan.
    - El score de cada dimensión esté dentro de rango.
    """
    # 1) Validar dimensiones extra/desconocidas
    unknown = set(dimension_scores.keys()) - set(MAX_SCORES.keys())
    if unknown:
        raise ScoringError(f"Dimensiones desconocidas: {sorted(unknown)}")

    # 2) Validar que estén todas las dimensiones esperadas.
    missing = set(MAX_SCORES.keys()) - set(dimension_scores.keys())
    if missing:
        raise ScoringError(f"Faltan dimensiones: {sorted(missing)}")

    # 3) Validar rangos
    for dim, score in dimension_scores.items():
        max_allowed = MAX_SCORES[dim]
        if score < 0.0 or score > max_allowed:
            raise ScoringError(
                f"Score inválido para '{dim}'. Valor: {score}. Máximo permitido: {max_allowed}"
            )


def calculate_total_score(dimension_scores: Dict[Dimension, float]) -> float:
    """Suma las puntuaciones por dimensión y devuelve la nota base sobre diez."""
    validate_dimension_scores(dimension_scores)
    return round(sum(dimension_scores.values()), 2)


def determine_qualification_level(total_score: float) -> QualificationLevel:
    """Determina el nivel de cualificación asociado a la puntuación final."""
    if total_score >= THRESHOLDS["high"]:
        return "high"
    if total_score >= THRESHOLDS["medium"]:
        return "medium"
    return "low"


# ----------------------------
# Ajustes estratégicos
# ----------------------------

def apply_strategic_adjustments(
    base_total_score: float,
    flags: StrategicFlags,
) -> Tuple[float, Dict[str, float]]:
    """Aplica ajustes estratégicos al score base y devuelve la nota ajustada con su desglose."""
    breakdown: Dict[str, float] = {}
    adjustment_sum = 0.0

    if flags.new_client_no_strong_champion:
        v = ADJUSTMENTS["new_client_no_strong_champion"]
        breakdown["new_client_no_strong_champion"] = v
        adjustment_sum += v

    if flags.fixed_price_without_scope:
        v = ADJUSTMENTS["fixed_price_without_scope"]
        breakdown["fixed_price_without_scope"] = v
        adjustment_sum += v

    if flags.rfp_no_access_to_economic_buyer:
        v = ADJUSTMENTS["rfp_no_access_to_economic_buyer"]
        breakdown["rfp_no_access_to_economic_buyer"] = v
        adjustment_sum += v

    if flags.strategic_vertical:
        v = ADJUSTMENTS["strategic_vertical"]
        breakdown["strategic_vertical"] = v
        adjustment_sum += v

    adjusted = round(base_total_score + adjustment_sum, 2)

    # Limita el resultado al rango valido de la escala.
    adjusted = max(0.0, min(10.0, adjusted))
    return adjusted, breakdown


# ----------------------------
# Acción recomendada
# ----------------------------

def determine_recommended_action(
    qualification_level: QualificationLevel,
    has_critical_risk: bool = False,
) -> RecommendedAction:
    """Selecciona la acción comercial recomendada a partir del nivel y del riesgo crítico."""
    if qualification_level == "high" and not has_critical_risk:
        return "invest_pre_sales"
    if qualification_level == "medium":
        return "request_more_info"
    return "do_not_prioritize"


# ----------------------------
# Función principal utilizada por el supervisor del workflow.
# ----------------------------

def build_scoring_summary(
    dimension_scores: Dict[Dimension, float],
    flags: StrategicFlags | None = None,
    has_critical_risk: bool = False,
    reference_bonus: float = 0.0,
) -> Dict[str, object]:
    """Construye el resumen final del scoring listo para su serialización y consumo por la API."""
    flags = flags or StrategicFlags()

    base_total = calculate_total_score(dimension_scores)
    adjusted_total, adjustments_breakdown = apply_strategic_adjustments(base_total, flags)

    # Calcula un bonus acotado según el número y la calidad de las referencias recuperadas.
    reference_bonus = max(0.0, min(0.5, round(float(reference_bonus), 2)))
    if reference_bonus > 0:
        adjustments_breakdown["references_bonus"] = reference_bonus
        adjusted_total = round(min(10.0, adjusted_total + reference_bonus), 2)
                               
    level = determine_qualification_level(adjusted_total)
    action = determine_recommended_action(level, has_critical_risk=has_critical_risk)

    return {
        "base_total_score": base_total,
        "total_score": adjusted_total,
        "qualification_level": level,
        "recommended_action": action,
        "adjustments": adjustments_breakdown,
    }