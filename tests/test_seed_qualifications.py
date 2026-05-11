"""Módulo `tests/test_seed_qualifications.py` de la plataforma Sales Qualification Agent."""

from __future__ import annotations

from datetime import datetime, timezone
import random

from seed_data.scripts.seed_qualifications import _build_payload


def test_seed_build_payload_with_due_date_in_upcoming_weeks() -> None:
    rnd = random.Random(123)
    payload = _build_payload(0, rnd, force_needs_date=True)

    assert payload["needs_date"] is True
    assert "proposal_due_date" in payload

    due = datetime.fromisoformat(payload["proposal_due_date"])
    now = datetime.now(timezone.utc)
    delta_days = (due - now).days

    assert 6 <= delta_days <= 62


def test_seed_build_payload_without_due_date() -> None:
    rnd = random.Random(456)
    payload = _build_payload(1, rnd, force_needs_date=False)

    assert payload["needs_date"] is False
    assert "proposal_due_date" not in payload


def test_seed_date_ratio_selection_logic_matches_expected_ratio() -> None:
    count = 20
    ratio = 0.4
    rnd = random.Random(42)

    target_with_date = int(round(count * ratio))
    indices_with_date = set(rnd.sample(range(count), k=target_with_date))

    date_count = 0
    for i in range(count):
        payload = _build_payload(i, rnd, force_needs_date=(i in indices_with_date))
        if payload["needs_date"]:
            date_count += 1
            assert "proposal_due_date" in payload
        else:
            assert "proposal_due_date" not in payload

    assert date_count == target_with_date
