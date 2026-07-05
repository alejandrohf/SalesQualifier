"""Rutas principales de cualificación, monitorización y revisión técnica."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder

from app.config import config
from interfaces.api.dependencies import (
    get_workflow_runner,
    validate_config_on_startup,
)
from interfaces.api.auth_dependencies import require_engineering, require_sales, require_sales_or_engineering
from infrastructure.db.opportunities import (
    count_opportunity_qualifications,
    get_opportunity_qualification_by_id,
    list_opportunity_qualifications,
    set_technical_decision,
    save_opportunity_qualification,
)
from infrastructure.db.users import get_user_by_id

from schemas.api import QualifyRequest, QualifyResponse, ErrorResponse
from schemas.scoring import ScoringSummary
from schemas.meddicc import MeddiccReport

router = APIRouter(tags=["qualification"])


class HealthResponse(Dict[str, Any]):
    """Representación documental de la respuesta del endpoint de salud."""


class ApiStatusResponse(Dict[str, Any]):
    """Representación documental del estado detallado de dependencias."""


class OpportunityListItem(Dict[str, Any]):
    """Elemento documental del listado de oportunidades."""


class OpportunitiesResponse(Dict[str, Any]):
    """Respuesta documental del endpoint de listado de oportunidades."""


class QualifyEnvelopeResponse(Dict[str, Any]):
    """Respuesta documental del endpoint de cualificación."""


class TechnicalDecisionRequest(BaseModel):
    """Solicitud para registrar una decisión técnica sobre una oportunidad."""
    decision: str
    comment: Optional[str] = None



def _classify_error(e: Exception) -> Dict[str, str]:
    msg = str(e)

    if "OPENAI" in msg.upper() or "LLM" in msg.upper():
        return {
            "error_type": "llm_error",
            "suggestion": "Verifica configuración de OpenAI/Azure OpenAI y conectividad.",
        }
    if "TAVILY" in msg.upper():
        return {
            "error_type": "tavily_error",
            "suggestion": "Verifica TAVILY_API_KEY o deshabilita búsqueda web en el agente.",
        }
    if "gmail" in msg.lower():
        return {
            "error_type": "gmail_error",
            "suggestion": "Configura OAuth2 de Gmail o usa modo compose-only (sin envío).",
        }
    if "timeout" in msg.lower():
        return {
            "error_type": "timeout_error",
            "suggestion": "Los servicios externos tardan. Reintenta o reduce herramientas/steps.",
        }
    if "validate" in msg.lower() or "pydantic" in msg.lower():
        return {
            "error_type": "validation_error",
            "suggestion": "Revisa el JSON del agente y los schemas Pydantic (extra=forbid).",
        }

    return {
        "error_type": "unknown_error",
        "suggestion": "Error inesperado. Revisa logs/trace del workflow.",
    }


def _agent_status_from_trace(trace: List[str], agent_key: str) -> str:
    has_start = any(f"{agent_key}:start" in t for t in trace)
    has_done = any(f"{agent_key}:done" in t for t in trace)
    has_timeout = any(f"{agent_key}:timeout" in t for t in trace)

    if has_timeout:
        return "timeout"
    if has_done:
        return "executed"
    if has_start:
        return "started_not_finished"
    return "skipped"


@router.get(
    "/health",
    summary="Health check del sistema",
    responses={
        200: {"description": "OK / degraded"},
    },
)
def health_check():
    """Devuelve el estado general del servicio y de sus dependencias principales."""
    config_status = validate_config_on_startup()

    api_configuration = {
        "openai": "configurada" if getattr(config, "OPENAI_API_KEY", None) else "no configurada",
        "tavily": "configurada" if getattr(config, "TAVILY_API_KEY", None) else "no configurada",
        "gmail_credentials": "configurada" if getattr(config, "GMAIL_CREDENTIALS_FILE", None) else "no configurada",
        "gmail_auth": "configurada" if getattr(config, 'GMAIL_TOKEN_FILE', None) else "no configurada",
        "database": "configurada" if getattr(config, 'DATABASE_URL', None) else "no configurada"
    }

    missing = [k for k, v in api_configuration.items() if v == "no configurada"]

    overall = "healthy"
    if missing or not config_status["configured"]:
        overall = "degraded"

    return {
        "status": overall,
        "timestamp": datetime.now().isoformat(),
        "total_opportunities_processed": count_opportunity_qualifications(),
        "api_configuration": api_configuration,
        "warnings": config_status.get("warnings", []),
        "errors": config_status.get("errors", []),
    }


@router.get(
    "/api-status",
    summary="Estado detallado de dependencias externas",
    responses={200: {"description": "Estado detallado de APIs"}},
)
def api_status():
    """Describe el estado de las dependencias externas utilizadas por la plataforma."""
    return {
        "timestamp": datetime.now().isoformat(),
        "apis": {
            "openai": {
                "configured": bool(getattr(config, "OPENAI_API_KEY", None)),
                "description": "LLM para agentes (MEDDICC, análisis extra y notificaciones).",
                "required": True,
            },
            "tavily": {
                "configured": bool(getattr(config, "TAVILY_API_KEY", None)),
                "description": "Búsqueda web para enriquecer contexto del cliente.",
                "required": False,
                "notes": "Si falta, el agente MEDDICC no usará búsqueda web.",
            },
            "gmail": {
                "configured": bool(getattr(config, "GMAIL_CREDENTIALS_FILE", None)),
                "description": "Envío real de emails (si tu agente notifica enviando).",
                "required": False,
                "setup_required": "Google Cloud Console + OAuth2 (token file + client secrets).",
            },
        },
    }


@router.get(
    "/opportunities",
    summary="Listar oportunidades procesadas",
    responses={200: {"description": "Listado de oportunidades"}},
)
def get_opportunities(current_user=Depends(require_sales_or_engineering())):
    """Lista las oportunidades procesadas y filtra el acceso según el rol del usuario."""
    opps = list_opportunity_qualifications(limit=2000, offset=0)
    user_id = str(current_user.get("id"))

    if current_user.get("can_sales") and not current_user.get("can_engineering"):
        opps = [
            o
            for o in opps
            if not o.get("created_by_user_id") or str(o.get("created_by_user_id") or "") == user_id
        ]
    elif current_user.get("can_engineering") and not current_user.get("can_sales"):
        filtered = []
        for o in opps:
            creator_id = o.get("created_by_user_id")
            if not creator_id:
                filtered.append(o)
                continue
            creator = get_user_by_id(creator_id)
            if creator and str(creator.get("engineering_manager_id") or "") == user_id:
                filtered.append(o)
        opps = filtered
    else:
        # Si el usuario combina funciones comerciales y técnicas, se integran ambos ámbitos de visibilidad.
        filtered = []
        for o in opps:
            creator_id = str(o.get("created_by_user_id") or "")
            if not creator_id:
                filtered.append(o)
                continue
            if creator_id == user_id:
                filtered.append(o)
                continue
            if creator_id:
                creator = get_user_by_id(creator_id)
                if creator and str(creator.get("engineering_manager_id") or "") == user_id:
                    filtered.append(o)
        opps = filtered
    # Añade el nombre del usuario que registró la decisión técnica para mostrarlo en la interfaz.
    decision_user_cache: Dict[str, str] = {}
    for o in opps:
        decision_id = str(o.get("technical_decision_by_user_id") or "").strip()
        if not decision_id:
            o["technical_decision_by_name"] = None
            continue
        if decision_id not in decision_user_cache:
            u = get_user_by_id(decision_id)
            if u:
                decision_user_cache[decision_id] = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or str(u.get("email", ""))
            else:
                decision_user_cache[decision_id] = ""
        o["technical_decision_by_name"] = decision_user_cache.get(decision_id) or None

    return {
        "opportunities": opps,
        "total_opportunities": len(opps),
        "last_updated": datetime.now().isoformat(),
    }


@router.post("/opportunities/{opportunity_id}/technical-decision")
def set_opportunity_technical_decision(
    opportunity_id: str,
    body: TechnicalDecisionRequest,
    current_user=Depends(require_engineering()),
):
    """Registra la decisión técnica sobre una oportunidad si el usuario está autorizado."""
    decision = (body.decision or "").strip().lower()
    if decision not in ("go", "no_go"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="decision must be go or no_go")
    if decision == "no_go" and not (body.comment or "").strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="comment is required for no_go")

    opp = get_opportunity_qualification_by_id(opportunity_id)
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    creator_user_id = opp.get("created_by_user_id")
    if not creator_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Opportunity without creator user")
    creator = get_user_by_id(creator_user_id)
    if not creator:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Creator user not found")

    # La autorización técnica depende de la asociación actual Sales -> Engineering.
    assigned_engineering_id = creator.get("engineering_manager_id")
    if not assigned_engineering_id or str(assigned_engineering_id) != str(current_user.get("id")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Engineering user not assigned to this Sales user")

    status_value = "go" if decision == "go" else "no_go"
    updated = set_technical_decision(
        opportunity_id=opportunity_id,
        technical_status=status_value,
        technical_decision_by_user_id=current_user.get("id"),
        technical_comment=(body.comment or "").strip() or None,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    return {
        "status": "success",
        "opportunity_id": opportunity_id,
        "technical_status": status_value,
        "technical_decision_by_user_id": current_user.get("id"),
    }


@router.post(
    "/qualify",
    summary="Cualificar una oportunidad (MEDDICC + scoring determinista + RAG de referencias + análisis complementarios)",
    responses={
        200: {"description": "Oportunidad procesada correctamente"},
        400: {"model": ErrorResponse, "description": "Error de validación/workflow"},
        422: {"model": ErrorResponse, "description": "Request inválido (Pydantic)"},
        500: {"model": ErrorResponse, "description": "Error interno"},
    },
)
def qualify_opportunity(
    req: QualifyRequest,
    run_workflow=Depends(get_workflow_runner),
    current_user=Depends(require_sales()),
):
    """Ejecuta el proceso completo de cualificación y devuelve su resultado consolidado."""
    try:

        opportunity_id = f"OPP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6]}"

        opp_json = req.opportunity.model_dump(mode="json")

        engineering_user = None
        engineering_id = current_user.get("engineering_manager_id")
        if engineering_id:
            engineering_user = get_user_by_id(engineering_id)
            if engineering_user and (not engineering_user.get("is_active") or not engineering_user.get("can_engineering")):
                engineering_user = None

        recipients_to = [str(current_user.get("email"))]
        if engineering_user and engineering_user.get("email"):
            recipients_to.append(str(engineering_user["email"]))

        result = run_workflow(
            opportunity=opp_json,
            recipients={"to": list(dict.fromkeys(recipients_to)), "cc": []},
        )

        # Si el workflow informa de error funcional, se devuelve como respuesta controlada.
        if isinstance(result, dict) and result.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": result.get("error") or "Workflow error",
                    "error_type": "workflow_error",
                    "suggestion": "Revisa el trace y el JSON de salida del agente MEDDICC.",
                    "timestamp": datetime.now().isoformat(),
                },
            )

        meddicc_report = result.get("meddicc_report")
        scoring = result.get("scoring")

        meddicc_obj = MeddiccReport.model_validate(meddicc_report)
        scoring_obj = ScoringSummary.model_validate(scoring)

        qualify_response = QualifyResponse(
            opportunity=req.opportunity,
            meddicc_report=meddicc_obj,
            scoring=scoring_obj,
            reference_matches=result.get("reference_matches"),
            metadata=req.metadata,
        )

        req_json = jsonable_encoder(req.opportunity)
        resp_json = jsonable_encoder(qualify_response)
        trace_json = jsonable_encoder(result.get("trace", []))
        agent_execution = {
            "client_website_analyzer": _agent_status_from_trace(trace_json, "node_run_client_website_context"),
            "risk_analyzer": _agent_status_from_trace(trace_json, "node_run_risk_analyzer"),
            "delivery_fit_analyzer": _agent_status_from_trace(trace_json, "node_run_delivery_fit_analyzer"),
            "commercial_fit_analyzer": _agent_status_from_trace(trace_json, "node_run_commercial_fit_analyzer"),
        }
        resp_persisted = {
            **resp_json,
            "_workflow_client_website_summary": result.get("client_website_summary"),
            "_workflow_notification": result.get("notification"),
            "_workflow_notification_raw": result.get("notification_payload_raw"),
            "_workflow_risk_report": result.get("risk_report"),
            "_workflow_delivery_fit_report": result.get("delivery_fit_report"),
            "_workflow_commercial_fit_report": result.get("commercial_fit_report"),
            "_workflow_agent_execution": agent_execution,
        }


        persisted_ts = datetime.now()
        save_opportunity_qualification(
            opportunity_id=opportunity_id,
            timestamp=persisted_ts,
            request_payload=req_json,
            response_payload=resp_persisted,
            trace_payload=trace_json,
            created_by_user_id=current_user.get("id"),
            created_by_email=current_user.get("email"),
            assigned_engineering_user_id=engineering_user.get("id") if engineering_user else None,
            technical_status="pending",
        )

        payload = {
            "status": "success",
            "opportunity_id": opportunity_id,
            "message": "Oportunidad procesada por el sistema multiagente.",
            "processing_time": "variable (depende de herramientas y profundidad)",
            "result": qualify_response.model_dump(mode="json"),
            "trace": jsonable_encoder(result.get("trace", [])),
            "analysis_reports": {
                "risk_report": result.get("risk_report"),
                "delivery_fit_report": result.get("delivery_fit_report"),
                "commercial_fit_report": result.get("commercial_fit_report"),
            },
            "client_website_summary": result.get("client_website_summary"),
            "agent_execution": agent_execution,
            "notification": result.get("notification"),
            "created_by_user_id": current_user.get("id"),
            "assigned_engineering_user_id": engineering_user.get("id") if engineering_user else None,
            "technical_status": "pending",
        }

        return jsonable_encoder(payload)

    except HTTPException:
        raise

    except Exception as e:
        classification = _classify_error(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": str(e),
                "error_type": classification["error_type"],
                "suggestion": classification["suggestion"],
                "timestamp": datetime.now().isoformat(),
            },
        )
