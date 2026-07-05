"""Herramienta de búsqueda web con Tavily para enriquecer contexto externo."""

from __future__ import annotations

from typing import Any, Dict

from tavily import TavilyClient
from langchain.tools import tool

from app.config import config


@tool("tavily_search_results_json")
def tavily_search_results_json(query: str) -> Dict[str, Any]:
    """Ejecuta una búsqueda web y devuelve los resultados en formato JSON."""
    if not getattr(config, "TAVILY_API_KEY", None):
        return {
            "error": "TAVILY_API_KEY not configured",
            "results": [],
        }

    client = TavilyClient(api_key=config.TAVILY_API_KEY)

    resp = client.search(query=query, max_results=3)
    return resp


search_tool = tavily_search_results_json
