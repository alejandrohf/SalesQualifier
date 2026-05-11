"""Módulo `schemas/auth.py` de la plataforma Sales Qualification Agent."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import EmailStr, Field

from schemas.common import AppBaseModel


class LoginRequest(AppBaseModel):
    """Define `LoginRequest` dentro de este modulo."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=256)


class UserOut(AppBaseModel):
    """Define `UserOut` dentro de este modulo."""
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
    """Define `TokenResponse` dentro de este modulo."""
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserOut


class CreateUserRequest(AppBaseModel):
    """Define `CreateUserRequest` dentro de este modulo."""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=120)
    last_name: str = Field(..., min_length=1, max_length=120)
    is_admin: bool = False
    can_sales: bool = False
    can_engineering: bool = False
    engineering_manager_id: Optional[UUID] = None
    send_reset_email: bool = True


class UpdateUserRequest(AppBaseModel):
    """Define `UpdateUserRequest` dentro de este modulo."""
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    is_admin: Optional[bool] = None
    can_sales: Optional[bool] = None
    can_engineering: Optional[bool] = None
    engineering_manager_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class UserListResponse(AppBaseModel):
    """Define `UserListResponse` dentro de este modulo."""
    users: List[UserOut] = Field(default_factory=list)
    total: int


class PasswordResetRequest(AppBaseModel):
    """Define `PasswordResetRequest` dentro de este modulo."""
    token: str = Field(..., min_length=16, max_length=512)
    new_password: str = Field(..., min_length=8, max_length=256)


class SendResetResponse(AppBaseModel):
    """Define `SendResetResponse` dentro de este modulo."""
    status: Literal["sent", "generated_only"]
    message: str
