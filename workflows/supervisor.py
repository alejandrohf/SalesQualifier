"""Supervisor del workflow multiagente de cualificación.

Orquesta la ejecución de agentes, aplica reglas deterministas, coordina la
recuperación de referencias y prepara la notificación final.
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any, cast

from fastapi.encoders import jsonable_encoder
from langgraph.graph import END, START, StateGraph

from agents import (
    client_website_analyzer,
    commercial_fit_analyzer,
    delivery_fit_analyzer,
    notification_agent,
    opportunity_analyzer,
    references_match_agent,
    risk_analyzer,
)

from domain.rules import derive_has_critical_risk, derive_strategic_flags
from domain.scoring import Dimension, ScoringError, build_scoring_summary
from schemas.meddicc import MeddiccReport
from schemas.notifications import EmailNotification

from schemas.opportunity import OpportunityInput
from schemas.reference_match import ReferenceMatchesReport
from schemas.scoring import ScoringSummary
from tools.vectorstore import search_references
from workflows.state import WorkflowState

# Tiempos máximos de ejecución por nodo, configurables mediante variables de entorno.
MEDDICC_TIMEOUT_S = int(os.getenv("SQA_MEDDICC_TIMEOUT_S", "120"))
CLIENT_WEBSITE_TIMEOUT_S = int(os.getenv("SQA_CLIENT_WEBSITE_TIMEOUT_S", "45"))
REFERENCES_TIMEOUT_S = int(os.getenv("SQA_REFERENCES_TIMEOUT_S", "60"))
RISK_TIMEOUT_S = int(os.getenv("SQA_RISK_TIMEOUT_S", "60"))
DELIVERY_TIMEOUT_S = int(os.getenv("SQA_DELIVERY_TIMEOUT_S", "60"))
COMMERCIAL_TIMEOUT_S = int(os.getenv("SQA_COMMERCIAL_TIMEOUT_S", "60"))
NOTIFICATION_TIMEOUT_S = int(os.getenv("SQA_NOTIFICATION_TIMEOUT_S", "90"))
DOCUMENT_BASE_URL = os.getenv("SQA_API_BASE_URL", "http://localhost:8000")


def _append_trace(state: WorkflowState, msg: str) -> None:
    trace = state.get("trace") or []
    trace.append(msg)
    state["trace"] = trace


def _invoke_agent_with_timeout(agent: Any, payload: dict[str, Any], timeout_s: int, label: str) -> Any:
    """Ejecuta un agente con un tiempo máximo para proteger la disponibilidad de la API."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(agent.invoke, payload)
        try:
            return fut.result(timeout=timeout_s)
        except FuturesTimeoutError as e:
            fut.cancel()
            raise TimeoutError(f"{label} timed out after {timeout_s}s") from e

def _safe_json_loads(raw: str) -> Any:
    """Intenta interpretar una respuesta JSON aunque incluya texto adicional alrededor."""
    text = (raw or "").strip()
    try:
        return json.loads(text)
    except Exception:
        # Busca el primer objeto JSON válido cuando la respuesta incluye texto accesorio.
        decoder = json.JSONDecoder()
        for i, ch in enumerate(text):
            if ch != "{":
                continue
            try:
                obj, _ = decoder.raw_decode(text[i:])
                return obj
            except Exception:
                continue
        raise

def _normalize_meddicc_payload(data: Any) -> Any:
    """Ajusta valores del informe MEDDICC antes de validarlos contra el esquema."""
    if not isinstance(data, dict):
        return data

    summary = data.get("summary")
    if isinstance(summary, dict):
        raw_total = summary.get("total_score")
        try:
            summary["total_score"] = max(0.0, min(10.0, float(raw_total)))
        except Exception:
            pass

    return data

def _build_dimension_scores(report: MeddiccReport) -> dict[Dimension, float]:
    """Extrae las puntuaciones por dimensión desde el informe MEDDICC validado."""
    return cast(dict[Dimension, float], {
        "metrics": report.meddicc.metrics.score,
        "economic_buyer": report.meddicc.economic_buyer.score,
        "decision_criteria": report.meddicc.decision_criteria.score,
        "decision_process": report.meddicc.decision_process.score,
        "identify_pain": report.meddicc.identify_pain.score,
        "champion": report.meddicc.champion.score,
        "competition": report.meddicc.competition.score,
    })

def _should_run_deep_analysis(state: WorkflowState) -> str:
    """Decide si la oportunidad requiere análisis adicionales o pasa directamente a notificación."""
    scoring = state.get("scoring") or {}
    action = scoring.get("recommended_action")

    if action in ("invest_pre_sales", "request_more_info"):
        return "deep_analysis"
    return "notify"

def _route_stop_if_error(state: WorkflowState) -> str:
    return "stop" if state.get("status") == "error" else "continue"

def _compute_reference_bonus(similarities: list[float]) -> float:
    """Calcula un bonus acotado según la similitud de las referencias recuperadas."""
    if not similarities:
        return 0.0

    sims = sorted([max(0.0, min(1.0, float(s))) for s in similarities], reverse=True)[:5]
    avg_top = sum(sims) / len(sims)

    if avg_top >= 0.85:
        return 0.5
    if avg_top >= 0.75:
        return 0.4
    if avg_top >= 0.65:
        return 0.3
    if avg_top >= 0.55:
        return 0.2
    if avg_top >= 0.45:
        return 0.1
    return 0.0

def _build_reference_query(opportunity: Any) -> str:
    data = jsonable_encoder(opportunity) if opportunity is not None else {}
    if not isinstance(data, dict):
        return str(data)[:1200]

    parts = [
        data.get("client_name", ""),
        data.get("description", ""),
        str(data.get("main_area", "")),
        str(data.get("partner", "")),
        str(data.get("collaboration_type", "")),
        data.get("notes", ""),
    ]
    query = " ".join([str(p).strip() for p in parts if p]).strip()
    return query[:1200]

def _fallback_reference_matches_report(state: WorkflowState) -> ReferenceMatchesReport | None:
    """Genera coincidencias de referencias sin depender de una respuesta estructurada del agente."""
    opportunity = state.get("opportunity")
    if opportunity is None:
        return None

    query = _build_reference_query(opportunity)
    if not query:
        return None

    hits = search_references(query=query, top_k=5, filters=None)
    matches: list[dict[str, Any]] = []
    for h in hits:
        snippet = (h.chunk_text or "")[:900]
        why = [
            f"Coincidencia semántica del caso (sim={h.similarity:.2f})",
            "Stack/objetivo alineado con la oportunidad actual",
        ]
        matches.append(
            {
                "reference_id": str(h.reference_id),
                "title": h.title,
                "customer": h.customer,
                "similarity": float(h.similarity),
                "best_chunk_snippet": snippet,
                "why_similar": why[:3],
                "document_url": f"{DOCUMENT_BASE_URL}/api/references/{h.reference_id}/download",
            }
        )

    report = ReferenceMatchesReport.model_validate(
        {
            "query_used": query,
            "top_k": 5,
            "matches": matches,
            "bonus_applied": 0.0,
        }
    )
    return report

def _build_opportunity_context_for_email(opportunity: Any) -> dict[str, Any]:
    data = jsonable_encoder(opportunity) if opportunity is not None else {}
    if not isinstance(data, dict):
        data = {}

    def _val(k: str) -> str:
        v = data.get(k)
        if v in (None, "", []):
            return "N/D"
        return str(v)

    return {
        "client_name": _val("client_name"),
        "client_website": _val("client_website"),
        "quote_id": _val("quote_id"),
        "quote_crm_url": _val("quote_crm_url"),
        "shared_folder_url": _val("shared_folder_url"),
        "partner": _val("partner"),
        "collaboration_type": _val("collaboration_type"),
        "deal_size": _val("deal_size"),
        "main_area": _val("main_area"),
        "description": _val("description"),
        "notes": _val("notes"),
    }

def node_meddicc_analyze(state: WorkflowState) -> WorkflowState:
    """
    Ejecuta opportunity_analyzer y guarda el JSON raw devuelto.
    """
    state["status"] = "running"
    _append_trace(state, "node_meddicc_analyze:start")

    opportunity = state.get("opportunity")
    if opportunity is None:
        state["status"] = "error"
        state["error"] = "Missing opportunity in state"
        return state

    # Convierte la oportunidad a un formato textual adecuado para el agente.
    if hasattr(opportunity, "model_dump"):
        payload = opportunity.model_dump(mode="json")
    elif isinstance(opportunity, dict):
        payload = opportunity
    else:
        payload = {"opportunity": str(opportunity)}

    website_context = state.get("client_website_summary") or {}

    prompt_input = f"""OPPORTUNITY_INPUT_JSON:
{json.dumps(payload, ensure_ascii=False, indent=2)}

CLIENT_WEBSITE_CONTEXT_JSON (si existe, úsalo para enriquecer company context):
{json.dumps(website_context, ensure_ascii=False, indent=2)}

INSTRUCCIÓN:
- Analiza con MEDDICC y responde SOLO con JSON válido según el esquema requerido.
"""

    try:
        result = _invoke_agent_with_timeout(
            opportunity_analyzer,
            {"messages": [{"role": "user", "content": prompt_input}]},
            MEDDICC_TIMEOUT_S,
            "meddicc_analyzer",
        )
    except TimeoutError as e:
        state["status"] = "error"
        state["error"] = str(e)
        _append_trace(state, f"node_meddicc_analyze:timeout {e}")
        return state

    # Toma el último mensaje generado por el agente cuando la respuesta llega en formato conversacional.
    raw = None
    if isinstance(result, dict) and "messages" in result and result["messages"]:
        raw = result["messages"][-1].content  # type: ignore[attr-defined]
    else:
        raw = getattr(result, "content", None) or str(result)

    state["meddicc_report_raw"] = raw
    _append_trace(state, "node_meddicc_analyze:done")
    return state

def node_run_client_website_context(state: WorkflowState) -> WorkflowState:
    """
    Si existe client_website en la oportunidad, obtiene un resumen corto de la web del cliente.
    """
    _append_trace(state, "node_run_client_website_context:start")

    opportunity = state.get("opportunity")
    opp_json = jsonable_encoder(opportunity) if opportunity is not None else {}
    website_url = ""
    if isinstance(opp_json, dict):
        website_url = str(opp_json.get("client_website") or "").strip()

    if not website_url:
        state["client_website_summary"] = None
        state["client_website_summary_raw"] = ""
        _append_trace(state, "node_run_client_website_context:skipped no_client_website")
        return state

    prompt_input = f"""CLIENT_WEBSITE_URL:
{website_url}

INSTRUCCIÓN:
- Navega la URL y devuelve SOLO JSON con resumen corto (3-4 líneas) y puntos relevantes.
"""

    try:
        result = _invoke_agent_with_timeout(
            client_website_analyzer,
            {"messages": [{"role": "user", "content": prompt_input}]},
            CLIENT_WEBSITE_TIMEOUT_S,
            "client_website_analyzer",
        )
    except TimeoutError as e:
        state["client_website_summary"] = None
        state["client_website_summary_raw"] = ""
        _append_trace(state, f"node_run_client_website_context:timeout {e}")
        return state

    raw = result["messages"][-1].content if isinstance(result, dict) and result.get("messages") else str(result)
    state["client_website_summary_raw"] = raw

    try:
        data = _safe_json_loads(raw)
        if isinstance(data, dict):
            state["client_website_summary"] = data
            _append_trace(state, "node_run_client_website_context:done")
        else:
            state["client_website_summary"] = None
            _append_trace(state, "node_run_client_website_context:invalid_non_dict")
    except Exception as e:
        state["client_website_summary"] = None
        _append_trace(state, f"node_run_client_website_context:failed {e}")

    return state

def node_parse_meddicc_report(state: WorkflowState) -> WorkflowState:
    """
    Parsea el JSON del LLM a MeddiccReport (Pydantic).
    """
    _append_trace(state, "node_parse_meddicc_report:start")

    raw = state.get("meddicc_report_raw")
    if not raw:
        state["status"] = "error"
        state["error"] = "Missing meddicc_report_raw"
        return state

    try:
        data = _safe_json_loads(raw)
        data = _normalize_meddicc_payload(data)
        report = MeddiccReport.model_validate(data)
        state["meddicc_report"] = report
        _append_trace(state, "node_parse_meddicc_report:validated")
        return state
    except Exception as e:
        state["status"] = "error"
        state["error"] = f"Failed to parse/validate MeddiccReport: {e}"
        return state

def node_run_references_match(state: WorkflowState) -> WorkflowState:
    """
    Invoca el agente RAG para recuperar referencias similares.
    """
    _append_trace(state, "node_run_references_match:start")

    opportunity = state.get("opportunity")
    report = state.get("meddicc_report")

    opp_json = jsonable_encoder(opportunity)
    meddicc_json = jsonable_encoder(report.summary) if report else {}

    # Base URL usada para construir enlaces de descarga de documentos.
    document_base_url = DOCUMENT_BASE_URL

    prompt_input = f"""OPPORTUNITY_JSON:
{json.dumps(opp_json, ensure_ascii=False, indent=2)}

MEDDICC_SUMMARY_JSON:
{json.dumps(meddicc_json, ensure_ascii=False, indent=2)}

CLIENT_WEBSITE_CONTEXT_JSON:
{json.dumps(state.get("client_website_summary") or {}, ensure_ascii=False, indent=2)}

DOCUMENT_BASE_URL:
{document_base_url}

INSTRUCCIÓN:
- Ejecuta la búsqueda en vectorstore y devuelve SOLO JSON según ReferenceMatchesReport.
"""

    try:
        result = _invoke_agent_with_timeout(
            references_match_agent,
            {"messages": [{"role": "user", "content": prompt_input}]},
            REFERENCES_TIMEOUT_S,
            "references_match_agent",
        )
    except TimeoutError as e:
        state["reference_matches_raw"] = ""
        _append_trace(state, f"node_run_references_match:timeout {e}")
        return state

    raw = result["messages"][-1].content if isinstance(result, dict) and result.get("messages") else str(result)

    state["reference_matches_raw"] = raw
    _append_trace(state, "node_run_references_match:done")
    return state

def node_parse_references_match(state: WorkflowState) -> WorkflowState:
    """
    Valida ReferenceMatchesReport y calcula bonus determinista.
    """
    _append_trace(state, "node_parse_references_match:start")

    raw = state.get("reference_matches_raw")
    if not raw:
        fallback = _fallback_reference_matches_report(state)
        if fallback:
            sims = [m.similarity for m in fallback.matches]
            bonus = _compute_reference_bonus(sims)
            fallback.bonus_applied = bonus
            state["reference_matches"] = fallback
            state["reference_bonus"] = bonus
            _append_trace(state, f"node_parse_references_match:fallback bonus={bonus} matches={len(fallback.matches)}")
            return state
        state["reference_matches"] = None
        state["reference_bonus"] = 0.0
        _append_trace(state, "node_parse_references_match:empty")
        return state

    try:
        data = _safe_json_loads(raw)
        report = ReferenceMatchesReport.model_validate(data)

        sims = [m.similarity for m in report.matches]
        bonus = _compute_reference_bonus(sims)

        # Actualiza el bonus calculado a partir de las similitudes recuperadas.
        report.bonus_applied = bonus

        state["reference_matches"] = report
        state["reference_bonus"] = bonus

        _append_trace(state, f"node_parse_references_match:done bonus={bonus}")
        return state
    except Exception as e:
        fallback = _fallback_reference_matches_report(state)
        if fallback:
            sims = [m.similarity for m in fallback.matches]
            bonus = _compute_reference_bonus(sims)
            fallback.bonus_applied = bonus
            state["reference_matches"] = fallback
            state["reference_bonus"] = bonus
            _append_trace(
                state,
                f"node_parse_references_match:failed_then_fallback error={e} bonus={bonus} matches={len(fallback.matches)}",
            )
            return state
        state["reference_matches"] = None
        state["reference_bonus"] = 0.0
        _append_trace(state, f"node_parse_references_match:failed {e}")
        return state
    
def node_domain_rules_and_scoring(state: WorkflowState) -> WorkflowState:
    """
    Aplica reglas deterministas (flags + critical risk) y recalcula scoring determinista.
    """
    _append_trace(state, "node_domain_rules_and_scoring:start")

    opportunity = state.get("opportunity")
    report = state.get("meddicc_report")

    if opportunity is None or report is None:
        state["status"] = "error"
        state["error"] = "Missing opportunity or meddicc_report"
        return state

    # Convierte la entrada a OpportunityInput cuando procede de la API como diccionario.
    if isinstance(opportunity, dict):
        opportunity_obj = OpportunityInput.model_validate(opportunity)
        state["opportunity"] = opportunity_obj
        opportunity = opportunity_obj

    try:
        dimension_scores = _build_dimension_scores(cast(MeddiccReport, report))
        flags = derive_strategic_flags(opportunity, report)
        has_critical_risk = derive_has_critical_risk(opportunity, report)

        scoring = build_scoring_summary(
            dimension_scores=dimension_scores,
            flags=flags,
            has_critical_risk=has_critical_risk,
            reference_bonus=float(state.get("reference_bonus", 0.0) or 0.0),
        )

        state["dimension_scores"] = dimension_scores
        state["strategic_flags"] = flags
        state["has_critical_risk"] = has_critical_risk
        state["scoring"] = scoring

        # Valida el resultado final con el esquema de scoring.
        scoring_summary = ScoringSummary.model_validate({
            "base_total_score": scoring["base_total_score"],
            "total_score": scoring["total_score"],
            "qualification_level": scoring["qualification_level"],
            "recommended_action": scoring["recommended_action"],
            "adjustments": scoring.get("adjustments", {}),
            "has_critical_risk": bool(has_critical_risk),
        })
        state["scoring_summary"] = scoring_summary

        _append_trace(state, "node_domain_rules_and_scoring:done")
        return state

    except ScoringError as e:
        state["status"] = "error"
        state["error"] = f"Scoring validation error: {e}"
        return state
    except Exception as e:
        state["status"] = "error"
        state["error"] = f"Rules/scoring error: {e}"
        return state

def node_run_risk_analyzer(state: WorkflowState) -> WorkflowState:
    """Ejecuta el analizador de riesgos y registra su salida textual en el estado."""
    _append_trace(state, "node_run_risk_analyzer:start")

    opportunity = state.get("opportunity")
    report = state.get("meddicc_report")
    scoring = state.get("scoring") or {}

    prompt_input = f"""CONTEXTO OPORTUNIDAD:
- Opportunity: {opportunity.model_dump() if hasattr(opportunity,'model_dump') else opportunity}
- MeddiccReport.summary: {report.summary.model_dump() if report else None}
- Scoring (determinista): {scoring}

INSTRUCCIÓN:
- Genera registro de riesgos y mitigaciones según tu formato requerido.
"""

    try:
        result = _invoke_agent_with_timeout(
            risk_analyzer,
            {"messages": [{"role": "user", "content": prompt_input}]},
            RISK_TIMEOUT_S,
            "risk_analyzer",
        )
    except TimeoutError as e:
        state["risk_report"] = f"Timeout en análisis de riesgos: {e}"
        _append_trace(state, f"node_run_risk_analyzer:timeout {e}")
        return state

    text = result["messages"][-1].content if isinstance(result, dict) and result.get("messages") else str(result)

    state["risk_report"] = text
    _append_trace(state, "node_run_risk_analyzer:done")
    return state

def node_run_delivery_fit_analyzer(state: WorkflowState) -> WorkflowState:
    """Ejecuta el análisis de viabilidad técnica y de entrega de la oportunidad."""
    _append_trace(state, "node_run_delivery_fit_analyzer:start")

    opportunity = state.get("opportunity")
    report = state.get("meddicc_report")

    prompt_input = f"""CONTEXTO OPORTUNIDAD:
- Opportunity: {opportunity.model_dump() if hasattr(opportunity,'model_dump') else opportunity}
- MEDDICC gaps (high level): {report.summary.model_dump() if report else None}

INSTRUCCIÓN:
- Evalúa viabilidad técnica y de delivery según el formato requerido.
"""

    try:
        result = _invoke_agent_with_timeout(
            delivery_fit_analyzer,
            {"messages": [{"role": "user", "content": prompt_input}]},
            DELIVERY_TIMEOUT_S,
            "delivery_fit_analyzer",
        )
    except TimeoutError as e:
        state["delivery_fit_report"] = f"Timeout en análisis de delivery: {e}"
        _append_trace(state, f"node_run_delivery_fit_analyzer:timeout {e}")
        return state

    text = result["messages"][-1].content if isinstance(result, dict) and result.get("messages") else str(result)

    state["delivery_fit_report"] = text
    _append_trace(state, "node_run_delivery_fit_analyzer:done")
    return state

def node_run_commercial_fit_analyzer(state: WorkflowState) -> WorkflowState:
    """Ejecuta el análisis comercial orientado a margen, modelo contractual y guardrails."""
    _append_trace(state, "node_run_commercial_fit_analyzer:start")

    opportunity = state.get("opportunity")
    report = state.get("meddicc_report")
    scoring = state.get("scoring") or {}

    prompt_input = f"""CONTEXTO OPORTUNIDAD:
- Opportunity: {opportunity.model_dump() if hasattr(opportunity,'model_dump') else opportunity}
- MEDDICC: {report.meddicc.model_dump() if report else None}
- Scoring (determinista): {scoring}

INSTRUCCIÓN:
- Evalúa riesgo de margen y estrategia contractual según tu formato requerido.
"""

    try:
        result = _invoke_agent_with_timeout(
            commercial_fit_analyzer,
            {"messages": [{"role": "user", "content": prompt_input}]},
            COMMERCIAL_TIMEOUT_S,
            "commercial_fit_analyzer",
        )
    except TimeoutError as e:
        state["commercial_fit_report"] = f"Timeout en análisis comercial: {e}"
        _append_trace(state, f"node_run_commercial_fit_analyzer:timeout {e}")
        return state

    text = result["messages"][-1].content if isinstance(result, dict) and result.get("messages") else str(result)

    state["commercial_fit_report"] = text
    _append_trace(state, "node_run_commercial_fit_analyzer:done")
    return state

def node_prepare_and_send_notification(state: WorkflowState) -> WorkflowState:
    """
    Ejecuta notification_agent. Dependiendo de cómo lo tengas:
    - Si notification_agent compone JSON: parsea EmailNotification y luego tú envías con Gmail API (recomendado).
    - Si notification_agent envía con GmailToolkit: guardas el resultado.
    """
    _append_trace(state, "node_prepare_and_send_notification:start")

    opportunity = state.get("opportunity")
    meddicc_report = state.get("meddicc_report")
    scoring_summary = state.get("scoring_summary")
    reference_matches = state.get("reference_matches")
    recipients = state.get("recipients") or {"to": [], "cc": []}
    if not recipients.get("to"):
        recipients = {"to": [os.getenv("SQA_EMAIL_RECIPIENT", "alejandrohf@gmail.com")], "cc": []}

    opp_json = jsonable_encoder(opportunity)
    opp_email_context = _build_opportunity_context_for_email(opportunity)
    website_ctx = state.get("client_website_summary")
    if isinstance(website_ctx, dict):
        opp_email_context["client_website_summary"] = website_ctx.get("summary_short", "N/D") or "N/D"
        opp_email_context["client_website_key_points"] = website_ctx.get("relevant_points", []) or []
        opp_email_context["client_website_source_used"] = website_ctx.get("source_used", "N/D") or "N/D"
    else:
        opp_email_context["client_website_summary"] = "N/D"
        opp_email_context["client_website_key_points"] = []
        opp_email_context["client_website_source_used"] = "N/D"
    meddicc_json = jsonable_encoder(meddicc_report) if meddicc_report else {}
    scoring_json = jsonable_encoder(scoring_summary) if scoring_summary else {}
    refs_json = jsonable_encoder(reference_matches) if reference_matches else {}

    prompt_input = f"""RECIPIENTS:
{json.dumps(recipients, ensure_ascii=False, indent=2)}

OPPORTUNITY:
{json.dumps(opp_json, ensure_ascii=False, indent=2)}

OPPORTUNITY_EMAIL_CONTEXT (usa esta ficha para asegurar campos obligatorios en el email):
{json.dumps(opp_email_context, ensure_ascii=False, indent=2)}

MEDDICC_REPORT (completo):
{json.dumps(meddicc_json, ensure_ascii=False, indent=2)}

SCORING (determinista):
{json.dumps(scoring_json, ensure_ascii=False, indent=2)}

REFERENCES_MATCHES (Top-5):
{json.dumps(refs_json, ensure_ascii=False, indent=2)}

RISK_REPORT (opcional):
{state.get("risk_report")}

DELIVERY_FIT (opcional):
{state.get("delivery_fit_report")}

COMMERCIAL_FIT (opcional):
{state.get("commercial_fit_report")}

ANALYSIS_REPORTS_RAW (COPIA LITERAL EN ANEXOS DEL EMAIL):
=== RISK_ANALYZER_RAW_BEGIN ===
{state.get("risk_report") or "N/D"}
=== RISK_ANALYZER_RAW_END ===

=== DELIVERY_FIT_ANALYZER_RAW_BEGIN ===
{state.get("delivery_fit_report") or "N/D"}
=== DELIVERY_FIT_ANALYZER_RAW_END ===

=== COMMERCIAL_FIT_ANALYZER_RAW_BEGIN ===
{state.get("commercial_fit_report") or "N/D"}
=== COMMERCIAL_FIT_ANALYZER_RAW_END ===

INSTRUCCIÓN:
- Genera y/o envía notificación según tu prompt.
"""

    try:
        result = _invoke_agent_with_timeout(
            notification_agent,
            {"messages": [{"role": "user", "content": prompt_input}]},
            NOTIFICATION_TIMEOUT_S,
            "notification_agent",
        )
    except TimeoutError as e:
        state["notification_result"] = f"failed: timeout sending notification ({e})"
        _append_trace(state, f"node_prepare_and_send_notification:timeout {e}")
        state["status"] = "completed"
        return state

    output = result["messages"][-1].content if isinstance(result, dict) and result.get("messages") else str(result)

    state["notification_payload_raw"] = output

    # Si el agente devuelve JSON (recomendado), lo validamos
    if EmailNotification is not None:
        try:
            data = _safe_json_loads(output)
            payload = EmailNotification.model_validate(data)
            state["notification_payload"] = payload
            state["notification_result"] = "prepared"
        except Exception:
            # Si la salida no es JSON, se conserva como resultado textual del agente.
            state["notification_result"] = output
    else:
        state["notification_result"] = output

    _append_trace(state, "node_prepare_and_send_notification:done")
    state["status"] = "completed"
    return state


def build_sales_qualification_workflow():
    """
    Compila el grafo LangGraph.
    """
    graph = StateGraph(WorkflowState)

    graph.add_node("client_website_context", node_run_client_website_context)
    graph.add_node("meddicc_analyze", node_meddicc_analyze)
    graph.add_node("parse_meddicc", node_parse_meddicc_report)
    graph.add_node("references_match", node_run_references_match)
    graph.add_node("parse_references_match", node_parse_references_match)

    graph.add_node("domain_scoring", node_domain_rules_and_scoring)

    graph.add_node("risk", node_run_risk_analyzer)
    graph.add_node("delivery_fit", node_run_delivery_fit_analyzer)
    graph.add_node("commercial_fit", node_run_commercial_fit_analyzer)

    graph.add_node("notify", node_prepare_and_send_notification)

    graph.add_edge(START, "client_website_context")
    graph.add_edge("client_website_context", "meddicc_analyze")
    graph.add_edge("meddicc_analyze", "parse_meddicc")
    graph.add_conditional_edges(
        "parse_meddicc",
        _route_stop_if_error,
        {
            "stop": END, 
            "continue": "references_match"
        },
    )

    graph.add_edge("references_match", "parse_references_match")
    graph.add_edge("parse_references_match", "domain_scoring")

    graph.add_conditional_edges(
        "domain_scoring",
        _should_run_deep_analysis,
        {
            "deep_analysis": "risk",
            "notify": "notify",
        },
    )

    graph.add_edge("risk", "delivery_fit")
    graph.add_edge("delivery_fit", "commercial_fit")
    graph.add_edge("commercial_fit", "notify")

    graph.add_edge("notify", END)

    return graph.compile()


sales_qualification_workflow = build_sales_qualification_workflow()


def process_opportunity(
    opportunity: OpportunityInput | dict[str, Any],
    recipients: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Ejecuta el workflow completo y devuelve una estructura serializable para la API y la interfaz."""
    init_state: WorkflowState = {
        "status": "draft",
        "opportunity": opportunity,
        "recipients": recipients or {"to": [], "cc": []},
        "trace": [],
    }

    result = sales_qualification_workflow.invoke(init_state)

    # Convierte la salida del workflow en una estructura directamente serializable.
    out: dict[str, Any] = {
        "status": result.get("status"),
        "error": result.get("error"),
        "trace": result.get("trace", []),
        "client_website_summary": result.get("client_website_summary"),
        "scoring": result.get("scoring_summary").model_dump() if result.get("scoring_summary") else result.get("scoring"),
        "meddicc_report": result.get("meddicc_report").model_dump(mode="json") if result.get("meddicc_report") else None,
        "reference_matches": result.get("reference_matches").model_dump(mode="json") if result.get("reference_matches") else None,
        "risk_report": result.get("risk_report"),
        "delivery_fit_report": result.get("delivery_fit_report"),
        "commercial_fit_report": result.get("commercial_fit_report"),
        "notification": (
            result.get("notification_payload").model_dump()
            if result.get("notification_payload") is not None and hasattr(result.get("notification_payload"), "model_dump")
            else result.get("notification_result")
        ),
        "notification_payload_raw": result.get("notification_payload_raw"),
    }
    return out
