"""Módulo `interfaces/ui/pages/6_Health.py` de la plataforma Sales Qualification Agent."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from interfaces.ui.components.auth import get_authenticated_api_client, require_authentication
from interfaces.ui.components.layout import (
    info_banner,
    kpi_card,
    page_header,
    section,
    set_page_config,
    sidebar_header,
)
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
    """Ejecuta `main` dentro de este modulo."""
    set_page_config()
    require_authentication()
    sidebar_header()
    page_header("Health", "Estado del sistema desde /api/health.")

    client = get_authenticated_api_client()

    try:
        data = client.health()
    except Exception as e:
        show_api_error(e)
        return

    status = data.get("status", "unknown")

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("Status", str(status), variant="success" if status == "healthy" else "danger")
    with c2:
        kpi_card("Procesadas", str(data.get("total_opportunities_processed", "-")), variant="neutral")
    with c3:
        kpi_card("Timestamp", _fmt_dt(data.get("timestamp")), variant="warning")

    st.divider()
    section("Detalle /health")
    json_expander("Detalle /health", data, expanded=True)


if __name__ == "__main__":
    main()
