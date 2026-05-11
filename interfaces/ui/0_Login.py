"""Módulo `interfaces/ui/0_Login.py` de la plataforma Sales Qualification Agent."""

from __future__ import annotations

import streamlit as st

from interfaces.ui.components.auth import clear_auth_session, get_authenticated_api_client, get_session_user
from interfaces.ui.components.layout import (
    info_banner,
    page_header,
    section,
    set_page_config,
    sidebar_header,
    styled_tabs,
)
from interfaces.ui.components.render import show_api_error


def _save_auth(result: dict) -> None:
    st.session_state["auth_token"] = result.get("access_token")
    st.session_state["auth_user"] = result.get("user")
    st.session_state["auth_expires_in"] = result.get("expires_in")


def main() -> None:
    """Ejecuta `main` dentro de este modulo."""
    set_page_config()
    sidebar_header()
    page_header("Login", "Accede a la plataforma con tu usuario corporativo.")

    current_user = get_session_user()
    if current_user:
        caps = []
        if current_user.get("is_admin"):
            caps.append("Admin")
        if current_user.get("can_sales"):
            caps.append("Sales")
        if current_user.get("can_engineering"):
            caps.append("Engineering")
        info_banner(
            type="success",
            text=f"Sesión activa: {current_user.get('first_name','')} {current_user.get('last_name','')} ({', '.join(caps) if caps else 'Ninguna'})",
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Ir al Dashboard", use_container_width=True):
                st.switch_page("pages/1_Dashboard.py")
        with c2:
            if st.button("Cerrar sesión", use_container_width=True):
                clear_auth_session()
                st.rerun()
        return

    client = get_authenticated_api_client()
    reset_token_from_qs = st.query_params.get("reset_token")

    section("Acceso")
    tabs = styled_tabs(["Iniciar sesión", "Recuperar contraseña"])

    with tabs[0]:
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Entrar", use_container_width=True)

        if submitted:
            try:
                result = client.login(email=email.strip(), password=password)
                _save_auth(result)
                st.success("Sesión iniciada.")
                st.switch_page("pages/1_Dashboard.py")
            except Exception as e:
                show_api_error(e)

    with tabs[1]:
        token = st.text_input("Token de reset", value=reset_token_from_qs or "")
        new_password = st.text_input("Nueva contraseña", type="password")
        new_password2 = st.text_input("Repite contraseña", type="password")
        if st.button("Actualizar contraseña", use_container_width=True):
            if new_password != new_password2:
                st.error("Las contraseñas no coinciden.")
            elif len(new_password) < 8:
                st.error("La contraseña debe tener al menos 8 caracteres.")
            else:
                try:
                    client.reset_password(token=token.strip(), new_password=new_password)
                    st.success("Contraseña actualizada. Ya puedes iniciar sesión.")
                except Exception as e:
                    show_api_error(e)


if __name__ == "__main__":
    main()
