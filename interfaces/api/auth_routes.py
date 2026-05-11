"""Módulo `interfaces/api/auth_routes.py` de la plataforma Sales Qualification Agent."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import config
from domain.auth import (
    create_access_token,
    generate_secure_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from infrastructure.db.users import (
    consume_password_reset_token,
    create_password_reset_token,
    create_user,
    get_user_by_email,
    get_user_auth_by_email,
    get_user_by_id,
    has_opportunities_created_by,
    has_technical_decisions_by,
    list_users,
    set_last_login,
    set_user_active,
    set_user_password,
    update_user,
)
from interfaces.api.auth_dependencies import get_current_user, require_admin
from schemas.auth import (
    CreateUserRequest,
    LoginRequest,
    PasswordResetRequest,
    SendResetResponse,
    TokenResponse,
    UpdateUserRequest,
    UserListResponse,
    UserOut,
)
from tools.email_sender import send_plain_email


router = APIRouter(prefix="/auth", tags=["auth"])


def _send_reset_email(email: str, full_name: str, reset_token: str) -> SendResetResponse:
    reset_link = f"{config.APP_PUBLIC_BASE_URL.rstrip('/')}/Login?reset_token={reset_token}"
    subject = "Configura tu contraseña - Sales Qualification Platform"
    body = (
        f"Hola {full_name},\n\n"
        f"Usa este enlace para crear o resetear tu contraseña:\n{reset_link}\n\n"
        "Este enlace expira en 24 horas.\n"
    )
    try:
        send_plain_email(to_email=email, subject=subject, body=body)
        return SendResetResponse(status="sent", message=f"Email enviado a {email}")
    except Exception as e:
        return SendResetResponse(
            status="generated_only",
            message=f"No se pudo enviar email automáticamente ({e}). Link temporal: {reset_link}",
        )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    """Ejecuta `login` dentro de este modulo."""
    user = get_user_auth_by_email(payload.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User disabled")

    password_hash = user.get("password_hash")
    if not password_hash or not verify_password(payload.password, password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token, expires_in = create_access_token(
        subject=str(user["id"]),
        email=str(user["email"]),
        role="admin" if user.get("is_admin") else "user",
    )
    set_last_login(user["id"])
    user_public = {k: v for k, v in user.items() if k != "password_hash"}

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserOut.model_validate(user_public),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Ejecuta `me` dentro de este modulo."""
    return UserOut.model_validate(current_user)


@router.get("/users", response_model=UserListResponse)
def get_users(_: Dict[str, Any] = Depends(require_admin())):
    """Ejecuta `get_users` dentro de este modulo."""
    users = list_users()
    return UserListResponse(users=[UserOut.model_validate(u) for u in users], total=len(users))


@router.post("/users", response_model=UserOut)
def create_user_endpoint(
    payload: CreateUserRequest,
    current_user: Dict[str, Any] = Depends(require_admin()),
):
    """Ejecuta `create_user_endpoint` dentro de este modulo."""
    if get_user_by_email(str(payload.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User email already exists")

    if payload.can_sales and not payload.engineering_manager_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sales user requires engineering manager")
    if payload.engineering_manager_id:
        manager = get_user_by_id(payload.engineering_manager_id)
        if not manager or not manager.get("is_active") or not manager.get("can_engineering"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="engineering_manager_id must be an active engineering user")
    if not (payload.is_admin or payload.can_sales or payload.can_engineering):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must have at least one capability")

    user = create_user(
        email=str(payload.email),
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=None,
        is_admin=payload.is_admin,
        can_sales=payload.can_sales,
        can_engineering=payload.can_engineering,
        password_hash=None,
        engineering_manager_id=payload.engineering_manager_id,
        created_by=current_user["id"],
    )

    if payload.send_reset_email:
        reset_token = generate_secure_token()
        create_password_reset_token(
            user_id=user["id"],
            token_hash=hash_reset_token(reset_token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            created_by=current_user["id"],
        )
        _send_reset_email(
            str(user["email"]),
            f"{user['first_name']} {user['last_name']}",
            reset_token,
        )

    return UserOut.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserOut)
def patch_user_endpoint(
    user_id: UUID,
    payload: UpdateUserRequest,
    current_user: Dict[str, Any] = Depends(require_admin()),
):
    """Ejecuta `patch_user_endpoint` dentro de este modulo."""
    patch = payload.model_dump(exclude_none=True)
    user_before = get_user_by_id(user_id)
    if not user_before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    next_can_sales = patch.get("can_sales", user_before.get("can_sales"))
    next_can_engineering = patch.get("can_engineering", user_before.get("can_engineering"))
    next_is_admin = patch.get("is_admin", user_before.get("is_admin"))

    if next_can_sales and patch.get("engineering_manager_id", user_before.get("engineering_manager_id")) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sales user requires engineering manager")
    if patch.get("engineering_manager_id") is not None:
        manager = get_user_by_id(patch["engineering_manager_id"])
        if not manager or not manager.get("is_active") or not manager.get("can_engineering"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="engineering_manager_id must be an active engineering user")
    if not (next_is_admin or next_can_sales or next_can_engineering):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must have at least one capability")

    # Regla: no se puede cambiar capacidades con oportunidades activas/históricas.
    if (
        next_is_admin != bool(user_before.get("is_admin"))
        or
        next_can_sales != bool(user_before.get("can_sales"))
        or next_can_engineering != bool(user_before.get("can_engineering"))
    ):
        if has_opportunities_created_by(user_id) or has_technical_decisions_by(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pueden cambiar capacidades con oportunidades activas/históricas",
            )

    user = update_user(user_id, patch=patch, updated_by=current_user["id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserOut.model_validate(user)


@router.post("/users/{user_id}/activate", response_model=UserOut)
def activate_user_endpoint(
    user_id: UUID,
    current_user: Dict[str, Any] = Depends(require_admin()),
):
    """Ejecuta `activate_user_endpoint` dentro de este modulo."""
    user = set_user_active(user_id, is_active=True, updated_by=current_user["id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserOut.model_validate(user)


@router.post("/users/{user_id}/deactivate", response_model=UserOut)
def deactivate_user_endpoint(
    user_id: UUID,
    current_user: Dict[str, Any] = Depends(require_admin()),
):
    """Ejecuta `deactivate_user_endpoint` dentro de este modulo."""
    if str(user_id) == str(current_user["id"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate current admin")
    user = set_user_active(user_id, is_active=False, updated_by=current_user["id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserOut.model_validate(user)


@router.post("/users/{user_id}/send-reset-email", response_model=SendResetResponse)
def send_reset_email_endpoint(
    user_id: UUID,
    current_user: Dict[str, Any] = Depends(require_admin()),
):
    """Ejecuta `send_reset_email_endpoint` dentro de este modulo."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    reset_token = generate_secure_token()
    create_password_reset_token(
        user_id=user["id"],
        token_hash=hash_reset_token(reset_token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        created_by=current_user["id"],
    )
    return _send_reset_email(
        str(user["email"]),
        f"{user['first_name']} {user['last_name']}",
        reset_token,
    )


@router.post("/reset-password")
def reset_password(payload: PasswordResetRequest):
    """Ejecuta `reset_password` dentro de este modulo."""
    token_data = consume_password_reset_token(hash_reset_token(payload.token))
    if not token_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    ok = set_user_password(
        token_data["user_id"],
        password_hash=hash_password(payload.new_password),
        updated_by=token_data["user_id"],
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"status": "ok", "message": "Password updated"}
