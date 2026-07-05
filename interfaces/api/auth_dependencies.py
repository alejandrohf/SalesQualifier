"""Dependencias reutilizables de autenticación y autorización para FastAPI."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from domain.auth import decode_access_token
from infrastructure.db.users import get_user_by_id


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Resuelve el usuario autenticado a partir del bearer token recibido."""
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
    """Construye una dependencia que exige capacidad administrativa."""
    def _dep(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if not bool(user.get("is_admin")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin capability required")
        return user

    return _dep


def require_sales():
    """Construye una dependencia que exige capacidad comercial."""
    def _dep(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if not bool(user.get("can_sales")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sales capability required")
        return user

    return _dep


def require_engineering():
    """Construye una dependencia que exige capacidad técnica."""
    def _dep(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if not bool(user.get("can_engineering")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Engineering capability required")
        return user

    return _dep


def require_sales_or_engineering():
    """Construye una dependencia válida para perfiles comerciales o técnicos."""
    def _dep(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if not bool(user.get("can_sales") or user.get("can_engineering")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sales or Engineering capability required",
            )
        return user

    return _dep
