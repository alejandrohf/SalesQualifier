"""Módulo `agents/base.py` de la plataforma Sales Qualification Agent."""

# agents/base.py
from __future__ import annotations

from langchain_openai import ChatOpenAI
from app.config import config


def build_llm() -> ChatOpenAI:
    """
    Construye el LLM una sola vez.
    Centralizarlo evita inconsistencias y facilita cambiar modelo/params.
    """
    return ChatOpenAI(
        model="gpt-4o-mini",
        api_key=config.OPENAI_API_KEY,
        temperature=0.1,
    )


# Instancia singleton (simple y suficiente para MVP)
llm = build_llm()