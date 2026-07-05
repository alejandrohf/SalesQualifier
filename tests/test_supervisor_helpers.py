"""Pruebas de utilidades internas del supervisor del workflow multiagente."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from types import ModuleType
from typing import Any


def _load_supervisor_module() -> Any:
    """
    Carga workflows/supervisor.py sin depender de agentes reales.
    """
    project_root = Path(__file__).resolve().parents[1]
    supervisor_path = project_root / "workflows" / "supervisor.py"

    dummy_agents = ModuleType("agents")

    class _DummyAgent:
        def invoke(self, payload):  # pragma: no cover - no se usa en estos tests
            return {"messages": [types.SimpleNamespace(content="{}")]}

    dummy_agents.opportunity_analyzer = _DummyAgent()
    dummy_agents.client_website_analyzer = _DummyAgent()
    dummy_agents.risk_analyzer = _DummyAgent()
    dummy_agents.delivery_fit_analyzer = _DummyAgent()
    dummy_agents.commercial_fit_analyzer = _DummyAgent()
    dummy_agents.references_match_agent = _DummyAgent()
    dummy_agents.notification_agent = _DummyAgent()

    dummy_vectorstore = ModuleType("tools.vectorstore")
    dummy_vectorstore.search_references = lambda query, top_k=5, filters=None: []

    previous_agents = sys.modules.get("agents")
    previous_vectorstore = sys.modules.get("tools.vectorstore")
    sys.modules["agents"] = dummy_agents
    sys.modules["tools.vectorstore"] = dummy_vectorstore

    try:
        module_name = "_test_supervisor_real_module"
        spec = importlib.util.spec_from_file_location(module_name, supervisor_path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if previous_agents is None:
            sys.modules.pop("agents", None)
        else:
            sys.modules["agents"] = previous_agents

        if previous_vectorstore is None:
            sys.modules.pop("tools.vectorstore", None)
        else:
            sys.modules["tools.vectorstore"] = previous_vectorstore


def test_safe_json_loads_extracts_first_valid_object_from_text() -> None:
    sup = _load_supervisor_module()
    raw = "texto previo\n{\"summary\": {\"total_score\": 10.5}}\ntexto posterior"
    out = sup._safe_json_loads(raw)
    assert out["summary"]["total_score"] == 10.5


def test_normalize_meddicc_payload_clamps_summary_total_score() -> None:
    sup = _load_supervisor_module()
    payload = {"summary": {"total_score": 10.5}}
    out = sup._normalize_meddicc_payload(payload)
    assert out["summary"]["total_score"] == 10.0


def test_compute_reference_bonus_uses_top5_and_thresholds() -> None:
    sup = _load_supervisor_module()
    bonus = sup._compute_reference_bonus([0.9, 0.88, 0.85, 0.82, 0.8, 0.1])
    assert bonus == 0.5
