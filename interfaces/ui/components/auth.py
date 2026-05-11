"""Módulo `interfaces/ui/components/auth.py` de la plataforma Sales Qualification Agent."""

from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

from interfaces.ui.client import ApiClient, get_api_client


def get_session_token() -> Optional[str]:
    """Ejecuta `get_session_token` dentro de este modulo."""
    return st.session_state.get("auth_token")


def get_session_user() -> Optional[Dict[str, Any]]:
    """Ejecuta `get_session_user` dentro de este modulo."""
    return st.session_state.get("auth_user")


def clear_auth_session() -> None:
    """Ejecuta `clear_auth_session` dentro de este modulo."""
    st.session_state.pop("auth_token", None)
    st.session_state.pop("auth_user", None)
    st.session_state.pop("auth_expires_in", None)


def get_authenticated_api_client() -> ApiClient:
    """Ejecuta `get_authenticated_api_client` dentro de este modulo."""
    client = get_api_client()
    token = get_session_token()
    if token:
        client.set_bearer_token(token)
    return client


def require_authentication() -> None:
    """Ejecuta `require_authentication` dentro de este modulo."""
    token = get_session_token()
    if not token:
        st.warning("Debes iniciar sesión para acceder a esta página.")
        st.page_link("0_Login.py", label="Ir a Login")
        st.stop()

    # Validación ligera de sesión (si token inválido, limpiamos).
    client = get_authenticated_api_client()
    try:
        me = client.me()
        st.session_state["auth_user"] = me
    except Exception:
        clear_auth_session()
        st.warning("Tu sesión ha expirado o es inválida. Inicia sesión de nuevo.")
        st.page_link("0_Login.py", label="Ir a Login")
        st.stop()
