"""Pantalla de consulta detallada del histórico de oportunidades procesadas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from interfaces.ui.components.auth import get_authenticated_api_client, require_authentication
from interfaces.ui.components.layout import (
    kpi_card,
    page_header,
    section,
    set_page_config,
    sidebar_header,
    styled_table,
)
from interfaces.ui.components.render import show_api_error


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .section-card {
            border: 1px solid var(--pc-border);
            border-radius: 14px;
            padding: 16px;
            background: rgba(255, 255, 255, 0.62);
            box-shadow: var(--pc-shadow-card);
            margin-bottom: 14px;
        }
        .section-title {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: .06em;
            color: var(--pc-text-muted);
            margin-bottom: 8px;
            font-weight: 700;
        }
        .kv-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 10px;
        }
        .kv-card {
            border: 1px solid var(--pc-border);
            border-radius: 10px;
            background: var(--pc-surface-soft);
            padding: 10px 12px;
        }
        .kv-label {
            color: var(--pc-text-muted);
            font-size: .78rem;
            margin-bottom: 4px;
        }
        .kv-value {
            color: var(--pc-text);
            font-size: .98rem;
            font-weight: 600;
            word-break: break-word;
        }
        .chip-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 6px;
            margin-bottom: 8px;
        }
        .chip {
            border-radius: 999px;
            padding: 4px 10px;
            font-size: .78rem;
            font-weight: 700;
            border: 1px solid transparent;
        }
        .chip-neutral { background: #eef2f7; color: #334155; border-color: #d9e2ec; }
        .chip-success { background: #eaf8f3; color: #0c7a5e; border-color: #cdeee3; }
        .chip-warning { background: #fff4df; color: #9a6408; border-color: #f4ddb0; }
        .chip-danger { background: #ffe9e9; color: #ab2525; border-color: #f6c8c8; }
        .panel-note {
            border: 1px solid var(--pc-border);
            border-left: 4px solid var(--pc-primary);
            border-radius: 10px;
            background: rgba(234, 248, 243, 0.8);
            padding: 10px 12px;
            color: var(--pc-text);
        }
        .mono-small { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: .85rem; }
        /* Reduce tamaño visual de st.metric en esta página */
        [data-testid="stMetricValue"] {
            font-size: 1.65rem !important;
            line-height: 1.1 !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.85rem !important;
        }
        /* Ajuste local para tabs de análisis en esta página */
        [data-testid="stTabs"] [data-baseweb="tab-panel"] {
            background: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(150, 177, 222, 0.34);
            border-radius: 10px;
            padding: 10px 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _fmt_dt(value: Any) -> str:
    if value in (None, "", "-"):
        return "-"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(value)


def _score_badge(value: Any) -> str:
    try:
        score = float(value)
    except Exception:
        return str(value)
    if score >= 8:
        return f"{score:.2f} (Alta)"
    if score >= 6:
        return f"{score:.2f} (Media)"
    return f"{score:.2f} (Baja)"


def _chip_class_for_technical(status: str) -> str:
    s = str(status).strip().lower()
    if s == "go":
        return "chip-success"
    if s == "no_go":
        return "chip-danger"
    return "chip-warning"


def _pretty_text(value: Any, fallback: str = "N/D") -> str:
    if value in (None, "", [], {}):
        return fallback
    return str(value)


def _render_full_detail(selected: dict[str, Any]) -> None:
    req = selected.get("request", {}) or {}
    resp = selected.get("response", {}) or {}
    scoring = (resp.get("scoring") or {})
    meddicc = (resp.get("meddicc_report") or {}).get("meddicc", {})
    meddicc_summary = (resp.get("meddicc_report") or {}).get("summary", {})
    refs = resp.get("reference_matches") or {}
    trace = selected.get("trace") or []

    tech_status = str(selected.get("technical_status", "pending"))
    tech_decider = str(
        selected.get("technical_decision_by_name")
        or selected.get("technical_decision_by_user_id")
        or "N/D"
    )
    st.markdown("#### Detalle completo")
    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-title">Resumen de oportunidad</div>
            <div class="kv-grid">
                <div class="kv-card"><div class="kv-label">Opportunity ID</div><div class="kv-value mono-small">{_pretty_text(selected.get('opportunity_id'), '-')}</div></div>
                <div class="kv-card"><div class="kv-label">Cliente</div><div class="kv-value">{_pretty_text(req.get('client_name'), '-')}</div></div>
                <div class="kv-card"><div class="kv-label">Cualificada en</div><div class="kv-value">{_fmt_dt(selected.get('timestamp'))}</div></div>
                <div class="kv-card"><div class="kv-label">Decisión técnica</div><div class="kv-value">{tech_status}</div></div>
                <div class="kv-card"><div class="kv-label">Decisión por</div><div class="kv-value">{tech_decider}</div></div>
                <div class="kv-card"><div class="kv-label">Fecha decisión</div><div class="kv-value">{_fmt_dt(selected.get('technical_decision_at'))}</div></div>
            </div>
            <div class="chip-row">
                <span class="chip { _chip_class_for_technical(tech_status) }">Technical {tech_status.upper()}</span>
                <span class="chip chip-neutral">Partner: {_pretty_text(req.get('partner'))}</span>
                <span class="chip chip-neutral">Área: {_pretty_text(req.get('main_area'))}</span>
                <span class="chip chip-neutral">Colaboración: {_pretty_text(req.get('collaboration_type'))}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if selected.get("technical_comment"):
        st.markdown(
            f"""
            <div class="panel-note">
                <strong>Comentario técnico:</strong> {_pretty_text(selected.get('technical_comment'))}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-card"><div class="section-title">Ficha de oportunidad</div>', unsafe_allow_html=True)
    f1, f2 = st.columns(2)
    with f1:
        st.write(f"**Web cliente:** {_pretty_text(req.get('client_website'))}")
        st.write(f"**Quote ID:** `{_pretty_text(req.get('quote_id'))}`")
        st.write(f"**CRM URL:** {_pretty_text(req.get('quote_crm_url'))}")
        st.write(f"**Carpeta compartida:** {_pretty_text(req.get('shared_folder_url'))}")
    with f2:
        st.write(f"**Partner:** {_pretty_text(req.get('partner'))}")
        st.write(f"**Tipo colaboración:** {_pretty_text(req.get('collaboration_type'))}")
        st.write(f"**Área:** {_pretty_text(req.get('main_area'))}")
        st.write(f"**Tamaño oferta:** {_pretty_text(req.get('deal_size'))}")
    st.markdown("**Descripción**")
    st.write(_pretty_text(req.get("description")))
    st.markdown("**Notas**")
    st.write(_pretty_text(req.get("notes")))
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card"><div class="section-title">Scoring</div>', unsafe_allow_html=True)
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Total score", str(scoring.get("total_score", "-")))
    sc2.metric("Nivel", str(scoring.get("qualification_level", "-")))
    sc3.metric("Acción", str(scoring.get("recommended_action", "-")))
    sc4.metric("Bonus refs", str(refs.get("bonus_applied", 0.0) if isinstance(refs, dict) else 0.0))
    st.write(f"**Ajustes aplicados:** `{scoring.get('adjustments', {})}`")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card"><div class="section-title">MEDDICC</div>', unsafe_allow_html=True)
    st.write(f"**Justificación score:** {_pretty_text(meddicc_summary.get('score_justification'))}")
    st.write(f"**Riesgos críticos Top 3:** {_pretty_text(meddicc_summary.get('critical_risks_top3'))}")
    st.write(f"**Siguientes pasos:** {_pretty_text(meddicc_summary.get('next_steps'))}")
    for dim_name, dim_payload in meddicc.items():
        with st.expander(f"Dimensión: {dim_name}", expanded=False):
            st.write(f"**Status:** {_pretty_text(dim_payload.get('status'))}")
            st.write(f"**Score:** {_pretty_text(dim_payload.get('score'))}")
            st.write(f"**Evidence:** {_pretty_text(dim_payload.get('evidence'))}")
            st.write(f"**Risks:** {_pretty_text(dim_payload.get('risks'))}")
            st.write(f"**Questions:** {_pretty_text(dim_payload.get('questions'))}")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card"><div class="section-title">Referencias similares</div>', unsafe_allow_html=True)
    matches = refs.get("matches", []) if isinstance(refs, dict) else []
    st.write(f"**Bonus aplicado:** `{refs.get('bonus_applied', 0.0) if isinstance(refs, dict) else 0.0}`")
    if matches:
        for m in matches:
            title = f"{m.get('customer', '')} — {m.get('title', '')}"
            with st.expander(title, expanded=False):
                st.write(f"**Similitud:** {m.get('similarity', 'N/D')}")
                st.write(f"**Razonamiento:** {_pretty_text(m.get('why_similar'))}")
                st.write(f"**Descripción:** {_pretty_text(m.get('best_chunk_snippet'))}")
                doc_url = _pretty_text(m.get("document_url"))
                if doc_url != "N/D":
                    st.markdown(f"**Documento:** [Abrir PDF]({doc_url})")
                else:
                    st.write("**Documento:** N/D")
    else:
        st.write("No hay referencias asociadas.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card"><div class="section-title">Análisis complementarios</div>', unsafe_allow_html=True)
    risk_tab, delivery_tab, commercial_tab = st.tabs(
        ["Risk Analyzer", "Delivery Fit Analyzer", "Commercial Fit Analyzer"]
    )
    with risk_tab:
        st.write(_pretty_text(resp.get("_workflow_risk_report"), "Sin contenido"))
    with delivery_tab:
        st.write(_pretty_text(resp.get("_workflow_delivery_fit_report"), "Sin contenido"))
    with commercial_tab:
        st.write(_pretty_text(resp.get("_workflow_commercial_fit_report"), "Sin contenido"))
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Trace técnico", expanded=False):
        st.write(f"**Ejecución de agentes:** {resp.get('_workflow_agent_execution', {})}")
        st.write(trace)


def main():
    """Muestra el listado de oportunidades y el detalle enriquecido de cada registro."""
    set_page_config()
    require_authentication()
    sidebar_header()
    _inject_styles()
    page_header("Oportunidades", "Histórico persistido con scoring y análisis complementarios.")

    client = get_authenticated_api_client()

    try:
        data = client.list_opportunities()
    except Exception as e:
        show_api_error(e)
        return

    opps = data.get("opportunities", [])
    total = int(data.get("total_opportunities", len(opps)) or len(opps))
    pending_count = sum(1 for o in opps if str(o.get("technical_status", "pending")) == "pending")
    go_count = sum(1 for o in opps if str(o.get("technical_status", "")) == "go")
    nogo_count = sum(1 for o in opps if str(o.get("technical_status", "")) == "no_go")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Total oportunidades", str(total), variant="neutral")
    with c2:
        kpi_card("Pendientes Revisión Ingeniería", str(pending_count), variant="warning")
    with c3:
        kpi_card("Technical GO", str(go_count), variant="success")
    with c4:
        kpi_card("Technical NO GO", str(nogo_count), variant="danger")

    st.divider()

    if not opps:
        st.info("Aún no hay oportunidades procesadas. Ve a la página 'Qualify' para crear la primera.")
        return

    rows = []
    for idx, item in enumerate(opps):
        rid = item.get("opportunity_id", "-")
        ts = _fmt_dt(item.get("timestamp", "-"))
        req = item.get("request", {}) or {}
        resp = item.get("response", {}) or {}
        scoring = (resp.get("scoring") or resp.get("result", {}).get("scoring") or {})

        rows.append(
            {
                "_row_idx": idx,
                "opportunity_id": rid,
                "timestamp": ts,
                "client_name": req.get("client_name", "-"),
                "quote_id": req.get("quote_id", "-"),
                "collaboration_type": req.get("collaboration_type", "-"),
                "main_area": req.get("main_area", "-"),
                "qualification_level": scoring.get("qualification_level", "-"),
                "total_score": _score_badge(scoring.get("total_score", "-")),
                "recommended_action": scoring.get("recommended_action", "-"),
                "technical_status": item.get("technical_status", "pending"),
            }
        )

    section("Listado")
    f1, f2, f3, f4, f5 = st.columns([2, 1, 1, 1, 1])
    with f1:
        q = st.text_input("Búsqueda", placeholder="Cliente, Opportunity ID o Quote ID")
    with f2:
        collab_values = sorted({str(r.get("collaboration_type", "-")) for r in rows})
        collab_filter = st.multiselect("Tipo colaboración", collab_values)
    with f3:
        area_values = sorted({str(r.get("main_area", "-")) for r in rows})
        area_filter = st.multiselect("Área", area_values)
    with f4:
        level_values = sorted({str(r.get("qualification_level", "-")) for r in rows})
        level_filter = st.multiselect("Nivel", level_values)
    with f5:
        tech_filter = st.multiselect("Estado técnico", ["pending", "go", "no_go"])

    filtered_rows = rows
    if q.strip():
        ql = q.strip().lower()
        filtered_rows = [
            r for r in filtered_rows
            if ql in str(r.get("client_name", "")).lower()
            or ql in str(r.get("opportunity_id", "")).lower()
            or ql in str(r.get("quote_id", "")).lower()
        ]
    if collab_filter:
        allowed = set(collab_filter)
        filtered_rows = [r for r in filtered_rows if str(r.get("collaboration_type", "-")) in allowed]
    if area_filter:
        allowed = set(area_filter)
        filtered_rows = [r for r in filtered_rows if str(r.get("main_area", "-")) in allowed]
    if level_filter:
        allowed = set(level_filter)
        filtered_rows = [r for r in filtered_rows if str(r.get("qualification_level", "-")) in allowed]
    if tech_filter:
        allowed = set(tech_filter)
        filtered_rows = [r for r in filtered_rows if str(r.get("technical_status", "pending")) in allowed]

    st.caption(f"Mostrando {len(filtered_rows)} de {len(rows)} oportunidades")
    if not filtered_rows:
        st.info("No hay oportunidades que cumplan los filtros.")
        return

    p1, p2, p3 = st.columns([1, 1, 2])
    with p1:
        page_size = st.selectbox("Filas por página", [5, 10, 20, 50], index=1)
    total_pages = max(1, (len(filtered_rows) + page_size - 1) // page_size)
    with p2:
        page = st.number_input("Página", min_value=1, max_value=total_pages, value=1, step=1)

    start = (int(page) - 1) * page_size
    end = start + page_size
    page_rows = filtered_rows[start:end]

    df = pd.DataFrame(
        [
            {
                "opportunity_id": r["opportunity_id"],
                "timestamp": r["timestamp"],
                "client_name": r["client_name"],
                "quote_id": r["quote_id"],
                "collaboration_type": r["collaboration_type"],
                "main_area": r["main_area"],
                "qualification_level": r["qualification_level"],
                "total_score": r["total_score"],
                "recommended_action": r["recommended_action"],
                "technical_status": r["technical_status"],
            }
            for r in page_rows
        ]
    )

    selected_idx = None
    try:
        event = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
        )
        selected_rows = getattr(event, "selection", {}).rows if hasattr(event, "selection") else []
        if selected_rows:
            selected_idx = page_rows[selected_rows[0]]["_row_idx"]
            st.session_state["selected_opp_idx"] = selected_idx
    except TypeError:
        styled_table(df)

    if selected_idx is None:
        selected_idx = st.session_state.get("selected_opp_idx")

    st.caption(f"Total páginas: {total_pages}")

    st.divider()

    section("Detalle")
    if selected_idx is None or not isinstance(selected_idx, int) or not (0 <= selected_idx < len(opps)):
        sel = st.selectbox(
            "Selecciona una oportunidad para ver detalle",
            options=list(range(len(opps))),
            format_func=lambda i: f"{opps[i].get('opportunity_id','-')} — {opps[i].get('request',{}).get('client_name','-')}",
        )
        selected_idx = sel
        st.session_state["selected_opp_idx"] = selected_idx

    selected: dict[str, Any] = opps[selected_idx]
    me = st.session_state.get("auth_user") or {}

    section("Engineering Qualification")
    if me.get("can_engineering") and str(selected.get("technical_status", "pending")) == "pending":
        comment = st.text_area("Comentario técnico (obligatorio para NO GO)", key=f"tech_comment_{selected.get('opportunity_id')}")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("GO", use_container_width=True):
                try:
                    client.set_technical_decision(str(selected.get("opportunity_id")), decision="go")
                    st.success("Technical GO registrado.")
                    st.rerun()
                except Exception as e:
                    show_api_error(e)
        with b2:
            if st.button("NO GO", use_container_width=True):
                if not comment.strip():
                    st.error("Debes añadir comentario para NO GO.")
                else:
                    try:
                        client.set_technical_decision(
                            str(selected.get("opportunity_id")),
                            decision="no_go",
                            comment=comment.strip(),
                        )
                        st.success("Technical NO GO registrado.")
                        st.rerun()
                    except Exception as e:
                        show_api_error(e)
    else:
        st.caption("No hay acción técnica disponible para esta oportunidad o para tu perfil.")

    _render_full_detail(selected)


if __name__ == "__main__":
    main()
