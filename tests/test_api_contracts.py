"""Pruebas de contratos JSON expuestos por los endpoints principales de la API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.testclient import TestClient

import interfaces.api.routes as routes
from interfaces.api.auth_dependencies import get_current_user
from interfaces.api.dependencies import get_workflow_runner


def _fake_workflow_runner(*, opportunity: Dict[str, Any], recipients: Dict[str, Any] | None = None) -> Dict[str, Any]:
    dim = {
        "status": "complete",
        "score": 1.0,
        "evidence": ["e1"],
        "risks": ["r1"],
        "questions": ["q1"],
    }
    return {
        "status": "completed",
        "trace": ["node_meddicc_analyze:start", "node_meddicc_analyze:done"],
        "meddicc_report": {
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
        },
        "scoring": {
            "base_total_score": 7.8,
            "total_score": 8.3,
            "qualification_level": "high",
            "recommended_action": "invest_pre_sales",
            "adjustments": {"strategic_vertical": 0.5},
            "has_critical_risk": False,
        },
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


def _valid_qualify_payload() -> Dict[str, Any]:
    return {
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


def test_api_qualify_contract_has_required_fields(monkeypatch) -> None:
    monkeypatch.setattr(routes, "save_opportunity_qualification", lambda **kwargs: None)
    client = TestClient(_build_app())
    resp = client.post("/api/qualify", json=_valid_qualify_payload())
    assert resp.status_code == 200
    body = resp.json()

    for field in [
        "status",
        "opportunity_id",
        "message",
        "processing_time",
        "result",
        "trace",
        "analysis_reports",
        "agent_execution",
        "notification",
    ]:
        assert field in body

    for result_field in ["opportunity", "meddicc_report", "scoring", "metadata"]:
        assert result_field in body["result"]


def test_api_opportunities_contract_has_required_fields(monkeypatch) -> None:
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

    for field in ["opportunities", "total_opportunities", "last_updated"]:
        assert field in body

    assert body["total_opportunities"] == len(body["opportunities"])
    assert len(body["opportunities"]) > 0
    for item_field in ["opportunity_id", "timestamp", "request", "response", "trace"]:
        assert item_field in body["opportunities"][0]
