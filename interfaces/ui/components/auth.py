"""Helpers de autenticación y sesión para las páginas de Streamlit."""

from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

from interfaces.ui.client import ApiClient, get_api_client


def get_session_token() -> Optional[str]:
    """Recupera el token de autenticación almacenado en la sesión de Streamlit."""
    return st.session_state.get("auth_token")


def get_session_user() -> Optional[Dict[str, Any]]:
    """Recupera el usuario autenticado almacenado en sesión."""
    return st.session_state.get("auth_user")


def clear_auth_session() -> None:
    """Limpia por completo el estado de autenticación de la sesión actual."""
    st.session_state.pop("auth_token", None)
    st.session_state.pop("auth_user", None)
    st.session_state.pop("auth_expires_in", None)


def get_authenticated_api_client() -> ApiClient:
    """Devuelve un cliente API con el bearer token actual ya configurado."""
    client = get_api_client()
    token = get_session_token()
    if token:
        client.set_bearer_token(token)
    return client


def require_authentication() -> None:
    """Fuerza autenticación válida antes de permitir el acceso a una página protegida."""
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
