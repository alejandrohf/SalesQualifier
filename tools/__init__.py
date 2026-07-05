"""Registro de herramientas reutilizables disponibles para los agentes del sistema."""

from __future__ import annotations

from .tavily import search_tool
from .gmail import gmail_tools

all_tools = [search_tool] + gmail_tools

__all__ = [
    "search_tool",
    "gmail_tools",
    "all_tools",
]
