"""Formulario de alta y cualificación de nuevas oportunidades comerciales."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

import streamlit as st

from interfaces.ui.components.auth import get_authenticated_api_client, require_authentication
from interfaces.ui.components.layout import page_header, section, set_page_config, sidebar_header
from interfaces.ui.components.render import json_expander, show_api_error, show_envelope_result

DISPLAY_OVERRIDES = {
    "decision_maker": "Decision Maker",
    "non_decision_maker": "Non Decision Maker",
    "unknown": "Unknown",
    "cxo": "CXO",
    "vp_head": "VP Head",
    "director": "Director",
    "employee": "Employee",
    "t&m": "T&M",
    "fixed_price": "Fixed Price",
    "profiles_request": "Profiles Request",
    "rfp": "RFP",
    "consulting": "Consulting",
    "licenses": "Licenses",
    "other": "Other",
    "none": "None",
    "microsoft": "Microsoft",
    "aws": "AWS",
    "google": "Google",
    "ibm": "IBM",
    "multiverse": "Multiverse",
    "snowflake": "Snowflake",
    "databricks": "Databricks",
    "data": "Data",
    "ai": "AI",
    "development": "Development",
    "security": "Security",
    "infrastructure": "Infrastructure",
    "XS": "XS (<25K)",
    "S": "S (>25K & <50K)",
    "M": "M (>50K & <100K)",
    "L": "L (>100K & <250K)",
    "XL": "XL (>250K & <1M)",
    "XXL": "XXL (>1M)"
}


def _format_option(value: str) -> str:
    s = str(value)
    if s in DISPLAY_OVERRIDES:
        return DISPLAY_OVERRIDES[s]
    return s.replace("_", " ").replace("-", " ").title()


def build_opportunity_payload_from_form(needs_date: bool, proposal_due_date: datetime | None) -> dict[str, Any]:
    """
    Construye el JSON de OpportunityInput.
    Ajusta si tu schema OpportunityInput cambia.
    """
    client_name = st.text_input("Cliente", value="")
    is_new_client = st.checkbox("¿Es nuevo cliente?", value=False)
    client_website = st.text_input("Web del cliente", value="")  # HttpUrl opcional

    section("Solicitante")
    requester_name = st.text_input("Nombre solicitante", value="")
    requester_role = st.selectbox(
        "Rol solicitante",
        ["decision_maker", "non_decision_maker", "unknown"],
        index=2,
        format_func=_format_option,
    )
    requester_seniority = st.selectbox(
        "Nivel solicitante",
        ["cxo", "vp_head", "director", "employee"],
        index=3,
        format_func=_format_option,
    )

    section("Oportunidad")
    description = st.text_area("Descripción de la oportunidad", height=160)

    quote_id = st.text_input("Quote ID", value="")
    quote_crm_url = st.text_input("CRM URL", value="")
    shared_folder_url = st.text_input("Carpeta compartida para trabajar la oportunidad", value="")

    collaboration_type = st.selectbox(
        "Tipo de colaboración",
        ["t&m", "fixed_price", "profiles_request", "rfp", "consulting", "licenses", "other"],
        index=6,
        format_func=_format_option,
    )
    partner = st.selectbox(
        "Partner involucrado",
        ["none", "microsoft", "aws", "google", "ibm", "multiverse", "snowflake", "databricks", "other"],
        index=0,
        format_func=_format_option,
    )
    main_area = st.selectbox(
        "Área de solución",
        ["development", "data", "ai", "security", "infrastructure", "other"],
        index=4,
        format_func=_format_option,
    )

    relationship_trust = st.slider("Relación de confianza (1-5)", min_value=1, max_value=5, value=3)
    sales_confidence = st.selectbox("Confianza del comercial en ganar la oportunidad", ["Alta", "Media", "Baja", "No sabe"], index=3)

    deal_size = st.selectbox("Tamaño oferta", ["XS", "S", "M", "L", "XL", "XXL"], index=1, format_func=_format_option)
    notes = st.text_area("Otras notas", height=100)

    payload: dict[str, Any] = {
        "client_name": client_name,
        "is_new_client": is_new_client,
        "requester": {
            "name": requester_name,
            "role": requester_role,
            "seniority": requester_seniority,
        },
        "description": description,
        "collaboration_type": collaboration_type,
        "partner": partner,
        "main_area": main_area,
        "relationship_trust": relationship_trust,
        "sales_confidence": "unknown" if sales_confidence == "No sabe" else sales_confidence,
        "needs_date": needs_date,
        "deal_size": deal_size,
    }

    if client_website.strip():
        payload["client_website"] = client_website.strip()
    if quote_id.strip():
        payload["quote_id"] = quote_id.strip()
    if quote_crm_url.strip():
        payload["quote_crm_url"] = quote_crm_url.strip()
    if shared_folder_url.strip():
        payload["shared_folder_url"] = shared_folder_url.strip()
    if proposal_due_date is not None:
        payload["proposal_due_date"] = proposal_due_date.isoformat()
    if notes.strip():
        payload["notes"] = notes.strip()

    return payload


def main():
    """Renderiza el formulario de cualificación y envía la oportunidad a la API."""
    set_page_config()
    require_authentication()
    sidebar_header()
    page_header("Cualificar oportunidad", "Envía el formulario de cualificación de la oportunidad según metodología MEDDICC.")

    client = get_authenticated_api_client()

    needs_date = st.checkbox("¿Hay fecha para entregar oferta?", value=False, key="needs_date_toggle")
    proposal_due_date = None
    if needs_date:
        c_date, c_time = st.columns(2)
        with c_date:
            due_date = st.date_input("Fecha límite de entrega", value=date.today(), key="proposal_due_date_date")
        with c_time:
            due_time = st.time_input("Hora límite", value=time(18, 0), key="proposal_due_date_time")
        proposal_due_date = datetime.combine(due_date, due_time)

    with st.form("qualify_form"):
        payload = build_opportunity_payload_from_form(
            needs_date=needs_date,
            proposal_due_date=proposal_due_date,
        )

        #st.markdown("### Destinatarios (opcional, para emails)")
        #to_emails = st.text_input("To (separados por coma)", value="")
        #cc_emails = st.text_input("CC (separados por coma)", value="")

        submitted = st.form_submit_button("🚀 Cualificar", use_container_width=True)

    if submitted:
        # Validación mínima UI
        if not payload.get("client_name") or not payload.get("requester", {}).get("name") or not payload.get("description"):
            st.error("Rellena al menos: client_name, requester.name y description.")
            return

        #recipients = {
        #    "to": [e.strip() for e in to_emails.split(",") if e.strip()],
        #    "cc": [e.strip() for e in cc_emails.split(",") if e.strip()],
        #}

        json_expander("Payload enviado (OpportunityInput)", payload, expanded=False)

        try:
            with st.spinner("Ejecutando workflow multi-agente..."):
                result = client.qualify(opportunity=payload)
            show_envelope_result(result)
        except Exception as e:
            show_api_error(e)


if __name__ == "__main__":
    main()
