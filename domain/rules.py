"""
Reglas deterministas para:
- Derivar StrategicFlags (penalizaciones/bonus) usados en scoring.py
- Derivar has_critical_risk para modular recommended_action

Estas reglas NO usan LLM. Se basan en:
- Input estructurado de la oportunidad (formulario)
- Resultado estructurado MEDDICC (JSON -> Pydantic)
"""

from __future__ import annotations

from typing import Any, Optional

from domain.scoring import StrategicFlags


# ------------------------------------------------------------------------------
# Accesores auxiliares
# ------------------------------------------------------------------------------

def _get(obj: Any, *paths: str, default: Any = None) -> Any:
    """
    Obtiene el primer atributo/clave existente en obj siguiendo paths alternativos.
    Soporta:
    - Pydantic models (atributos)
    - dicts (keys)
    """
    for p in paths:
        # dict
        if isinstance(obj, dict) and p in obj:
            return obj.get(p, default)

        # atributo
        if hasattr(obj, p):
            v = getattr(obj, p)
            return v if v is not None else default

    return default


def _norm_str(x: Any) -> str:
    return (str(x) if x is not None else "").strip().lower()


# ------------------------------------------------------------------------------
# Heurísticas MEDDICC deterministas (basadas en score/status)
# ------------------------------------------------------------------------------

def _is_strong_champion(meddicc_report: Any) -> bool:
    """
    Champion fuerte (heurística simple):
    - status complete + score >= 0.75
    o
    - score == 1.0
    """
    champ = _get(meddicc_report, "meddicc", default={}).champion if hasattr(_get(meddicc_report, "meddicc"), "champion") else _get(_get(meddicc_report, "meddicc", default={}), "champion", default={})
    status = _get(champ, "status", default="insufficient")
    score = float(_get(champ, "score", default=0.0) or 0.0)
    return (status == "complete" and score >= 0.75) or (score >= 1.0)


def _has_access_to_economic_buyer(meddicc_report: Any) -> bool:
    """
    Acceso mínimo al EB:
    - economic_buyer.status != insufficient
    - economic_buyer.score >= 1.0
    """
    eb = _get(meddicc_report, "meddicc", default={}).economic_buyer if hasattr(_get(meddicc_report, "meddicc"), "economic_buyer") else _get(_get(meddicc_report, "meddicc", default={}), "economic_buyer", default={})
    status = _get(eb, "status", default="insufficient")
    score = float(_get(eb, "score", default=0.0) or 0.0)
    return status != "insufficient" and score >= 1.0


# ------------------------------------------------------------------------------
# Heurísticas sobre el input de oportunidad (sin LLM)
# ------------------------------------------------------------------------------

def _is_new_client(opportunity: Any, meddicc_report: Optional[Any] = None) -> bool:
    """
    Detecta cliente nuevo.
    - Si opportunity trae is_new_client, úsalo.
    - Si no, intenta usar client_context.is_new_client del report MEDDICC.
    """
    v = _get(opportunity, "is_new_client", default=None)
    if isinstance(v, bool):
        return v

    if meddicc_report is not None:
        ctx = _get(meddicc_report, "client_context", default=None)
        v2 = _get(ctx, "is_new_client", default=None)
        if isinstance(v2, bool):
            return v2

    return False


def _collaboration_type(opportunity: Any) -> str:
    return _norm_str(_get(opportunity, "collaboration_type", "tipo_colaboracion", default=""))


def _is_rfp(opportunity: Any) -> bool:
    ct = _collaboration_type(opportunity)
    return ("rfp" in ct) or ("rfi" in ct) or ("licit" in ct) or ("tender" in ct)


def _is_fixed_price(opportunity: Any) -> bool:
    ct = _collaboration_type(opportunity)
    return ("fixed" in ct) or ("precio cerrado" in ct) or ("cerrado" in ct)


def _is_scope_defined(opportunity: Any) -> bool:
    """
    Heurística de 'scope definido' para evitar fixed-price con riesgo.
    Criterio:
    - descripción >= 80 chars
    - existe due_date o fecha objetivo
    - existe tamaño estimado
    """
    desc = _get(opportunity, "description", "client_request_description", "descripcion", default="")
    desc_ok = isinstance(desc, str) and len(desc.strip()) >= 80

    due = _get(opportunity, "due_date", "proposal_due_date", "fecha_presentacion", default=None)
    due_ok = due is not None

    size = _get(opportunity, "deal_size", "estimated_size", "tamano_estimado", default=None)
    size_ok = size is not None

    return bool(desc_ok and due_ok and size_ok)


def _is_strategic_vertical(opportunity: Any) -> bool:
    """Detecta si la oportunidad encaja en una vertical considerada estratégica por la organización.

    La clasificación actual se apoya en palabras clave del área principal y puede
    refinarse si la taxonomía comercial evoluciona.
    """
    area = _norm_str(_get(opportunity, "main_area", "area", "area_principal", default=""))
    strategic_markers = ("data", "ia", "ai", "analytics", "modern", "cloud", "agent", "snowflake", "databricks", "fabric", "copilot")
    return any(m in area for m in strategic_markers)


# ------------------------------------------------------------------------------
# Reglas públicas (API del dominio)
# ------------------------------------------------------------------------------

def derive_strategic_flags(opportunity: Any, meddicc_report: Any) -> StrategicFlags:
    """
    Deriva los StrategicFlags usados por domain/scoring.py:
    - new_client_no_strong_champion -> -0.5
    - fixed_price_without_scope -> -0.5
    - rfp_no_access_to_economic_buyer -> -1.0
    - strategic_vertical -> +0.5
    """
    new_client = _is_new_client(opportunity, meddicc_report)
    strong_champion = _is_strong_champion(meddicc_report)

    is_fixed = _is_fixed_price(opportunity)
    scope_defined = _is_scope_defined(opportunity)

    is_rfp = _is_rfp(opportunity)
    has_eb_access = _has_access_to_economic_buyer(meddicc_report)

    strategic_vertical = _is_strategic_vertical(opportunity)

    return StrategicFlags(
        new_client_no_strong_champion=bool(new_client and not strong_champion),
        fixed_price_without_scope=bool(is_fixed and not scope_defined),
        rfp_no_access_to_economic_buyer=bool(is_rfp and not has_eb_access),
        strategic_vertical=bool(strategic_vertical),
    )


def derive_has_critical_risk(opportunity: Any, meddicc_report: Any) -> bool:
    """
    Determina si existe un riesgo crítico que debería influir recommended_action.

    Regla operativa alineada con el motor de scoring:
    - decision_process insuficiente -> riesgo crítico
    - economic_buyer insuficiente -> riesgo crítico
    - RFP sin acceso a EB -> riesgo crítico
    - fixed price sin scope -> riesgo crítico

    Esta comprobación complementa las penalizaciones del scoring para evitar
    recomendaciones excesivamente optimistas cuando faltan condiciones críticas.
    """
    # decision_process insuficiente
    dp = _get(_get(meddicc_report, "meddicc", default={}), "decision_process", default={})
    dp_status = _get(dp, "status", default="insufficient")
    if dp_status == "insufficient":
        return True

    # economic_buyer insuficiente
    eb = _get(_get(meddicc_report, "meddicc", default={}), "economic_buyer", default={})
    eb_status = _get(eb, "status", default="insufficient")
    if eb_status == "insufficient":
        return True

    # RFP sin EB
    if _is_rfp(opportunity) and not _has_access_to_economic_buyer(meddicc_report):
        return True

    # Fixed sin scope
    if _is_fixed_price(opportunity) and not _is_scope_defined(opportunity):
        return True

    return False
