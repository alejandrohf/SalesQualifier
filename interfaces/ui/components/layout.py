"""Sistema visual compartido de la interfaz Streamlit: estilos, cabeceras y componentes de layout."""

from __future__ import annotations

import html
import os
from typing import Any

import streamlit as st

from interfaces.ui.components.auth import clear_auth_session, get_session_user


def inject_global_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --pc-bg-1: #dde4f7;
            --pc-bg-2: #cfd8f4;
            --pc-shell: rgba(255, 255, 255, 0.48);
            --pc-surface: rgba(255, 255, 255, 0.62);
            --pc-surface-strong: rgba(255, 255, 255, 0.78);
            --pc-surface-soft: rgba(245, 249, 255, 0.7);
            --pc-border: rgba(150, 177, 222, 0.34);
            --pc-text: #1f3360;
            --pc-text-muted: #5d6f98;
            --pc-primary: #2c74e7;
            --pc-primary-dark: #1d58b7;
            --pc-success: #24a58d;
            --pc-warning: #de9f46;
            --pc-danger: #d96570;
            --pc-shadow-soft: 0 10px 26px rgba(54, 83, 143, 0.14);
            --pc-shadow-card: 0 12px 24px rgba(47, 76, 144, 0.12);
            --pc-radius-lg: 18px;
            --pc-radius-md: 12px;
            --pc-radius-sm: 10px;
            --pc-space-1: 6px;
            --pc-space-2: 10px;
            --pc-space-3: 14px;
            --pc-space-4: 18px;
        }

        .stApp {
            background:
                radial-gradient(circle at 5% 5%, #e6eeff 0%, transparent 35%),
                radial-gradient(circle at 95% 10%, #e5f1ff 0%, transparent 38%),
                linear-gradient(180deg, var(--pc-bg-1) 0%, var(--pc-bg-2) 100%);
            color: var(--pc-text);
            font-family: "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        }

        .main .block-container {
            max-width: 1320px;
            background: var(--pc-shell);
            border: 1px solid rgba(255, 255, 255, 0.55);
            box-shadow: var(--pc-shadow-soft);
            backdrop-filter: blur(10px);
            border-radius: 0 0 20px 20px;
            padding-top: .8rem !important;
            padding-left: 1.7rem !important;
            padding-right: 1.7rem !important;
            padding-bottom: 1.5rem !important;
        }

        [data-testid="stHeader"] {
            background: var(--pc-surface-strong) !important;
            backdrop-filter: blur(8px);
            border-bottom: 1px solid var(--pc-border) !important;
        }

        [data-testid="stSidebar"] {
            background:
                radial-gradient(circle at 10% 15%, rgba(90, 140, 255, 0.28) 0%, transparent 40%),
                linear-gradient(165deg, #2f5da8 0%, #345fae 35%, #2f4e95 100%);
            border-right: 1px solid rgba(180, 204, 255, 0.24);
            box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.14);
        }
        [data-testid="stSidebarContent"] { color: #e8f1ff; }
        [data-testid="stSidebarNav"] [data-testid="stSidebarNavLink"] {
            border-radius: 10px;
            margin: 4px 8px;
            color: #dce7ff !important;
            transition: all .18s ease;
        }
        [data-testid="stSidebarNav"] [data-testid="stSidebarNavLink"]:hover {
            background: rgba(122, 176, 255, 0.24) !important;
            color: #ffffff !important;
        }
        [data-testid="stSidebarNav"] [aria-current="page"] {
            background: linear-gradient(90deg, rgba(80, 160, 255, 0.56) 0%, rgba(123, 152, 255, 0.42) 100%) !important;
            border: 1px solid rgba(182, 220, 255, 0.5);
            color: #ffffff !important;
            font-weight: 700;
            box-shadow: 0 6px 14px rgba(18, 41, 94, 0.2);
        }
        [data-testid="stSidebar"] hr { border-color: rgba(210, 226, 255, 0.25) !important; }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] div {
            color: #e9f2ff !important;
        }

        h1, h2, h3, h4 { color: var(--pc-text); letter-spacing: -0.01em; }
        p, li, label, [data-testid="stCaptionContainer"] { color: var(--pc-text-muted); }

        .pc-page-hero {
            border: 1px solid var(--pc-border);
            border-radius: var(--pc-radius-lg);
            background:
                linear-gradient(180deg, rgba(255,255,255,0.72) 0%, rgba(248,252,255,0.64) 100%),
                radial-gradient(circle at 10% 10%, rgba(179, 214, 255, 0.18) 0%, transparent 45%);
            box-shadow: var(--pc-shadow-card);
            padding: 18px 22px;
            margin-bottom: 12px;
        }
        .pc-page-title {
            margin: 0;
            color: var(--pc-text);
            font-size: 2.2rem;
            line-height: 1.1;
            font-weight: 800;
            letter-spacing: -0.02em;
        }
        .pc-page-subtitle {
            margin: 8px 0 0 0;
            color: var(--pc-text-muted);
            font-size: 1.02rem;
            line-height: 1.45;
        }

        .pc-section {
            margin-top: 6px;
            margin-bottom: 7px;
            border-bottom: 1px solid rgba(154, 176, 216, 0.24);
            padding-bottom: 5px;
        }
        .pc-section h3 {
            margin: 0;
            font-size: 1.9rem;
            font-weight: 760;
            color: #233966;
        }

        .stTextInput > div > div > input,
        .stNumberInput input,
        .stDateInput input,
        .stTimeInput input,
        textarea,
        [data-baseweb="select"] > div {
            background: var(--pc-surface-soft) !important;
            border-radius: var(--pc-radius-sm) !important;
            border: 1px solid rgba(163, 184, 221, 0.35) !important;
            color: var(--pc-text) !important;
            min-height: 44px;
        }
        .stTextInput > div > div > input:focus,
        .stNumberInput input:focus,
        .stDateInput input:focus,
        .stTimeInput input:focus,
        textarea:focus,
        [data-baseweb="select"] > div:focus-within {
            border-color: rgba(65, 120, 220, 0.58) !important;
            box-shadow: 0 0 0 2px rgba(84, 142, 242, 0.15) !important;
        }

        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stLinkButton"] a {
            border-radius: var(--pc-radius-sm) !important;
            border: 1px solid rgba(143, 175, 231, 0.48) !important;
            background: linear-gradient(180deg, #4f98f2 0%, #2f73de 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 8px 16px rgba(37, 90, 180, 0.24);
            font-weight: 600 !important;
        }
        .stButton > button:hover,
        .stDownloadButton > button:hover,
        [data-testid="stLinkButton"] a:hover {
            background: linear-gradient(180deg, #5aa2ff 0%, #2f73de 100%) !important;
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] .stButton > button {
            background: linear-gradient(180deg, rgba(120, 169, 255, 0.72) 0%, rgba(88, 139, 235, 0.72) 100%) !important;
            color: #f7fbff !important;
            border: 1px solid rgba(200, 223, 255, 0.55) !important;
            text-shadow: 0 1px 0 rgba(18, 41, 94, 0.3);
            font-weight: 700 !important;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            background: linear-gradient(180deg, rgba(141, 186, 255, 0.78) 0%, rgba(93, 144, 238, 0.78) 100%) !important;
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] .stButton > button:disabled {
            color: #eef6ff !important;
            opacity: 0.95 !important;
        }
        .stButton > button[kind="secondary"] {
            background: var(--pc-surface-strong) !important;
            color: var(--pc-text) !important;
            box-shadow: none !important;
        }

        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 6px;
            border-bottom: 1px solid rgba(146, 170, 213, 0.3);
        }
        [data-testid="stTabs"] [data-baseweb="tab"] {
            background: transparent;
            border-radius: 10px 10px 0 0;
            color: var(--pc-text-muted);
            padding: 8px 12px;
        }
        [data-testid="stTabs"] [aria-selected="true"] {
            color: var(--pc-text) !important;
            background: rgba(255,255,255,.56) !important;
            border: 1px solid rgba(146, 170, 213, 0.32) !important;
            border-bottom-color: transparent !important;
            font-weight: 700;
        }
        [data-testid="stTabs"] [data-baseweb="tab-panel"] {
            background: rgba(255,255,255,.5);
            border: 1px solid rgba(146, 170, 213, 0.32);
            border-radius: 0 12px 12px 12px;
            padding: 10px 12px 12px 12px;
        }

        [data-testid="stDataFrame"] {
            border-radius: 12px;
            border: 1px solid rgba(150, 177, 222, 0.34);
            overflow: hidden;
            background: rgba(255,255,255,.56);
            box-shadow: 0 8px 16px rgba(47, 76, 144, 0.09);
        }
        [data-testid="stDataFrame"] [role="columnheader"] {
            background: rgba(233, 241, 255, 0.72) !important;
            color: #2b4578 !important;
            font-weight: 650 !important;
        }
        [data-testid="stDataFrame"] [role="gridcell"] {
            border-color: rgba(150, 177, 222, 0.22) !important;
        }

        [data-testid="stExpander"] {
            border: 1px solid rgba(150, 177, 222, 0.34) !important;
            border-radius: 12px !important;
            background: rgba(255,255,255,0.56) !important;
            overflow: hidden;
            box-shadow: 0 8px 16px rgba(47, 76, 144, 0.08);
        }
        [data-testid="stExpander"] details summary {
            background: rgba(246, 250, 255, 0.82);
            min-height: 44px;
            border-bottom: 1px solid rgba(150, 177, 222, 0.18);
        }

        [data-testid="stVerticalBlock"] > [data-testid="stContainer"][data-testid*="border"] {
            border-radius: 12px !important;
            border: 1px solid rgba(150, 177, 222, 0.3) !important;
            background: rgba(255,255,255,.55) !important;
        }

        .pc-card {
            border: 1px solid var(--pc-border);
            border-radius: var(--pc-radius-lg);
            background: var(--pc-surface);
            box-shadow: var(--pc-shadow-card);
            padding: 12px 14px;
        }
        .pc-card-title { font-size: .85rem; color: var(--pc-text-muted); margin-bottom: 6px; text-transform: uppercase; letter-spacing: .04em; font-weight: 700; }
        .pc-kpi-label { font-size: .9rem; color: var(--pc-text-muted); }
        .pc-kpi-value { font-size: 2rem; line-height: 1.05; color: var(--pc-text); font-weight: 800; margin-top: 3px; }
        .pc-kpi { min-height: 104px; }
        .pc-kpi-neutral {
            background:
              linear-gradient(180deg, rgba(255,255,255,.72) 0%, rgba(244,250,255,.68) 100%),
              radial-gradient(circle at 85% 10%, rgba(119, 185, 255, .15) 0%, transparent 40%);
        }
        .pc-kpi-success {
            background:
              linear-gradient(180deg, rgba(238,255,251,.86) 0%, rgba(228,250,242,.72) 100%),
              radial-gradient(circle at 85% 10%, rgba(38, 178, 143, .16) 0%, transparent 42%);
            border-color: rgba(72, 181, 148, .35);
        }
        .pc-kpi-success .pc-kpi-value { color: #0f7f66; }
        .pc-kpi-warning {
            background:
              linear-gradient(180deg, rgba(255,248,236,.85) 0%, rgba(255,241,219,.72) 100%),
              radial-gradient(circle at 85% 10%, rgba(224, 158, 60, .16) 0%, transparent 42%);
            border-color: rgba(224, 158, 60, .35);
        }
        .pc-kpi-warning .pc-kpi-value { color: #9a6917; }
        .pc-kpi-danger {
            background:
              linear-gradient(180deg, rgba(255,242,245,.86) 0%, rgba(255,232,238,.72) 100%),
              radial-gradient(circle at 85% 10%, rgba(214, 100, 123, .15) 0%, transparent 42%);
            border-color: rgba(214, 100, 123, .34);
        }
        .pc-kpi-danger .pc-kpi-value { color: #aa3d55; }
        .pc-banner { border-radius: 12px; padding: 10px 12px; border: 1px solid rgba(152, 178, 220, 0.4); background: var(--pc-surface-strong); }
        .pc-banner.info { border-left: 4px solid #4d87ea; }
        .pc-banner.success { border-left: 4px solid #23a184; }
        .pc-banner.warning { border-left: 4px solid #da9d45; }
        .pc-banner.error { border-left: 4px solid #d16373; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def set_page_config() -> None:
    """Aplica la configuración base de página y los estilos globales de la UI."""
    st.set_page_config(
        page_title="Sales Qualification Platform",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_global_styles()


def sidebar_header() -> None:
    """Renderiza la cabecera lateral con información de sesión y navegación contextual."""
    st.sidebar.title("Sales Qualifier")

    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    st.sidebar.markdown(f"**API_BASE_URL**: `{base_url}`")

    user = get_session_user()
    if user:
        full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        caps = []
        if user.get("is_admin"):
            caps.append("Admin")
        if user.get("can_sales"):
            caps.append("Sales")
        if user.get("can_engineering"):
            caps.append("Engineering")
        st.sidebar.caption(f"Sesión: **{full_name or user.get('email','-')}**")
        st.sidebar.caption(f"Capacidades: `{', '.join(caps) if caps else 'Ninguna'}`")
        if st.sidebar.button("Cerrar sesión", use_container_width=True):
            clear_auth_session()
            st.switch_page("0_Login.py")

    st.sidebar.divider()


def page_header(title: str, subtitle: str | None = None) -> None:
    """Renderiza cabecera de página reutilizable."""
    subtitle_html = f'<p class="pc-page-subtitle">{html.escape(subtitle)}</p>' if subtitle else ""
    st.markdown(
        f"""
        <section class="pc-page-hero">
            <h1 class="pc-page-title">{html.escape(title)}</h1>
            {subtitle_html}
        </section>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, right_actions: str | None = None) -> None:
    """Renderiza título de sección con separador visual."""
    right = f"<div>{right_actions}</div>" if right_actions else ""
    st.markdown(
        f"""
        <div class="pc-section" style="display:flex;align-items:center;justify-content:space-between;gap:12px;">
          <h3>{html.escape(title)}</h3>
          {right}
        </div>
        """,
        unsafe_allow_html=True,
    )


def card(title: str | None = None, variant: str = "default") -> None:
    """Renderiza una tarjeta simple reutilizable."""
    title_html = f'<div class="pc-card-title">{html.escape(title)}</div>' if title else ""
    st.markdown(
        f"""
        <div class="pc-card pc-card-{html.escape(variant)}">
          {title_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str | int | float, icon: str | None = None, variant: str = "neutral") -> None:
    """Renderiza KPI con estilo consistente."""
    icon_html = f"{html.escape(icon)} " if icon else ""
    st.markdown(
        f"""
        <div class="pc-card pc-kpi pc-kpi-{html.escape(variant)}">
          <div class="pc-kpi-label">{icon_html}{html.escape(label)}</div>
          <div class="pc-kpi-value">{html.escape(str(value))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_banner(type: str = "info", text: str = "") -> None:
    """Renderiza banner informativo de estado."""
    st.markdown(
        f'<div class="pc-banner {html.escape(type)}">{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )


def styled_tabs(labels: list[str], key: str | None = None):
    """Wrapper de tabs para mantener API consistente."""
    return st.tabs(labels)


def styled_table(data: Any, use_container_width: bool = True, hide_index: bool = True, **kwargs: Any) -> None:
    """Wrapper de dataframe con defaults de estilo."""
    st.dataframe(data, use_container_width=use_container_width, hide_index=hide_index, **kwargs)


def primary_button(label: str, key: str | None = None, use_container_width: bool = True, help: str | None = None) -> bool:
    """Botón primario."""
    return st.button(label, key=key, use_container_width=use_container_width, help=help)


def secondary_button(label: str, key: str | None = None, use_container_width: bool = True, help: str | None = None) -> bool:
    """Botón secundario."""
    return st.button(label, key=key, use_container_width=use_container_width, help=help, type="secondary")
