"""Módulo `tests/test_rules.py` de la plataforma Sales Qualification Agent."""

from __future__ import annotations

from types import SimpleNamespace

from domain.rules import derive_has_critical_risk, derive_strategic_flags


def _mk_dim(status: str, score: float):
    return SimpleNamespace(status=status, score=score)


def _mk_report(*, champion_status: str = "insufficient", champion_score: float = 0.2, eb_status: str = "insufficient", eb_score: float = 0.5, dp_status: str = "insufficient", dp_score: float = 0.5):
    meddicc = SimpleNamespace(
        champion=_mk_dim(champion_status, champion_score),
        economic_buyer=_mk_dim(eb_status, eb_score),
        decision_process=_mk_dim(dp_status, dp_score),
    )
    return SimpleNamespace(meddicc=meddicc, client_context=SimpleNamespace(is_new_client=True))


def test_derive_flags_fixed_price_without_scope_and_new_client_no_champion() -> None:
    opp = {
        "is_new_client": True,
        "collaboration_type": "fixed_price",
        "description": "Corto",  # scope no definido por heurística
        "deal_size": None,
    }
    report = _mk_report(champion_status="insufficient", champion_score=0.2, eb_status="partial", eb_score=1.2, dp_status="partial", dp_score=1.0)
    flags = derive_strategic_flags(opp, report)

    assert flags.new_client_no_strong_champion is True
    assert flags.fixed_price_without_scope is True


def test_derive_has_critical_risk_when_decision_process_insufficient() -> None:
    opp = {"collaboration_type": "t&m", "description": "x" * 120, "deal_size": "M"}
    report = _mk_report(dp_status="insufficient", dp_score=0.2, eb_status="complete", eb_score=1.5)

    assert derive_has_critical_risk(opp, report) is True


def test_derive_flags_rfp_without_access_to_economic_buyer() -> None:
    opp = {
        "is_new_client": False,
        "collaboration_type": "rfp",
        "description": "x" * 200,
        "deal_size": "L",
        "proposal_due_date": "2026-03-20T18:00:00",
        "main_area": "ai",
    }
    report = _mk_report(eb_status="insufficient", eb_score=0.2, dp_status="complete", dp_score=1.2)
    flags = derive_strategic_flags(opp, report)

    assert flags.rfp_no_access_to_economic_buyer is True
