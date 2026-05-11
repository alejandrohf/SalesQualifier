# domain/__init__.py
"""
Domain layer (lógica de negocio determinista).

Esta capa NO depende de:
- LangChain / LLM
- Streamlit
- FastAPI

Contiene reglas, decisiones y scoring testeables con pytest.
"""

from .scoring import (
    ADJUSTMENTS,
    MAX_SCORES,
    THRESHOLDS,
    Dimension,
    QualificationLevel,
    RecommendedAction,
    ScoringError,
    StrategicFlags,
    apply_strategic_adjustments,
    build_scoring_summary,
    calculate_total_score,
    determine_qualification_level,
    determine_recommended_action,
    validate_dimension_scores,
)

from .rules import (
    derive_has_critical_risk,
    derive_strategic_flags,
)

__all__ = [
    "ADJUSTMENTS",
    "MAX_SCORES",
    "THRESHOLDS",
    "Dimension",
    "QualificationLevel",
    "RecommendedAction",
    "ScoringError",
    "StrategicFlags",
    "validate_dimension_scores",
    "calculate_total_score",
    "determine_qualification_level",
    "determine_recommended_action",
    "apply_strategic_adjustments",
    "build_scoring_summary",
    "derive_strategic_flags",
    "derive_has_critical_risk",
]