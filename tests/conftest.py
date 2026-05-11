"""Módulo `tests/conftest.py` de la plataforma Sales Qualification Agent."""

from __future__ import annotations

import sys
import types
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Evita cargar el grafo real (y dependencias pesadas) durante tests de API.
if "workflows.supervisor" not in sys.modules:
    supervisor_stub = types.ModuleType("workflows.supervisor")

    def _stub_process_opportunity(*args, **kwargs):
        raise RuntimeError("stub workflow should be overridden in tests")

    supervisor_stub.process_opportunity = _stub_process_opportunity
    sys.modules["workflows.supervisor"] = supervisor_stub
