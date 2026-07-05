"""Vista de diagnóstico del estado de dependencias externas y APIs configuradas."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from interfaces.ui.components.auth import get_authenticated_api_client, require_authentication
from interfaces.ui.components.layout import kpi_card, page_header, section, set_page_config, sidebar_header
from interfaces.ui.components.render import json_expander, show_api_error


def _fmt_dt(value: object) -> str:
    if not value:
        return "N/D"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(value)


def main():
    """Renderiza el estado detallado de APIs y servicios auxiliares de la solución."""
    set_page_config()
    require_authentication()
    sidebar_header()
    page_header("API Status", "Detalle de dependencias externas desde /api/api-status.")

    client = get_authenticated_api_client()

    try:
        data = client.api_status()
    except Exception as e:
        show_api_error(e)
        return

    apis = data.get("apis", {})

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Checked at", _fmt_dt(data.get("timestamp")), variant="warning")
    with c2:
        kpi_card(
            "OpenAI",
            "✅" if apis.get("openai", {}).get("configured") else "❌",
            variant="success" if apis.get("openai", {}).get("configured") else "danger",
        )
    with c3:
        kpi_card(
            "Tavily",
            "✅" if apis.get("tavily", {}).get("configured") else "❌",
            variant="success" if apis.get("tavily", {}).get("configured") else "danger",
        )
    with c4:
        kpi_card(
            "Gmail",
            "✅" if apis.get("gmail", {}).get("configured") else "❌",
            variant="success" if apis.get("gmail", {}).get("configured") else "danger",
        )

    st.divider()
    section("Respuesta completa")
    json_expander("Respuesta completa", data, expanded=True)


if __name__ == "__main__":
    main()
