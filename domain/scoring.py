# domain/scoring.py
"""
Scoring determinista para oportunidades cualificadas con MEDDICC.
El motor matemático y de reglas que transforma el análisis MEDDICC en score final y recomendación.

Objetivos:
- Validar rangos por dimensión (evitar scores inválidos del LLM).
- Calcular total_score (0-10) y nivel de cualificación.
- Aplicar ajustes estratégicos (Plain Concepts) de forma trazable y testeable.

Nota:
- Este módulo NO depende de LangChain, FastAPI ni Streamlit.
- Es 100% determinista y fácil de testear con pytest.
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

# Ajustes estratégicos (Plain Concepts)
ADJUSTMENTS = {
    "new_client_no_strong_champion": -0.5,   # Nuevo cliente sin champion fuerte
    "fixed_price_without_scope": -0.5,       # Fixed price sin scope definido
    "rfp_no_access_to_economic_buyer": -1.0, # RFP sin acceso a EB
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
    """
    Flags booleanos para ajustes estratégicos.
    Se derivan del input de la oportunidad + análisis MEDDICC.
    """
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

    # 2) Validar que estén todas (opcional, pero recomendable)
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
    """
    Suma scores por dimensión y devuelve total (0–10) sin ajustes estratégicos.
    """
    validate_dimension_scores(dimension_scores)
    return round(sum(dimension_scores.values()), 2)


def determine_qualification_level(total_score: float) -> QualificationLevel:
    """
    Determina nivel de cualificación según thresholds.
    """
    if total_score >= THRESHOLDS["high"]:
        return "high"
    if total_score >= THRESHOLDS["medium"]:
        return "medium"
    return "low"


# ----------------------------
# Ajustes estratégicos (Plain Concepts)
# ----------------------------

def apply_strategic_adjustments(
    base_total_score: float,
    flags: StrategicFlags,
) -> Tuple[float, Dict[str, float]]:
    """
    Aplica ajustes estratégicos al score base.
    Devuelve:
      - adjusted_score (clamped 0–10)
      - breakdown de ajustes aplicados (para auditoría y explicabilidad)
    """
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

    # Clamp a [0, 10]
    adjusted = max(0.0, min(10.0, adjusted))
    return adjusted, breakdown


# ----------------------------
# Acción recomendada
# ----------------------------

def determine_recommended_action(
    qualification_level: QualificationLevel,
    has_critical_risk: bool = False,
) -> RecommendedAction:
    """
    Recomendación operativa:
    - high sin riesgos críticos -> invertir preventa
    - medium -> pedir más info (discovery) antes de comprometer recursos
    - low o high con riesgo crítico -> no priorizar (o pedir info si quieres ser más laxo)
    """
    if qualification_level == "high" and not has_critical_risk:
        return "invest_pre_sales"
    if qualification_level == "medium":
        return "request_more_info"
    return "do_not_prioritize"


# ----------------------------
# API principal (para supervisor/workflow)
# ----------------------------

def build_scoring_summary(
    dimension_scores: Dict[Dimension, float],
    flags: StrategicFlags | None = None,
    has_critical_risk: bool = False,
    reference_bonus: float = 0.0,
) -> Dict[str, object]:
    """
    Calcula:
      - base_total_score
      - adjusted_total_score (si flags)
      - qualification_level sobre adjusted_total_score
      - recommended_action
      - breakdown de ajustes (para auditoría)

    Devuelve un dict listo para mapear a tu Summary Pydantic.
    """
    flags = flags or StrategicFlags()

    base_total = calculate_total_score(dimension_scores)
    adjusted_total, adjustments_breakdown = apply_strategic_adjustments(base_total, flags)

    # clamp reference bonus [0..0.5] y lo aplicamos
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