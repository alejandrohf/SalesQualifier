"""Funciones de renderizado reutilizable para resultados, errores y KPIs en Streamlit."""

from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st

def show_api_error(e: Exception):
    """Presenta de forma amigable un error devuelto por la API."""
    st.error(str(e))
    if hasattr(e, "detail"):
        with st.expander("Detalle"):
            st.write(getattr(e, "detail"))

def show_envelope_result(result: Dict[str, Any]):
    """Muestra el resultado devuelto por el endpoint de cualificación."""
    status = result.get("status")
    if status == "success":
        st.success(result.get("message", "Procesado correctamente"))
    else:
        st.warning("La API ha respondido sin marcar el proceso como satisfactorio.")

    cols = st.columns(3)
    cols[0].metric("Status", str(status))
    cols[1].metric("Opportunity ID", str(result.get("opportunity_id", "-")))
    cols[2].metric("Timestamp", str(result.get("timestamp", "")) if result.get("timestamp") else "-")

    st.divider()

    if "trace" in result and result["trace"]:
        with st.expander("Trazabilidad del workflow", expanded=False):
            st.write(result["trace"])

    if "result" in result and result["result"]:
        st.subheader("Resultado")
        st.json(result["result"], expanded=False)
    else:
        st.info("No hay campo 'result' en la respuesta.")

    analysis = result.get("analysis_reports") or {}
    agent_execution = result.get("agent_execution") or {}
    if agent_execution:
        st.subheader("⚙️ Ejecución de agentes")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Client Website Analyzer", str(agent_execution.get("client_website_analyzer", "-")))
        c2.metric("Risk Analyzer", str(agent_execution.get("risk_analyzer", "-")))
        c3.metric("Delivery Fit Analyzer", str(agent_execution.get("delivery_fit_analyzer", "-")))
        c4.metric("Commercial Fit Analyzer", str(agent_execution.get("commercial_fit_analyzer", "-")))

    if analysis:
        st.subheader("🧪 Análisis complementarios")
        risk = analysis.get("risk_report")
        delivery = analysis.get("delivery_fit_report")
        commercial = analysis.get("commercial_fit_report")

        if risk:
            with st.expander("Risk Analyzer", expanded=False):
                st.write(risk)
        if delivery:
            with st.expander("Delivery Fit Analyzer", expanded=False):
                st.write(delivery)
        if commercial:
            with st.expander("Commercial Fit Analyzer", expanded=False):
                st.write(commercial)

def json_expander(title: str, data: Any, expanded: bool = False):
    """Muestra un bloque JSON colapsable cuando existe contenido que inspeccionar."""
    if data is None:
        return
    with st.expander(title, expanded=expanded):
        st.json(data, expanded=False)


def kpi_row(items: List[Dict[str, Any]]):
    """Renderiza una fila de indicadores a partir de una lista de elementos."""
    cols = st.columns(len(items))
    for col, it in zip(cols, items):
        col.metric(label=it.get("label", ""), value=it.get("value", ""), help=it.get("help"))


def render_reference_matches(result_obj: Dict[str, Any]):
    """Representa las referencias semánticas devueltas en el resultado de cualificación."""
    refs = result_obj.get("reference_matches")
    if not refs:
        st.info("No se han encontrado referencias similares (RAG).")
        return

    st.subheader("Referencias similares")
    st.caption(f"Bonus aplicado al scoring: {refs.get('bonus_applied', 0.0)}")

    matches = refs.get("matches", [])
    if not matches:
        st.info("No hay matches de referencias.")
        return

    for m in matches:
        customer = m.get("customer", "")
        title = m.get("title", "")
        similarity = m.get("similarity", 0.0)
        header = f"{customer} — {title}  (sim={similarity:.2f})"

        with st.expander(header, expanded=False):
            why = m.get("why_similar", []) or []
            if why:
                st.write("**Por qué es similar:**")
                for b in why[:3]:
                    st.write(f"- {b}")

            snippet = m.get("best_chunk_snippet", "")
            if snippet:
                st.write("**Snippet más relevante:**")
                st.write(snippet)

            doc_url = m.get("document_url")
            if doc_url:
                st.link_button("📎 Abrir PDF", doc_url)
