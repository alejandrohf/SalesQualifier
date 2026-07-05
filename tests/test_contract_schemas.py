"""Validaciones automáticas sobre esquemas Pydantic y contratos internos de respuesta."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from schemas.api import QualifyResponse
from schemas.meddicc import MeddiccReport
from schemas.opportunity import OpportunityInput
from schemas.reference_match import ReferenceMatchesReport


def _opportunity_payload() -> dict:
    return {
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
    }


def _meddicc_report_payload() -> dict:
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


def _reference_matches_payload() -> dict:
    return {
        "query_used": "modernizacion datos azure ia",
        "top_k": 5,
        "matches": [
            {
                "reference_id": "47fc75bd-2962-4fa0-ac4e-44f5984106db",
                "title": "Ribera Salud",
                "customer": "Ribera Salud",
                "similarity": 0.72,
                "best_chunk_snippet": "Caso de uso de IA generativa para automatización.",
                "why_similar": ["Misma vertical", "Stack compatible"],
                "document_url": "/api/references/47fc75bd-2962-4fa0-ac4e-44f5984106db/download",
            }
        ],
        "bonus_applied": 0.3,
    }


def test_opportunity_input_accepts_datetime_proposal_due_date() -> None:
    obj = OpportunityInput.model_validate(_opportunity_payload())
    assert isinstance(obj.proposal_due_date, datetime)


def test_opportunity_input_rejects_unknown_fields_strict() -> None:
    payload = _opportunity_payload()
    payload["unexpected_field"] = "boom"
    with pytest.raises(ValidationError):
        OpportunityInput.model_validate(payload)


def test_meddicc_report_rejects_out_of_range_total_score() -> None:
    payload = _meddicc_report_payload()
    payload["summary"]["total_score"] = 10.5
    with pytest.raises(ValidationError):
        MeddiccReport.model_validate(payload)


def test_reference_matches_report_rejects_unknown_field() -> None:
    payload = _reference_matches_payload()
    payload["matches"][0]["extra"] = "not_allowed"
    with pytest.raises(ValidationError):
        ReferenceMatchesReport.model_validate(payload)


def test_qualify_response_validates_full_contract() -> None:
    payload = {
        "opportunity": _opportunity_payload(),
        "meddicc_report": _meddicc_report_payload(),
        "scoring": {
            "base_total_score": 8.0,
            "total_score": 8.3,
            "qualification_level": "high",
            "recommended_action": "invest_pre_sales",
            "adjustments": {"strategic_vertical": 0.5},
            "has_critical_risk": False,
        },
        "reference_matches": _reference_matches_payload(),
        "metadata": {},
    }
    out = QualifyResponse.model_validate(payload)
    assert out.scoring.total_score == 8.3
    assert out.reference_matches is not None
    assert out.reference_matches.matches[0].similarity == 0.72
