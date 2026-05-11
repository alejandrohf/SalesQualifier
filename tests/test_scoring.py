"""Módulo `tests/test_scoring.py` de la plataforma Sales Qualification Agent."""

from __future__ import annotations

from domain.scoring import (
    StrategicFlags,
    build_scoring_summary,
    determine_qualification_level,
    determine_recommended_action,
)


def _base_dimension_scores() -> dict[str, float]:
    return {
        "metrics": 1.5,
        "economic_buyer": 1.5,
        "decision_criteria": 1.0,
        "decision_process": 1.0,
        "identify_pain": 1.0,
        "champion": 0.8,
        "competition": 0.3,
    }


def test_determine_qualification_level_thresholds() -> None:
    assert determine_qualification_level(8.0) == "high"
    assert determine_qualification_level(6.0) == "medium"
    assert determine_qualification_level(5.99) == "low"


def test_build_scoring_summary_applies_reference_bonus_with_cap() -> None:
    scores = _base_dimension_scores()
    out = build_scoring_summary(
        dimension_scores=scores,
        flags=StrategicFlags(),
        has_critical_risk=False,
        reference_bonus=0.9,  # debe clamp a 0.5
    )

    assert out["adjustments"].get("references_bonus") == 0.5
    assert out["total_score"] <= 10.0


def test_recommended_action_high_with_critical_risk_not_prioritized() -> None:
    assert determine_recommended_action("high", has_critical_risk=True) == "do_not_prioritize"
