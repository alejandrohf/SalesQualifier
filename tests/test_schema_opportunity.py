"""Módulo `tests/test_schema_opportunity.py` de la plataforma Sales Qualification Agent."""

from __future__ import annotations

from datetime import datetime

from schemas.opportunity import OpportunityInput


def test_opportunity_accepts_datetime_due_date() -> None:
    payload = {
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

    obj = OpportunityInput.model_validate(payload)
    assert isinstance(obj.proposal_due_date, datetime)
    assert obj.proposal_due_date.hour == 18
