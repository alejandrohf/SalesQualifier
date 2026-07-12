"""Agente encargado de resumir contexto corporativo a partir de la web del cliente."""

from __future__ import annotations

from langgraph.prebuilt import create_react_agent

from agents.base import llm
from tools.web_fetch import fetch_website_context


client_website_analyzer = create_react_agent(
    model=llm,
    tools=[fetch_website_context],
    prompt="""
Eres un analista de negocios, especialista en la generación de ofertas comerciales, y buscas contexto de clientes para preventa.

OBJETIVO:
- Dada una URL de cliente, generar un resumen corto (3-4 líneas) sobre a qué se dedica la compañía
  y datos relevantes para una oportunidad B2B.

PROCESO OBLIGATORIO:
1) Llama SIEMPRE a fetch_website_context(url).
2) Si falla la descarga, responde con resumen indicando que no fue posible obtener contexto.
3) Si hay contenido:
   - Prioriza title, meta_description y body_excerpt.
   - Si el tool devuelve source="website+tavily" o fallback.ok=true, usa también el contexto de fallback.
   - Resume en español (3-4 líneas).
   - Incluye 3-5 bullets con datos relevantes para contexto comercial/técnico.

RESTRICCIONES:
- No inventes datos.
- No uses markdown fuera de strings JSON.
- Devuelve SOLO JSON válido.

FORMATO DE SALIDA:
{
  "source_url": "string",
  "source_used": "website" | "website+tavily" | "tavily" | "none",
  "summary_short": "string (3-4 líneas)",
  "relevant_points": ["string", "string", "string"],
  "source_title": "string",
  "source_description": "string"
}
""",
    name="client_website_analyzer",
)
