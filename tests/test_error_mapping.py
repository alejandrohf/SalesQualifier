"""Pruebas unitarias del mapeo de errores y degradación controlada de la API."""

from __future__ import annotations

from infrastructure.db.opportunities import _is_missing_table_error
from interfaces.api.routes import _classify_error


def test_classify_error_timeout() -> None:
    out = _classify_error(RuntimeError("Request timeout while calling upstream service"))
    assert out["error_type"] == "timeout_error"


def test_classify_error_validation() -> None:
    out = _classify_error(ValueError("Failed to validate payload with pydantic"))
    assert out["error_type"] == "validation_error"


def test_is_missing_table_error_detects_undefined_table() -> None:
    msg = 'relation "opportunity_qualifications" does not exist'
    assert _is_missing_table_error(RuntimeError(msg)) is True
