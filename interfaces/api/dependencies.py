"""Dependencias técnicas de FastAPI para workflow y validación de configuración."""

# interfaces/api/dependencies.py
from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable, Dict

from app.config import config
from workflows.supervisor import process_opportunity  # tu entrypoint del workflow


@lru_cache
def get_workflow_runner() -> Callable[..., Dict[str, Any]]:
    """
    Devuelve el runner del workflow (singleton para MVP).
    """
    return process_opportunity

def validate_config_on_startup() -> Dict[str, Any]:
    """
    Valida la config y devuelve un resumen utilizable en /health.
    No lanza excepción: devuelve estado y warnings.
    """
    status = {
        "configured": True,
        "errors": [],
        "warnings": [],
    }

    try:
        config.validate_required_config()
    except Exception as e:
        status["configured"] = False
        status["errors"].append(str(e))

    # Avisos opcionales (ej. Gmail podría ser opcional)
    # Ajusta estas condiciones a tu config real.
    if not getattr(config, "TAVILY_API_KEY", None):
        status["warnings"].append("Falta TAVILY_API_KEY (búsqueda web no disponible).")

    if not getattr(config, "OPENAI_API_KEY", None):
        status["errors"].append("Falta OPENAI_API_KEY (LLM no disponible).")
        status["configured"] = False

    # Gmail normalmente opcional en MVP si solo compones email
    if not getattr(config, "GMAIL_CREDENTIALS_FILE", None):
        status["warnings"].append("Gmail credentials no configuradas (envío de email deshabilitado).")

    return status
