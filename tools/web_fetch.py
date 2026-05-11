"""Módulo `tools/web_fetch.py` de la plataforma Sales Qualification Agent."""

from __future__ import annotations

import re
from html import unescape
from typing import Any, Dict

import requests
from langchain.tools import tool
from tavily import TavilyClient

from app.config import config


def _clean_text(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_thin_content(title: str, meta_description: str, body_excerpt: str) -> bool:
    signal_text = " ".join([title or "", meta_description or "", body_excerpt or ""]).strip()
    if len(signal_text) < 220:
        return True
    low_value_patterns = [
        "enable javascript",
        "coming soon",
        "under construction",
        "cookie",
        "accept all",
        "privacy preferences",
    ]
    lowered = signal_text.lower()
    return any(p in lowered for p in low_value_patterns)


def _tavily_fallback_for_domain(url: str) -> Dict[str, Any]:
    if not getattr(config, "TAVILY_API_KEY", None):
        return {"ok": False, "source": "tavily", "error": "TAVILY_API_KEY not configured"}

    query = f"Company overview, business model, services, industries, recent news site:{url}"
    try:
        client = TavilyClient(api_key=config.TAVILY_API_KEY)
        resp = client.search(query=query, max_results=4)
    except Exception as e:
        return {"ok": False, "source": "tavily", "error": str(e)}

    results = resp.get("results", []) if isinstance(resp, dict) else []
    snippets = []
    for r in results[:4]:
        title = _clean_text(str(r.get("title", "")))
        content = _clean_text(str(r.get("content", "")))
        if title or content:
            snippets.append({"title": title, "content": content, "url": r.get("url", "")})

    merged = " ".join([f"{s.get('title','')} {s.get('content','')}".strip() for s in snippets]).strip()
    return {
        "ok": bool(snippets),
        "source": "tavily",
        "query": query,
        "snippets": snippets,
        "body_excerpt": merged[:2500],
    }


@tool("fetch_website_context")
def fetch_website_context(url: str) -> Dict[str, Any]:
    """
    Descarga una URL pública y devuelve contexto básico (title, meta description y extracto de body).
    """
    try:
        resp = requests.get(
            url,
            timeout=12,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; SalesQualificationAgent/1.0)",
                "Accept-Language": "es,en;q=0.9",
            },
        )
        resp.raise_for_status()
    except Exception as e:
        return {"ok": False, "url": url, "error": str(e)}

    html = resp.text or ""

    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    title = _clean_text(title_match.group(1)) if title_match else ""

    meta_desc_match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not meta_desc_match:
        meta_desc_match = re.search(
            r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']',
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
    meta_description = _clean_text(meta_desc_match.group(1)) if meta_desc_match else ""

    body = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", html)
    body = re.sub(r"(?is)<[^>]+>", " ", body)
    body_text = _clean_text(body)
    body_excerpt = body_text[:2500]

    result = {
        "ok": True,
        "source": "website",
        "url": url,
        "status_code": resp.status_code,
        "title": title,
        "meta_description": meta_description,
        "body_excerpt": body_excerpt,
    }
    if _is_thin_content(title=title, meta_description=meta_description, body_excerpt=body_excerpt):
        fallback = _tavily_fallback_for_domain(url)
        result["fallback"] = fallback
        if fallback.get("ok"):
            # Si la home es pobre, priorizamos contenido de Tavily para el agente.
            result["source"] = "website+tavily"
            result["body_excerpt"] = fallback.get("body_excerpt", body_excerpt)

    return result
