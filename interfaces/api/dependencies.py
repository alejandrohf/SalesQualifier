"""Dependencias técnicas de FastAPI para workflow y validación de configuración."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable, Dict

from app.config import config
from workflows.supervisor import process_opportunity


@lru_cache
def get_workflow_runner() -> Callable[..., Dict[str, Any]]:
    """Devuelve la función que ejecuta el workflow de cualificación."""
    return process_opportunity

def validate_config_on_startup() -> Dict[str, Any]:
    """Valida la configuración disponible y resume errores y advertencias."""
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

    if not getattr(config, "TAVILY_API_KEY", None):
        status["warnings"].append("Falta TAVILY_API_KEY (búsqueda web no disponible).")

    if not getattr(config, "OPENAI_API_KEY", None):
        status["errors"].append("Falta OPENAI_API_KEY (LLM no disponible).")
        status["configured"] = False

    if not getattr(config, "GMAIL_CREDENTIALS_FILE", None):
        status["warnings"].append("Gmail credentials no configuradas (envío de email deshabilitado).")

    return status
