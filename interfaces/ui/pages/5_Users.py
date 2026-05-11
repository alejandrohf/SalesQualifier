"""Módulo `interfaces/ui/pages/5_Users.py` de la plataforma Sales Qualification Agent."""

from __future__ import annotations

from typing import Any

import streamlit as st

from interfaces.ui.components.auth import get_authenticated_api_client, require_authentication
from interfaces.ui.components.layout import (
    page_header,
    section,
    set_page_config,
    sidebar_header,
    styled_table,
)
from interfaces.ui.components.render import show_api_error


def _caps_label(u: dict[str, Any]) -> str:
    caps: list[str] = []
    if u.get("is_admin"):
        caps.append("Admin User")
    if u.get("can_sales"):
        caps.append("Sales User")
    if u.get("can_engineering"):
        caps.append("Engineering User")
    return " + ".join(caps) if caps else "Sin capacidades"


def _find_engineering_users(users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [u for u in users if u.get("can_engineering") and u.get("is_active")]


def _fmt_dt(value: Any) -> str:
    if not value:
        return "N/D"
    try:
        s = str(value).replace("Z", "+00:00")
        from datetime import datetime
        dt = datetime.fromisoformat(s)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(value)


def main() -> None:
    """Ejecuta `main` dentro de este modulo."""
    set_page_config()
    require_authentication()
    sidebar_header()
    page_header("Gestión de Usuarios", "Administración de usuarios y acceso de la plataforma.")

    client = get_authenticated_api_client()
    me = st.session_state.get("auth_user") or {}
    if not me.get("is_admin"):
        st.error("Esta página requiere rol Admin User.")
        st.stop()

    try:
        payload = client.list_users()
    except Exception as e:
        show_api_error(e)
        return

    users = payload.get("users", [])
    engineering_users = _find_engineering_users(users)

    section("Crear usuario")
    with st.form("create_user_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            email = st.text_input("Email")
            first_name = st.text_input("Nombre")
        with c2:
            last_name = st.text_input("Apellidos")
            is_admin = st.checkbox("Admin User", value=False)
            can_sales = st.checkbox("Sales User", value=False)
            can_engineering = st.checkbox("Engineering User", value=False)

        engineering_manager_id: str | None = None
        if can_sales:
            manager_options = [u["id"] for u in engineering_users]
            if manager_options:
                engineering_manager_id = st.selectbox(
                    "Responsable de Ingeniería asociado",
                    options=manager_options,
                    format_func=lambda uid: next(
                        (f"{u['first_name']} {u['last_name']} ({u['email']})" for u in engineering_users if u["id"] == uid),
                        str(uid),
                    ),
                )
            else:
                st.warning("No hay Engineering Users activos para asociar.")

        send_reset_email = st.checkbox("Enviar email para crear/resetear contraseña", value=True)
        create_submit = st.form_submit_button("Crear usuario", use_container_width=True)

    if create_submit:
        try:
            out = client.create_user(
                email=email.strip(),
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                is_admin=is_admin,
                can_sales=can_sales,
                can_engineering=can_engineering,
                engineering_manager_id=engineering_manager_id,
                send_reset_email=send_reset_email,
            )
            st.success(f"Usuario creado: {out.get('email')}")
            st.rerun()
        except Exception as e:
            show_api_error(e)

    st.divider()
    section("Usuarios")

    if not users:
        st.info("No hay usuarios creados.")
        return

    selected_user_id = st.selectbox(
        "Selecciona usuario",
        options=[u["id"] for u in users],
        format_func=lambda uid: next(
            (f"{u['first_name']} {u['last_name']} - {u['email']} ({_caps_label(u)})" for u in users if u["id"] == uid),
            str(uid),
        ),
    )

    user = next((u for u in users if u["id"] == selected_user_id), None)
    if not user:
        st.info("Usuario no encontrado.")
        return

    st.markdown(
        f"**Estado:** {'Activo' if user.get('is_active') else 'Inactivo'}  \n"
        f"**Último acceso:** {_fmt_dt(user.get('last_login_at'))}  \n"
        f"**Fecha creación:** {_fmt_dt(user.get('created_at'))}"
    )

    with st.form("edit_user_form"):
        e1, e2 = st.columns(2)
        with e1:
            new_first_name = st.text_input("Nombre", value=user.get("first_name", ""))
            new_last_name = st.text_input("Apellidos", value=user.get("last_name", ""))
        with e2:
            new_is_admin = st.checkbox("Admin User", value=bool(user.get("is_admin")))
            new_can_sales = st.checkbox("Sales User", value=bool(user.get("can_sales")))
            new_can_engineering = st.checkbox("Engineering User", value=bool(user.get("can_engineering")))
            new_active = st.checkbox("Usuario activo", value=bool(user.get("is_active")))

        new_eng_manager = None
        if new_can_sales:
            existing = user.get("engineering_manager_id")
            manager_options = [u["id"] for u in engineering_users]
            if existing and existing not in manager_options:
                manager_options = [existing] + manager_options
            if manager_options:
                new_eng_manager = st.selectbox(
                    "Responsable de Ingeniería asociado",
                    options=manager_options,
                    index=0,
                    format_func=lambda uid: next(
                        (f"{u['first_name']} {u['last_name']} ({u['email']})" for u in users if u["id"] == uid),
                        str(uid),
                    ),
                )
            else:
                st.warning("No hay Engineering Users activos para asociar.")

        save_submit = st.form_submit_button("Guardar cambios", use_container_width=True)

    if save_submit:
        patch: dict[str, Any] = {
            "first_name": new_first_name.strip(),
            "last_name": new_last_name.strip(),
            "is_admin": new_is_admin,
            "can_sales": new_can_sales,
            "can_engineering": new_can_engineering,
            "is_active": new_active,
        }
        if new_can_sales:
            patch["engineering_manager_id"] = new_eng_manager
        else:
            patch["engineering_manager_id"] = None

        try:
            client.update_user(str(selected_user_id), patch=patch)
            if user.get("is_active") and not new_active:
                client.deactivate_user(str(selected_user_id))
            elif not user.get("is_active") and new_active:
                client.activate_user(str(selected_user_id))
            st.success("Usuario actualizado.")
            st.rerun()
        except Exception as e:
            show_api_error(e)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Enviar email de reset", use_container_width=True):
            try:
                out = client.send_user_reset_email(str(selected_user_id))
                st.success(out.get("message", "Email de reset enviado"))
            except Exception as e:
                show_api_error(e)
    with c2:
        if user.get("is_active"):
            if st.button("Desactivar usuario", use_container_width=True):
                try:
                    client.deactivate_user(str(selected_user_id))
                    st.success("Usuario desactivado.")
                    st.rerun()
                except Exception as e:
                    show_api_error(e)
        else:
            if st.button("Activar usuario", use_container_width=True):
                try:
                    client.activate_user(str(selected_user_id))
                    st.success("Usuario activado.")
                    st.rerun()
                except Exception as e:
                    show_api_error(e)

    st.divider()
    styled_table(
        [
            {
                "email": u.get("email"),
                "nombre": f"{u.get('first_name','')} {u.get('last_name','')}".strip(),
                "capacidades": _caps_label(u),
                "responsable ingeniería asociado": next(
                    (
                        f"{mgr.get('first_name','')} {mgr.get('last_name','')}".strip()
                        for mgr in users
                        if str(mgr.get("id")) == str(u.get("engineering_manager_id"))
                    ),
                    "N/D",
                ),
                "activo": "Sí" if u.get("is_active") else "No",
                "último acceso": _fmt_dt(u.get("last_login_at")),
                "creado": _fmt_dt(u.get("created_at")),
            }
            for u in users
        ],
    )


if __name__ == "__main__":
    main()
