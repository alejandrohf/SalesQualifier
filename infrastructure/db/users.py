"""Acceso a datos para usuarios, capacidades y tokens de reseteo.

Centraliza las operaciones CRUD y las comprobaciones auxiliares necesarias para
autenticación, administración y auditoría de usuarios.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import asc, select

from infrastructure.db.models import UserORM, UserPasswordResetTokenORM
from infrastructure.db.session import SessionLocal


def _legacy_role_from_caps(*, is_admin: bool, can_sales: bool, can_engineering: bool) -> str:
    # Compatibilidad con esquemas antiguos donde users.role era NOT NULL.
    if is_admin:
        return "admin"
    if can_sales:
        return "sales"
    if can_engineering:
        return "engineering"
    return "user"


def _to_user_dict(u: UserORM) -> Dict[str, Any]:
    # Backward compat: si aún no se migró a flags y existe role legacy.
    role_legacy = (u.role or "").lower().strip()
    is_admin = bool(u.is_admin) or role_legacy == "admin"
    can_sales = bool(u.can_sales) or role_legacy == "sales"
    can_engineering = bool(u.can_engineering) or role_legacy == "engineering"
    return {
        "id": u.id,
        "email": u.email,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "is_admin": is_admin,
        "can_sales": can_sales,
        "can_engineering": can_engineering,
        "is_active": bool(u.is_active),
        "must_change_password": bool(u.must_change_password),
        "engineering_manager_id": u.engineering_manager_id,
        "created_at": u.created_at,
        "updated_at": u.updated_at,
        "last_login_at": u.last_login_at,
        "created_by": u.created_by,
        "updated_by": u.updated_by,
        "disabled_at": u.disabled_at,
    }


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Busca un usuario por email y devuelve su representación pública interna."""
    with SessionLocal() as db:
        stmt = select(UserORM).where(UserORM.email == email.strip().lower())
        row = db.scalar(stmt)
        return _to_user_dict(row) if row else None


def get_user_auth_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Variante interna para autenticación: incluye password_hash.
    No usar para payloads de salida API/UI.
    """
    with SessionLocal() as db:
        stmt = select(UserORM).where(UserORM.email == email.strip().lower())
        row = db.scalar(stmt)
        if not row:
            return None
        out = _to_user_dict(row)
        out["password_hash"] = row.password_hash
        return out


def get_user_by_id(user_id: str | UUID) -> Optional[Dict[str, Any]]:
    """Obtiene un usuario por identificador UUID."""
    with SessionLocal() as db:
        stmt = select(UserORM).where(UserORM.id == user_id)
        row = db.scalar(stmt)
        return _to_user_dict(row) if row else None


def list_users() -> List[Dict[str, Any]]:
    """Lista todos los usuarios ordenados por email."""
    with SessionLocal() as db:
        stmt = select(UserORM).order_by(asc(UserORM.email))
        rows = list(db.scalars(stmt).all())
        return [_to_user_dict(r) for r in rows]


def create_user(
    *,
    email: str,
    first_name: str,
    last_name: str,
    role: str | None,
    is_admin: bool,
    can_sales: bool,
    can_engineering: bool,
    password_hash: str | None,
    engineering_manager_id: str | UUID | None,
    created_by: str | UUID | None,
) -> Dict[str, Any]:
    """Crea un nuevo usuario con sus capacidades y metadatos de trazabilidad."""
    role_to_store = role or _legacy_role_from_caps(
        is_admin=bool(is_admin),
        can_sales=bool(can_sales),
        can_engineering=bool(can_engineering),
    )

    with SessionLocal() as db:
        row = UserORM(
            email=email.strip().lower(),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            role=role_to_store,
            is_admin=bool(is_admin),
            can_sales=bool(can_sales),
            can_engineering=bool(can_engineering),
            password_hash=password_hash,
            is_active=True,
            must_change_password=True,
            engineering_manager_id=engineering_manager_id,
            created_by=created_by,
            updated_by=created_by,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _to_user_dict(row)


def update_user(user_id: str | UUID, *, patch: Dict[str, Any], updated_by: str | UUID | None) -> Optional[Dict[str, Any]]:
    """Aplica una actualización parcial sobre un usuario existente."""
    with SessionLocal() as db:
        stmt = select(UserORM).where(UserORM.id == user_id)
        row = db.scalar(stmt)
        if not row:
            return None

        for k, v in patch.items():
            if hasattr(row, k):
                setattr(row, k, v)
        row.updated_by = updated_by
        db.commit()
        db.refresh(row)
        return _to_user_dict(row)


def set_user_active(user_id: str | UUID, *, is_active: bool, updated_by: str | UUID | None) -> Optional[Dict[str, Any]]:
    """Activa o desactiva lógicamente una cuenta de usuario."""
    now = datetime.now(timezone.utc)
    patch = {"is_active": bool(is_active), "disabled_at": None if is_active else now}
    return update_user(user_id, patch=patch, updated_by=updated_by)


def set_last_login(user_id: str | UUID) -> None:
    """Actualiza la fecha del último acceso satisfactorio del usuario."""
    with SessionLocal() as db:
        stmt = select(UserORM).where(UserORM.id == user_id)
        row = db.scalar(stmt)
        if not row:
            return
        row.last_login_at = datetime.now(timezone.utc)
        db.commit()


def has_opportunities_created_by(user_id: str | UUID) -> bool:
    """Indica si un usuario ha creado oportunidades en el sistema."""
    from infrastructure.db.models import OpportunityQualificationORM

    with SessionLocal() as db:
        stmt = select(OpportunityQualificationORM.id).where(
            OpportunityQualificationORM.created_by_user_id == user_id
        ).limit(1)
        return db.scalar(stmt) is not None


def has_technical_decisions_by(user_id: str | UUID) -> bool:
    """Comprueba si un usuario ha emitido decisiones técnicas sobre oportunidades."""
    from infrastructure.db.models import OpportunityQualificationORM

    with SessionLocal() as db:
        stmt = select(OpportunityQualificationORM.id).where(
            OpportunityQualificationORM.technical_decision_by_user_id == user_id
        ).limit(1)
        return db.scalar(stmt) is not None


def set_user_password(user_id: str | UUID, *, password_hash: str, updated_by: str | UUID | None) -> bool:
    """Guarda una nueva contraseña hash y limpia el flag de cambio obligatorio."""
    with SessionLocal() as db:
        stmt = select(UserORM).where(UserORM.id == user_id)
        row = db.scalar(stmt)
        if not row:
            return False
        row.password_hash = password_hash
        row.must_change_password = False
        row.updated_by = updated_by
        db.commit()
        return True


def create_password_reset_token(
    *,
    user_id: str | UUID,
    token_hash: str,
    expires_at: datetime,
    created_by: str | UUID | None,
) -> None:
    """Persiste un token temporal de reseteo de contraseña para un usuario."""
    with SessionLocal() as db:
        row = UserPasswordResetTokenORM(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_by=created_by,
        )
        db.add(row)
        db.commit()


def consume_password_reset_token(token_hash: str) -> Optional[Dict[str, Any]]:
    """Marca un token como usado y devuelve el usuario asociado si sigue vigente."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        stmt = (
            select(UserPasswordResetTokenORM)
            .where(UserPasswordResetTokenORM.token_hash == token_hash)
            .where(UserPasswordResetTokenORM.used_at.is_(None))
        )
        row = db.scalar(stmt)
        if not row or row.expires_at < now:
            return None
        row.used_at = now
        db.commit()
        return {"user_id": row.user_id}
