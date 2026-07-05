"""Schemas de autenticación, gestión de usuarios y reseteo de contraseña."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import EmailStr, Field

from schemas.common import AppBaseModel


class LoginRequest(AppBaseModel):
    """Credenciales necesarias para iniciar sesión en la plataforma."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=256)


class UserOut(AppBaseModel):
    """Representación pública de un usuario devuelta por la API."""
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    is_admin: bool
    can_sales: bool
    can_engineering: bool
    is_active: bool
    must_change_password: bool
    engineering_manager_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    disabled_at: Optional[datetime] = None


class TokenResponse(AppBaseModel):
    """Respuesta de autenticación con token JWT y datos del usuario autenticado."""
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserOut


class CreateUserRequest(AppBaseModel):
    """Datos necesarios para dar de alta un nuevo usuario desde administración."""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=120)
    last_name: str = Field(..., min_length=1, max_length=120)
    is_admin: bool = False
    can_sales: bool = False
    can_engineering: bool = False
    engineering_manager_id: Optional[UUID] = None
    send_reset_email: bool = True


class UpdateUserRequest(AppBaseModel):
    """Actualización parcial de nombre, capacidades o estado de un usuario existente."""
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    is_admin: Optional[bool] = None
    can_sales: Optional[bool] = None
    can_engineering: Optional[bool] = None
    engineering_manager_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class UserListResponse(AppBaseModel):
    """Listado paginable de usuarios devuelto por la API de administración."""
    users: List[UserOut] = Field(default_factory=list)
    total: int


class PasswordResetRequest(AppBaseModel):
    """Petición para establecer una nueva contraseña a partir de un token de reseteo."""
    token: str = Field(..., min_length=16, max_length=512)
    new_password: str = Field(..., min_length=8, max_length=256)


class SendResetResponse(AppBaseModel):
    """Resultado de la generación o envío del enlace de reseteo de contraseña."""
    status: Literal["sent", "generated_only"]
    message: str
