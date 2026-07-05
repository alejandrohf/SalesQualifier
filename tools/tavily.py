"""Herramienta de búsqueda web con Tavily para enriquecer contexto externo."""

# tools/tavily.py
from __future__ import annotations

from typing import Any, Dict

from tavily import TavilyClient
from langchain.tools import tool

from app.config import config


@tool("tavily_search_results_json")
def tavily_search_results_json(query: str) -> Dict[str, Any]:
    """
    Búsqueda web con Tavily. Devuelve JSON para que el agente lo use como contexto.
    """
    if not getattr(config, "TAVILY_API_KEY", None):
        return {
            "error": "TAVILY_API_KEY not configured",
            "results": [],
        }

    client = TavilyClient(api_key=config.TAVILY_API_KEY)

    # Tavily devuelve dict con results; ajusta max_results
    resp = client.search(query=query, max_results=3)
    return resp


# Export para agentes
search_tool = tavily_search_results_json