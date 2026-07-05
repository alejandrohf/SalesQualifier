"""Dashboard operativo con KPIs, embudos y distribución de oportunidades cualificadas."""

from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

import altair as alt
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

TIME_WINDOWS = {
    "Última semana": 7,
    "Último mes": 30,
    "Último año": 365,
    "Todo histórico": None,
}


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _normalize_row(item: dict[str, Any]) -> dict[str, Any]:
    req = item.get("request", {}) or {}
    resp = item.get("response", {}) or {}
    scoring = resp.get("scoring", {}) or {}
    refs = resp.get("reference_matches", {}) or {}
    ref_matches = refs.get("matches", []) if isinstance(refs, dict) else []

    ts = _to_utc(_parse_iso(item.get("timestamp")))
    technical_decision_at = _to_utc(_parse_iso(item.get("technical_decision_at")))
    date_str = ts.date().isoformat() if ts else "unknown"
    raw_client_name = str(req.get("client_name", "-") or "-")
    client_name = re.sub(r"\s+#\d+\s*$", "", raw_client_name).strip() or raw_client_name

    return {
        "opportunity_id": item.get("opportunity_id", "-"),
        "timestamp": ts,
        "timestamp_raw": item.get("timestamp"),
        "date": date_str,
        "client_name": client_name,
        "main_area": req.get("main_area", "-"),
        "partner": req.get("partner", "-"),
        "deal_size": req.get("deal_size", "-"),
        "collaboration_type": req.get("collaboration_type", "-"),
        "score": float(scoring.get("total_score", 0.0) or 0.0),
        "qualification_level": scoring.get("qualification_level", "unknown"),
        "recommended_action": scoring.get("recommended_action", "unknown"),
        "has_refs": bool(ref_matches),
        "refs_count": len(ref_matches) if isinstance(ref_matches, list) else 0,
        "refs_bonus": float(refs.get("bonus_applied", 0.0) or 0.0) if isinstance(refs, dict) else 0.0,
        "technical_status": item.get("technical_status", "pending"),
        "technical_decision_at": technical_decision_at,
        "technical_decision_at_raw": item.get("technical_decision_at"),
        "created_by_user_id": item.get("created_by_user_id"),
        "created_by_email": item.get("created_by_email"),
        "technical_decision_by_user_id": item.get("technical_decision_by_user_id"),
        "technical_decision_by_name": item.get("technical_decision_by_name"),
        "has_client_website": bool(str(req.get("client_website") or "").strip()),
        "has_quote_id": bool(str(req.get("quote_id") or "").strip()),
        "has_quote_crm_url": bool(str(req.get("quote_crm_url") or "").strip()),
        "has_due_date": bool(str(req.get("proposal_due_date") or "").strip()),
    }


def _filter_by_days(rows: list[dict[str, Any]], days: int | None) -> list[dict[str, Any]]:
    if days is None:
        return rows
    cutoff = datetime.now(UTC) - timedelta(days=days)
    return [r for r in rows if r["timestamp"] and r["timestamp"] >= cutoff]


def _count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    c = Counter(r.get(key, "unknown") for r in rows)
    return dict(sorted(c.items(), key=lambda kv: kv[1], reverse=True))


def _avg_score(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    return round(sum(r["score"] for r in rows) / len(rows), 2)


def _score_bucket(score: float) -> str:
    if score >= 8.0:
        return "8-10"
    if score >= 6.0:
        return "6-7.99"
    return "0-5.99"


def _fmt_action(action: str) -> str:
    mapping = {
        "do_not_prioritize": "No Priorizar",
        "invest_pre_sales": "Invertir en Preventa",
        "invest_in_presales": "Invertir en Preventa",
        "request_more_info": "Solicitar Más Información",
    }
    return mapping.get(str(action), str(action))


def _fmt_dt_display(value: str | None) -> str:
    if not value:
        return "N/D"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(value)


def _avg_hours_between(rows: list[dict[str, Any]], start_key: str, end_key: str) -> float | None:
    deltas_h: list[float] = []
    for row in rows:
        start = row.get(start_key)
        end = row.get(end_key)
        if isinstance(start, datetime) and isinstance(end, datetime) and end >= start:
            deltas_h.append((end - start).total_seconds() / 3600.0)
    if not deltas_h:
        return None
    return round(sum(deltas_h) / len(deltas_h), 1)


def _render_altair_bar(data: dict[str, int], y_title: str, height: int = 260) -> None:
    categories = list(data.keys())
    values = [{"categoria": k, "valor": int(v)} for k, v in data.items()]
    chart = (
        alt.Chart(alt.Data(values=values))
        .mark_bar()
        .encode(
            x=alt.X("categoria:N", title="", sort=categories, axis=alt.Axis(labelAngle=0, labelLimit=220)),
            y=alt.Y("valor:Q", title=y_title),
            color=alt.Color(
                "categoria:N",
                title=None,
                legend=alt.Legend(orient="top", direction="horizontal", symbolType="square"),
            ),
            tooltip=["categoria:N", "valor:Q"],
        )
        .properties(height=height)
    )
    st.altair_chart(chart, use_container_width=True)


def _pct(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((part / total) * 100.0, 1)


def main():
    """Renderiza el dashboard principal y sus filtros temporales, técnicos y comerciales."""
    set_page_config()
    require_authentication()
    sidebar_header()
    page_header(
        "Dashboard Comercial",
        "KPIs operativos de cualificación, scoring y uso de referencias para seguimiento del pipeline.",
    )

    client = get_authenticated_api_client()

    try:
        opportunities_payload = client.list_opportunities()
        references = client.list_references(limit=500, offset=0)
    except Exception as e:
        show_api_error(e)
        return
    try:
        users_payload = client.list_users()
        users = users_payload.get("users", []) if isinstance(users_payload, dict) else []
    except Exception:
        users = []

    raw_rows = opportunities_payload.get("opportunities", [])
    rows = [_normalize_row(r) for r in raw_rows]

    if not rows:
        st.info("Aún no hay oportunidades procesadas. Ve a Qualify para generar datos.")
        return

    col_filters_1, col_filters_2, col_filters_3 = st.columns([1.4, 1.2, 1.2])
    with col_filters_1:
        selected_window_label = st.selectbox("Ventana temporal", list(TIME_WINDOWS.keys()), index=1)
    with col_filters_2:
        selected_area = st.selectbox(
            "Área",
            ["Todas"] + sorted({r["main_area"] for r in rows if r["main_area"] not in (None, "-", "")}),
            index=0,
        )
    with col_filters_3:
        selected_partner = st.selectbox(
            "Partner",
            ["Todos"] + sorted({r["partner"] for r in rows if r["partner"] not in (None, "-", "")}),
            index=0,
        )

    filtered = _filter_by_days(rows, TIME_WINDOWS[selected_window_label])
    if selected_area != "Todas":
        filtered = [r for r in filtered if r["main_area"] == selected_area]
    if selected_partner != "Todos":
        filtered = [r for r in filtered if r["partner"] == selected_partner]

    user_name_by_id: dict[str, str] = {}
    for u in users:
        user_id = str(u.get("id") or "").strip()
        if not user_id:
            continue
        full_name = f"{str(u.get('first_name') or '').strip()} {str(u.get('last_name') or '').strip()}".strip()
        email = str(u.get("email") or "").strip()
        user_name_by_id[user_id] = full_name or email or user_id

    for row in filtered:
        creator_id = str(row.get("created_by_user_id") or "").strip()
        creator_email = str(row.get("created_by_email") or "").strip()
        row["sales_owner"] = user_name_by_id.get(creator_id) or creator_email or creator_id or "Sin asignar"

        reviewer_id = str(row.get("technical_decision_by_user_id") or "").strip()
        reviewer_name = str(row.get("technical_decision_by_name") or "").strip()
        row["engineering_owner"] = reviewer_name or user_name_by_id.get(reviewer_id) or reviewer_id or "Sin revisión"

        row["input_fields_complete"] = int(
            bool(row.get("has_client_website"))
            + bool(row.get("has_quote_id"))
            + bool(row.get("has_quote_crm_url"))
            + bool(row.get("has_due_date"))
        )
        row["input_complete"] = row["input_fields_complete"] == 4

    total = len(filtered)
    invest_count = sum(1 for r in filtered if r["recommended_action"] == "invest_pre_sales")
    with_refs_count = sum(1 for r in filtered if r["has_refs"])
    high_count = sum(1 for r in filtered if r["qualification_level"] == "high")
    medium_count = sum(1 for r in filtered if r["qualification_level"] == "medium")
    low_count = sum(1 for r in filtered if r["qualification_level"] == "low")
    tech_pending = sum(1 for r in filtered if r.get("technical_status") == "pending")
    tech_go = sum(1 for r in filtered if r.get("technical_status") == "go")
    tech_no_go = sum(1 for r in filtered if r.get("technical_status") == "no_go")

    k1, k2, k3, k4, k5, k6, k7, k8, k9 = st.columns(9)
    with k1:
        kpi_card("Oportunidades", str(total), variant="neutral")
    with k2:
        kpi_card("Score medio", f"{_avg_score(filtered):.2f}", variant="warning")
    with k3:
        kpi_card("A preventa", f"{invest_count}", variant="success")
    with k4:
        kpi_card("Con referencias", f"{with_refs_count}", variant="neutral")
    with k5:
        kpi_card("Caulif. Alta", str(high_count), variant="success")
    with k6:
        kpi_card("Referencias", str(len(references)), variant="neutral")
    with k7:
        kpi_card("Pending Eng", str(tech_pending), variant="warning")
    with k8:
        kpi_card("Tech GO", str(tech_go), variant="success")
    with k9:
        kpi_card("Tech NO GO", str(tech_no_go), variant="danger")

    st.divider()

    section("Embudo de cualificación por usuario")
    sales_options = sorted({str(r.get("sales_owner") or "Sin asignar") for r in filtered})
    selected_sales_owner = st.selectbox("Usuario de ventas", ["Todos"] + sales_options, index=0)
    funnel_rows = filtered if selected_sales_owner == "Todos" else [r for r in filtered if r["sales_owner"] == selected_sales_owner]

    funnel_total = len(funnel_rows)
    funnel_qualified_count = sum(1 for r in funnel_rows if r.get("score", 0.0) > 0.0)
    funnel_tech_pending = sum(1 for r in funnel_rows if r.get("technical_status") == "pending")
    funnel_tech_go = sum(1 for r in funnel_rows if r.get("technical_status") == "go")
    funnel_tech_no_go = sum(1 for r in funnel_rows if r.get("technical_status") == "no_go")
    funnel_conversion_rate = _pct(funnel_tech_go, funnel_qualified_count)
    funnel_pending_rate = _pct(funnel_tech_pending, funnel_qualified_count)
    funnel_avg_q_to_tech_h = _avg_hours_between(funnel_rows, "timestamp", "technical_decision_at")

    funnel_cols = st.columns(5)
    with funnel_cols[0]:
        kpi_card("Creadas", str(funnel_total), variant="neutral")
    with funnel_cols[1]:
        kpi_card("Cualificadas", str(funnel_qualified_count), variant="neutral")
    with funnel_cols[2]:
        kpi_card("Pendientes GO/NO GO", f"{funnel_tech_pending} ({funnel_pending_rate}%)", variant="warning")
    with funnel_cols[3]:
        kpi_card("GO", f"{funnel_tech_go} ({funnel_conversion_rate}% conv.)", variant="success")
    with funnel_cols[4]:
        kpi_card(
            "Tiempo medio Cualificación→Técnica",
            f"{funnel_avg_q_to_tech_h:.1f} h" if funnel_avg_q_to_tech_h is not None else "N/D",
            variant="neutral",
        )

    funnel_order = ["Creada", "Cualificada", "Pendientes", "GO", "NO GO"]
    funnel_data = [
        {"etapa": "Creada", "valor": funnel_total},
        {"etapa": "Cualificada", "valor": funnel_qualified_count},
        {"etapa": "Pendientes", "valor": funnel_tech_pending},
        {"etapa": "GO", "valor": funnel_tech_go},
        {"etapa": "NO GO", "valor": funnel_tech_no_go},
    ]
    funnel_color_scale = alt.Scale(
        domain=funnel_order,
        range=["#1d63c8", "#7ab5ef", "#2db4a6", "#ff3b30", "#f8a9b3"],
    )
    funnel_max = max((row["valor"] for row in funnel_data), default=0)
    funnel_chart = (
        alt.Chart(alt.Data(values=funnel_data))
        .mark_bar(size=70, cornerRadiusTopLeft=8, cornerRadiusTopRight=8, opacity=0.95)
        .encode(
            x=alt.X("etapa:N", title="", sort=funnel_order, axis=alt.Axis(labelAngle=0, labelLimit=220)),
            y=alt.Y(
                "valor:Q",
                title="Número de oportunidades",
                scale=alt.Scale(domain=[0, max(funnel_max, 1)]),
            ),
            color=alt.Color(
                "etapa:N",
                title=None,
                scale=funnel_color_scale,
                legend=alt.Legend(orient="top", direction="horizontal", symbolType="square"),
            ),
            tooltip=[
                alt.Tooltip("etapa:N", title="Etapa"),
                alt.Tooltip("valor:Q", title="Oportunidades"),
            ],
        )
        .properties(height=320)
    )
    st.altair_chart(funnel_chart, use_container_width=True)

    stage_col_1, stage_col_2, stage_col_3 = st.columns(3)
    stage_col_1.metric(
        "Tiempo medio Creación→Cualificación",
        "N/D",
        "Se registra la oportunidad ya cualificada",
    )
    stage_col_2.metric(
        "Tiempo medio Cualificación→GO/NO GO",
        f"{funnel_avg_q_to_tech_h:.1f} h" if funnel_avg_q_to_tech_h is not None else "N/D",
    )
    stage_col_3.metric("Tasa GO sobre cualificadas", f"{funnel_conversion_rate}%")

    st.divider()

    left, right = st.columns([1, 1])
    with left:
        section("Cualificación")
        qual_counts = {"Alta": high_count, "Media": medium_count, "Baja": low_count}
        _render_altair_bar(qual_counts, y_title="Número de oportunidades")

        section("Acción recomendada")
        action_counts_raw = _count_by(filtered, "recommended_action")
        action_counts = {_fmt_action(k): v for k, v in action_counts_raw.items()}
        _render_altair_bar(action_counts, y_title="Número de oportunidades")

    with right:
        section("Pipeline por score")
        score_buckets = Counter(_score_bucket(r["score"]) for r in filtered)
        _render_altair_bar(dict(score_buckets), y_title="Número de oportunidades")

        section("Cobertura de referencias")
        _render_altair_bar(
            {"Con referencias": with_refs_count, "Sin referencias": max(0, total - with_refs_count)},
            y_title="Número de oportunidades",
        )

    st.divider()

    section("Ranking de usuarios de ventas")
    sales_stats: dict[str, dict[str, float]] = {}
    for row in filtered:
        owner = str(row.get("sales_owner") or "Sin asignar")
        status = str(row.get("technical_status") or "pending").lower().strip()
        if owner not in sales_stats:
            sales_stats[owner] = {
                "opportunities": 0,
                "score_sum": 0.0,
                "high_count": 0,
                "go": 0,
                "no_go": 0,
                "pending": 0,
            }
        sales_stats[owner]["opportunities"] += 1
        sales_stats[owner]["score_sum"] += float(row.get("score", 0.0) or 0.0)
        if row.get("qualification_level") == "high":
            sales_stats[owner]["high_count"] += 1
        if status == "go":
            sales_stats[owner]["go"] += 1
        elif status == "no_go":
            sales_stats[owner]["no_go"] += 1
        else:
            sales_stats[owner]["pending"] += 1

    sales_ranking = sorted(
        (
            {
                "usuario_ventas": owner,
                "oportunidades_creadas": int(stats["opportunities"]),
                "score_medio": round(float(stats["score_sum"]) / int(stats["opportunities"]), 2)
                if int(stats["opportunities"]) > 0
                else 0.0,
                "%_alta_cualificacion": _pct(int(stats["high_count"]), int(stats["opportunities"])),
                "go": int(stats["go"]),
                "no_go": int(stats["no_go"]),
                "pendientes": int(stats["pending"]),
            }
            for owner, stats in sales_stats.items()
        ),
        key=lambda x: (x["oportunidades_creadas"], x["go"], -x["pendientes"]),
        reverse=True,
    )
    styled_table(sales_ranking)
    _render_altair_bar(
        {r["usuario_ventas"]: int(r["oportunidades_creadas"]) for r in sales_ranking[:10]},
        y_title="Oportunidades creadas",
    )

    st.divider()

    section("Ranking de engineering")
    engineering_stats: dict[str, dict[str, float]] = {}
    for row in filtered:
        status = str(row.get("technical_status") or "pending").lower().strip()
        if status not in {"go", "no_go"}:
            continue
        owner = str(row.get("engineering_owner") or "Sin revisión")
        if owner not in engineering_stats:
            engineering_stats[owner] = {"reviewed": 0, "go": 0, "no_go": 0, "decision_hours_sum": 0.0, "timed": 0}
        engineering_stats[owner]["reviewed"] += 1
        if status == "go":
            engineering_stats[owner]["go"] += 1
        else:
            engineering_stats[owner]["no_go"] += 1
        start = row.get("timestamp")
        end = row.get("technical_decision_at")
        if isinstance(start, datetime) and isinstance(end, datetime) and end >= start:
            engineering_stats[owner]["decision_hours_sum"] += (end - start).total_seconds() / 3600.0
            engineering_stats[owner]["timed"] += 1

    engineering_ranking = sorted(
        (
            {
                "usuario_engineering": owner,
                "oportunidades_revisadas": int(stats["reviewed"]),
                "%_go": _pct(int(stats["go"]), int(stats["reviewed"])),
                "%_no_go": _pct(int(stats["no_go"]), int(stats["reviewed"])),
                "tiempo_medio_decision_h": round(float(stats["decision_hours_sum"]) / int(stats["timed"]), 1)
                if int(stats["timed"]) > 0
                else None,
            }
            for owner, stats in engineering_stats.items()
        ),
        key=lambda x: (x["oportunidades_revisadas"], x["%_go"]),
        reverse=True,
    )
    if engineering_ranking:
        styled_table(engineering_ranking)
        _render_altair_bar(
            {r["usuario_engineering"]: int(r["oportunidades_revisadas"]) for r in engineering_ranking[:10]},
            y_title="Oportunidades revisadas",
        )
    else:
        st.info("No hay revisiones técnicas (GO/NO GO) en el filtro actual.")

    st.divider()

    section("Calidad de input comercial")
    complete_count = sum(1 for r in filtered if r.get("input_complete"))
    incomplete_count = max(0, total - complete_count)
    complete_pct = _pct(complete_count, total)
    quality_k1, quality_k2 = st.columns(2)
    quality_k1.metric("% oportunidades con input completo", f"{complete_pct}%")
    quality_k2.metric("Campos completos requeridos", "Web + Quote ID + CRM URL + Due Date")

    cohorts = [
        ("Input completo", [r for r in filtered if r.get("input_complete")]),
        ("Input incompleto", [r for r in filtered if not r.get("input_complete")]),
    ]
    quality_rows = []
    for label, cohort_rows in cohorts:
        cohort_total = len(cohort_rows)
        cohort_go = sum(1 for r in cohort_rows if r.get("technical_status") == "go")
        quality_rows.append(
            {
                "cohorte": label,
                "oportunidades": cohort_total,
                "score_medio": _avg_score(cohort_rows),
                "go_rate_%": _pct(cohort_go, cohort_total),
            }
        )
    styled_table(quality_rows)
    _render_altair_bar(
        {"Input completo": complete_count, "Input incompleto": incomplete_count},
        y_title="Número de oportunidades",
    )

    st.divider()

    section("Competitividad")
    partner_stats: dict[str, dict[str, float]] = {}
    area_stats: dict[str, dict[str, float]] = {}
    for row in filtered:
        partner = str(row.get("partner") or "-")
        area = str(row.get("main_area") or "-")
        for key, bucket in (("partner", partner_stats), ("area", area_stats)):
            category = partner if key == "partner" else area
            if category not in bucket:
                bucket[category] = {"opportunities": 0, "score_sum": 0.0, "go": 0}
            bucket[category]["opportunities"] += 1
            bucket[category]["score_sum"] += float(row.get("score", 0.0) or 0.0)
            if row.get("technical_status") == "go":
                bucket[category]["go"] += 1

    comp_left, comp_right = st.columns(2)
    with comp_left:
        st.markdown("**Resultados por partner**")
        partner_rows = sorted(
            (
                {
                    "partner": p,
                    "oportunidades": int(s["opportunities"]),
                    "score_medio": round(float(s["score_sum"]) / int(s["opportunities"]), 2)
                    if int(s["opportunities"]) > 0
                    else 0.0,
                    "go_rate_%": _pct(int(s["go"]), int(s["opportunities"])),
                }
                for p, s in partner_stats.items()
            ),
            key=lambda x: x["oportunidades"],
            reverse=True,
        )
        _render_altair_bar(
            {r["partner"]: int(r["oportunidades"]) for r in partner_rows[:10]},
            y_title="Oportunidades por partner",
        )
        styled_table(partner_rows)

    with comp_right:
        st.markdown("**Resultados por área**")
        area_rows = sorted(
            (
                {
                    "área": a,
                    "oportunidades": int(s["opportunities"]),
                    "score_medio": round(float(s["score_sum"]) / int(s["opportunities"]), 2)
                    if int(s["opportunities"]) > 0
                    else 0.0,
                    "go_rate_%": _pct(int(s["go"]), int(s["opportunities"])),
                }
                for a, s in area_stats.items()
            ),
            key=lambda x: x["oportunidades"],
            reverse=True,
        )
        _render_altair_bar(
            {r["área"]: int(r["oportunidades"]) for r in area_rows[:10]},
            y_title="Oportunidades por área",
        )
        styled_table(area_rows)

    st.divider()

    section("Top clientes por volumen")
    client_stats: dict[str, dict[str, int]] = {}
    for row in filtered:
        client = str(row.get("client_name") or "-")
        status = str(row.get("technical_status") or "pending").lower().strip()
        if client not in client_stats:
            client_stats[client] = {"opportunities": 0, "go": 0, "no_go": 0, "pending": 0}
        client_stats[client]["opportunities"] += 1
        if status == "go":
            client_stats[client]["go"] += 1
        elif status == "no_go":
            client_stats[client]["no_go"] += 1
        else:
            client_stats[client]["pending"] += 1

    top_clients = sorted(
        client_stats.items(),
        key=lambda kv: (
            kv[1]["opportunities"],
            kv[1]["go"],
            -kv[1]["pending"],
            kv[0].lower(),
        ),
        reverse=True,
    )[:10]
    styled_table(
        [
            {
                "cliente": client,
                "oportunidades": stats["opportunities"],
                "go": stats["go"],
                "no_go": stats["no_go"],
                "pendientes": stats["pending"],
            }
            for client, stats in top_clients
        ],
    )

if __name__ == "__main__":
    main()
