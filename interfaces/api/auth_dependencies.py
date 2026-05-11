"""Módulo `interfaces/api/auth_dependencies.py` de la plataforma Sales Qualification Agent."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from domain.auth import decode_access_token
from infrastructure.db.users import get_user_by_id


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Ejecuta `get_current_user` dentro de este modulo."""
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User disabled")

    return user


def require_admin():
    """Ejecuta `require_admin` dentro de este modulo."""
    def _dep(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if not bool(user.get("is_admin")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin capability required")
        return user

    return _dep


def require_sales():
    """Ejecuta `require_sales` dentro de este modulo."""
    def _dep(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if not bool(user.get("can_sales")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sales capability required")
        return user

    return _dep


def require_engineering():
    """Ejecuta `require_engineering` dentro de este modulo."""
    def _dep(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if not bool(user.get("can_engineering")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Engineering capability required")
        return user

    return _dep


def require_sales_or_engineering():
    """Ejecuta `require_sales_or_engineering` dentro de este modulo."""
    def _dep(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if not bool(user.get("can_sales") or user.get("can_engineering")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sales or Engineering capability required",
            )
        return user

    return _dep
