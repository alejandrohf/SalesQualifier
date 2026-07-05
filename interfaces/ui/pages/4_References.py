"""Gestión del catálogo de referencias y búsqueda semántica desde la interfaz web."""

from __future__ import annotations

from collections import Counter
from typing import Any

import altair as alt
import streamlit as st

from interfaces.ui.components.auth import get_authenticated_api_client, require_authentication
from interfaces.ui.components.layout import page_header, section, set_page_config, sidebar_header
from interfaces.ui.components.render import json_expander, show_api_error

INDUSTRIES = [
    "Legal & Business Services",
    "Financial Services & Insurance",
    "Real Estate",
    "Consumer Goods & Retail",
    "Energy, Utilities & Natural Resources",
    "Automotive",
    "Engineering, Manufacturing & Construction",
    "Defense, Security & Aerospace",
    "Government & Public Services",
    "Healthcare, Pharma & Biotech",
    "Education",
    "Nonprofit",
    "Transport & Logistics",
    "Hospitality & Leisure",
    "Media & Telecommunications",
    "Technology Services & Platforms",
    "Other",
]

AREAS = [
    "Artificial Intelligence",
    "Security",
    "Development",
    "Data",
    "Consultancy",
    "Infrastructure",
    "Extended Reality",
    "Mobile",
    "Other",
]

CLOUDS = ["Azure", "Google Cloud", "AWS", "No Cloud"]
SIZES = ["XS", "S", "M", "L", "XL"]


def _build_assistant_reply(search_data: dict[str, Any], api_base_url: str) -> str:
    hits = search_data.get("hits", []) or []
    if not hits:
        return (
            "No encontré referencias similares para esa consulta. "
            "Prueba con más contexto de sector, stack tecnológico y objetivo del proyecto."
        )

    base = api_base_url.rstrip("/")
    lines: list[str] = [f"He encontrado {len(hits)} referencias similares:"]
    for i, h in enumerate(hits[:5], start=1):
        sim = float(h.get("similarity", 0.0) or 0.0)
        customer = h.get("customer", "Cliente")
        title = h.get("title", "Referencia")
        doc_url = h.get("document_url", "")
        snippet = (h.get("chunk_text", "") or "").strip().replace("\n", " ")
        if len(snippet) > 180:
            snippet = snippet[:180] + "..."

        lines.append(f"{i}. **{customer}** — {title} (sim={sim:.2f})")
        if snippet:
            lines.append(f"   {snippet}")
        if doc_url:
            full_url = doc_url if str(doc_url).startswith("http") else f"{base}{doc_url}"
            lines.append(f"   [Abrir PDF]({full_url})")

    return "\n".join(lines)


def main():
    """Renderiza la operativa de alta, búsqueda, descarga y reindexación de referencias."""
    set_page_config()
    require_authentication()
    sidebar_header()
    page_header("Customer References")

    client = get_authenticated_api_client()

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        section("Subir nueva referencia")
        with st.form("reference_upload_form", clear_on_submit=True):
            title = st.text_input("Title", placeholder="Cliente + título del caso (ej: Repsol – Optimización geológica 3D)")
            customer = st.text_input("Customer", placeholder="Nombre del cliente")
            industry = st.selectbox("Industry", INDUSTRIES, index=INDUSTRIES.index("Other"))
            area = st.selectbox("Area", AREAS, index=AREAS.index("Other"))
            cloud = st.selectbox("Cloud", CLOUDS, index=0)
            size = st.selectbox("Size", SIZES, index=2)

            pdf = st.file_uploader("Documento PDF", type=["pdf"])
            submit = st.form_submit_button("Create + Index (Background)", use_container_width=True)

        if submit:
            if not title.strip() or not customer.strip():
                st.error("Title y Customer son obligatorios.")
            elif not pdf:
                st.error("Debes subir un PDF.")
            else:
                try:
                    res = client.create_reference(
                        title=title.strip(),
                        customer=customer.strip(),
                        industry=industry,
                        area=area,
                        cloud=cloud,
                        size=size,
                        pdf_bytes=pdf.getvalue(),
                        pdf_filename=pdf.name or "reference.pdf",
                    )
                    st.success(f"Referencia creada: {res.get('reference_id')} (indexación programada).")
                    json_expander("Respuesta API", res, expanded=False)
                except Exception as e:
                    show_api_error(e)

    with col2:
        section("Chat de referencias")
        
        if "references_chat_messages" not in st.session_state:
            st.session_state["references_chat_messages"] = [
                {
                    "role": "assistant",
                    "content": (
                        "Cuéntame el caso (cliente, sector, stack, objetivo) y te devuelvo referencias similares."
                    ),
                }
            ]

        if st.button("🧹 Limpiar chat", use_container_width=True):
            st.session_state["references_chat_messages"] = [
                {
                    "role": "assistant",
                    "content": (
                        "Cuéntame el caso (cliente, sector, stack, objetivo) y te devuelvo referencias similares."
                    ),
                }
            ]

        chat_box = st.container(border=True, height=560)
        with chat_box:
            for msg in st.session_state["references_chat_messages"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        prompt = st.chat_input("Ej: Plataforma de datos en Azure + optimización logística con IA")
        if prompt:
            st.session_state["references_chat_messages"].append({"role": "user", "content": prompt})
            try:
                data = client.search_references(prompt.strip())
                assistant_text = _build_assistant_reply(data, client.cfg.base_url)
                st.session_state["references_chat_messages"].append(
                    {"role": "assistant", "content": assistant_text}
                )
            except Exception as e:
                st.session_state["references_chat_messages"].append(
                    {"role": "assistant", "content": f"Error consultando referencias: {e}"}
                )
            st.rerun()

    st.divider()
    section("Lista de referencias")

    try:
        refs = client.list_references(limit=200, offset=0)
    except Exception as e:
        show_api_error(e)
        return

    if not refs:
        st.info("No hay referencias todavía.")
        return

    section("Distribución por área de solución")
    area_counts = Counter(str(r.get("area") or "Unknown") for r in refs)
    area_values = [{"area": area, "total": total} for area, total in area_counts.items()]
    area_chart = (
        alt.Chart(alt.Data(values=area_values))
        .mark_bar()
        .encode(
            x=alt.X("area:N", title="", axis=alt.Axis(labelAngle=0, labelLimit=220)),
            y=alt.Y("total:Q", title="Número de referencias"),
            color=alt.Color(
                "area:N",
                title=None,
                legend=alt.Legend(orient="top", direction="horizontal", symbolType="square"),
            ),
            tooltip=["area:N", "total:Q"],
        )
        .properties(height=280)
    )
    st.altair_chart(area_chart, use_container_width=True)

    section("Filtros")
    f1, f2, f3 = st.columns(3)
    with f1:
        search_text = st.text_input("Buscar por cliente o título", placeholder="Ej: Repsol, Azure, logística")
        industry_options = sorted({str(r.get("industry", "")) for r in refs if r.get("industry")})
        selected_industries = st.multiselect("Industry", options=industry_options)
    with f2:
        area_options = sorted({str(r.get("area", "")) for r in refs if r.get("area")})
        selected_areas = st.multiselect("Area", options=area_options)
        cloud_options = sorted({str(r.get("cloud", "")) for r in refs if r.get("cloud")})
        selected_clouds = st.multiselect("Cloud", options=cloud_options)
    with f3:
        size_options = sorted({str(r.get("size", "")) for r in refs if r.get("size")})
        selected_sizes = st.multiselect("Size", options=size_options)
        indexing_status = st.selectbox("Estado de indexación", ["Todos", "Indexadas", "Pendientes"], index=0)

    filtered_refs = refs
    if search_text.strip():
        q = search_text.strip().lower()
        filtered_refs = [
            r
            for r in filtered_refs
            if q in str(r.get("customer", "")).lower() or q in str(r.get("title", "")).lower()
        ]
    if selected_industries:
        allowed = set(selected_industries)
        filtered_refs = [r for r in filtered_refs if str(r.get("industry", "")) in allowed]
    if selected_areas:
        allowed = set(selected_areas)
        filtered_refs = [r for r in filtered_refs if str(r.get("area", "")) in allowed]
    if selected_clouds:
        allowed = set(selected_clouds)
        filtered_refs = [r for r in filtered_refs if str(r.get("cloud", "")) in allowed]
    if selected_sizes:
        allowed = set(selected_sizes)
        filtered_refs = [r for r in filtered_refs if str(r.get("size", "")) in allowed]
    if indexing_status == "Indexadas":
        filtered_refs = [r for r in filtered_refs if r.get("indexed_at")]
    elif indexing_status == "Pendientes":
        filtered_refs = [r for r in filtered_refs if not r.get("indexed_at")]

    st.caption(f"Mostrando {len(filtered_refs)} de {len(refs)} referencias")
    if not filtered_refs:
        st.info("No hay referencias que cumplan los filtros actuales.")
        return

    for r in filtered_refs:
        ref_id = r.get("id")
        header = f"{r.get('customer', '')} — {r.get('title', '')}  (v{r.get('document_version', 1)})"
        with st.expander(header, expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            c1.write(f"**Industry:** {r.get('industry')}")
            c2.write(f"**Area:** {r.get('area')}")
            c3.write(f"**Cloud:** {r.get('cloud')}")
            c4.write(f"**Size:** {r.get('size')}")

            st.write(f"**Indexed at:** {r.get('indexed_at')}")
            st.write(f"**Updated at:** {r.get('updated_at')}")

            btns = st.columns([1, 1, 2])
            with btns[0]:
                if st.button("🔁 Reindex", key=f"reindex_{ref_id}", use_container_width=True):
                    try:
                        res = client.reindex_reference(str(ref_id))
                        st.success("Reindex programado.")
                        json_expander("Respuesta API", res, expanded=False)
                    except Exception as e:
                        show_api_error(e)

            with btns[1]:
                if ref_id:
                    st.link_button("📎 Abrir PDF", client.reference_download_url(str(ref_id)), use_container_width=True)

            with btns[2]:
                json_expander("Ver JSON", r, expanded=False)


if __name__ == "__main__":
    main()
