"""Configuración base del LLM compartido por los agentes especializados."""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from app.config import config


def build_llm() -> ChatOpenAI:
    """Crea la instancia compartida de ChatOpenAI utilizada por los agentes."""
    return ChatOpenAI(
        model="gpt-4o-mini",
        api_key=config.OPENAI_API_KEY,
        temperature=0.1,
    )


llm = build_llm()
