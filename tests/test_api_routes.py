"""Módulo `tests/test_api_routes.py` de la plataforma Sales Qualification Agent."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.testclient import TestClient

import interfaces.api.routes as routes
from interfaces.api.auth_dependencies import get_current_user
from interfaces.api.dependencies import get_workflow_runner


def _fake_meddicc_report() -> Dict[str, Any]:
    dim = {
        "status": "complete",
        "score": 1.0,
        "evidence": ["e1"],
        "risks": ["r1"],
        "questions": ["q1"],
    }
    return {
        "client_context": {
            "source": "input",
            "client_name": "Acme",
            "is_new_client": False,
            "sector": None,
            "company_summary": None,
            "multinational": None,
            "employee_count": None,
            "revenue_info": None,
            "notes": None,
        },
        "meddicc": {
            "metrics": {**dim, "score": 1.5},
            "economic_buyer": {**dim, "score": 1.5},
            "decision_criteria": {**dim, "score": 1.2},
            "decision_process": {**dim, "score": 1.0},
            "identify_pain": {**dim, "score": 1.0},
            "champion": {**dim, "score": 0.8},
            "competition": {**dim, "score": 0.3},
        },
        "summary": {
            "total_score": 8.3,
            "qualification_level": "high",
            "recommended_action": "invest_pre_sales",
            "score_justification": "ok",
            "critical_risks_top3": ["r1", "r2", "r3"],
            "next_steps": ["n1"],
        },
    }


def _fake_scoring() -> Dict[str, Any]:
    return {
        "base_total_score": 7.8,
        "total_score": 8.3,
        "qualification_level": "high",
        "recommended_action": "invest_pre_sales",
        "adjustments": {"strategic_vertical": 0.5},
        "has_critical_risk": False,
    }


def _fake_workflow_runner(*, opportunity: Dict[str, Any], recipients: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "status": "completed",
        "trace": [
            "node_meddicc_analyze:start",
            "node_meddicc_analyze:done",
            "node_run_delivery_fit_analyzer:start",
            "node_run_delivery_fit_analyzer:done",
            "node_run_commercial_fit_analyzer:start",
            "node_run_commercial_fit_analyzer:done",
        ],
        "meddicc_report": _fake_meddicc_report(),
        "scoring": _fake_scoring(),
        "reference_matches": {
            "query_used": "q",
            "top_k": 5,
            "matches": [],
            "bonus_applied": 0.0,
        },
        "risk_report": "risk raw",
        "delivery_fit_report": "delivery raw",
        "commercial_fit_report": "commercial raw",
        "notification": {"status": "sent", "message_id": "m1"},
        "notification_payload_raw": "raw",
        "client_website_summary": {"summary_short": "Acme es...", "source_used": "website"},
    }


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(routes.router, prefix="/api")
    app.dependency_overrides[get_workflow_runner] = lambda: _fake_workflow_runner
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "admin@example.com",
        "is_admin": True,
        "can_sales": True,
        "can_engineering": True,
        "is_active": True,
    }
    return app


def test_qualify_returns_analysis_and_agent_execution(monkeypatch) -> None:
    captured = {}

    def _fake_save(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(routes, "save_opportunity_qualification", _fake_save)

    client = TestClient(_build_app())
    payload = {
        "opportunity": {
            "client_name": "Acme",
            "is_new_client": False,
            "requester": {"name": "Laura", "role": "decision_maker", "seniority": "director"},
            "description": "Proyecto de modernización de plataforma de datos e IA para reducir costes y mejorar operaciones.",
            "collaboration_type": "fixed_price",
            "partner": "microsoft",
            "main_area": "ai",
            "relationship_trust": 4,
            "sales_confidence": "Alta",
            "needs_date": True,
            "proposal_due_date": "2026-03-20T18:00:00",
            "deal_size": "L",
        },
        "metadata": {},
    }

    resp = client.post("/api/qualify", json=payload)
    assert resp.status_code == 200
    body = resp.json()

    assert body["status"] == "success"
    assert body["analysis_reports"]["delivery_fit_report"] == "delivery raw"
    assert body["analysis_reports"]["commercial_fit_report"] == "commercial raw"
    assert body["agent_execution"]["delivery_fit_analyzer"] == "executed"
    assert body["agent_execution"]["commercial_fit_analyzer"] == "executed"

    assert captured["response_payload"]["_workflow_delivery_fit_report"] == "delivery raw"
    assert captured["response_payload"]["_workflow_commercial_fit_report"] == "commercial raw"


def test_get_opportunities_reads_from_db_service(monkeypatch) -> None:
    monkeypatch.setattr(
        routes,
        "list_opportunity_qualifications",
        lambda limit=2000, offset=0: [
            {
                "opportunity_id": "OPP-1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request": {"client_name": "Acme"},
                "response": {"scoring": {"total_score": 8.0}},
                "trace": [],
            }
        ],
    )

    client = TestClient(_build_app())
    resp = client.get("/api/opportunities")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_opportunities"] == 1
    assert body["opportunities"][0]["opportunity_id"] == "OPP-1"


def test_qualify_returns_400_when_workflow_returns_error_status() -> None:
    def _runner_with_error(*, opportunity: Dict[str, Any], recipients: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return {"status": "error", "error": "invalid meddicc payload"}

    app = FastAPI()
    app.include_router(routes.router, prefix="/api")
    app.dependency_overrides[get_workflow_runner] = lambda: _runner_with_error
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "admin@example.com",
        "is_admin": True,
        "can_sales": True,
        "can_engineering": True,
        "is_active": True,
    }
    client = TestClient(app)

    payload = {
        "opportunity": {
            "client_name": "Acme",
            "is_new_client": False,
            "requester": {"name": "Laura", "role": "decision_maker", "seniority": "director"},
            "description": "Proyecto con alcance y detalle suficiente para validación del contrato API.",
            "collaboration_type": "fixed_price",
            "partner": "microsoft",
            "main_area": "ai",
            "relationship_trust": 4,
            "sales_confidence": "Alta",
            "needs_date": False,
            "deal_size": "L",
        },
        "metadata": {},
    }
    resp = client.post("/api/qualify", json=payload)
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["error_type"] == "workflow_error"


def test_qualify_returns_500_with_mapped_timeout_error() -> None:
    def _runner_timeout(*, opportunity: Dict[str, Any], recipients: Dict[str, Any] | None = None) -> Dict[str, Any]:
        raise TimeoutError("timeout while running agent")

    app = FastAPI()
    app.include_router(routes.router, prefix="/api")
    app.dependency_overrides[get_workflow_runner] = lambda: _runner_timeout
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "admin@example.com",
        "is_admin": True,
        "can_sales": True,
        "can_engineering": True,
        "is_active": True,
    }
    client = TestClient(app)

    payload = {
        "opportunity": {
            "client_name": "Acme",
            "is_new_client": False,
            "requester": {"name": "Laura", "role": "decision_maker", "seniority": "director"},
            "description": "Proyecto con alcance y detalle suficiente para validación del contrato API.",
            "collaboration_type": "fixed_price",
            "partner": "microsoft",
            "main_area": "ai",
            "relationship_trust": 4,
            "sales_confidence": "Alta",
            "needs_date": False,
            "deal_size": "L",
        },
        "metadata": {},
    }
    resp = client.post("/api/qualify", json=payload)
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert detail["error_type"] == "timeout_error"
