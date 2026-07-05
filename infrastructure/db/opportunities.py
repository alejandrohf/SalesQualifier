"""Acceso a datos para oportunidades cualificadas y revisión técnica.

Este módulo encapsula las operaciones de persistencia y consulta sobre el
histórico de oportunidades procesadas por la plataforma.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import desc, func, select
from sqlalchemy.exc import ProgrammingError

from infrastructure.db.models import OpportunityQualificationORM
from infrastructure.db.session import SessionLocal


def _is_missing_table_error(e: Exception) -> bool:
    msg = str(e).lower()
    return "opportunity_qualifications" in msg and (
        "does not exist" in msg or "undefinedtable" in msg
    )


def save_opportunity_qualification(
    *,
    opportunity_id: str,
    timestamp: datetime,
    request_payload: Dict[str, Any],
    response_payload: Dict[str, Any],
    trace_payload: List[Any],
    created_by_user_id: str | None = None,
    created_by_email: str | None = None,
    assigned_engineering_user_id: str | None = None,
    technical_status: str = "pending",
) -> None:
    """Persiste una oportunidad procesada junto con request, response y traza del workflow."""
    try:
        with SessionLocal() as db:
            row = OpportunityQualificationORM(
                opportunity_id=opportunity_id,
                timestamp=timestamp,
                request_payload=request_payload,
                response_payload=response_payload,
                trace_payload=trace_payload,
                created_by_user_id=created_by_user_id,
                created_by_email=created_by_email,
                assigned_engineering_user_id=assigned_engineering_user_id,
                technical_status=technical_status,
            )
            db.add(row)
            db.commit()
    except ProgrammingError as e:
        if _is_missing_table_error(e):
            raise RuntimeError(
                "Tabla 'opportunity_qualifications' no existe. Ejecuta migraciones: ./venv/bin/alembic upgrade head"
            ) from e
        raise


def list_opportunity_qualifications(limit: int = 500, offset: int = 0) -> List[Dict[str, Any]]:
    """Recupera el histórico de oportunidades cualificadas en orden descendente de fecha."""
    try:
        with SessionLocal() as db:
            stmt = (
                select(OpportunityQualificationORM)
                .order_by(desc(OpportunityQualificationORM.timestamp))
                .limit(limit)
                .offset(offset)
            )
            rows = list(db.scalars(stmt).all())
    except ProgrammingError as e:
        if _is_missing_table_error(e):
            return []
        raise

    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "opportunity_id": r.opportunity_id,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "request": r.request_payload or {},
                "response": r.response_payload or {},
                "trace": r.trace_payload or [],
                "created_by_user_id": r.created_by_user_id,
                "created_by_email": r.created_by_email,
                "assigned_engineering_user_id": r.assigned_engineering_user_id,
                "technical_status": r.technical_status,
                "technical_decision_by_user_id": r.technical_decision_by_user_id,
                "technical_decision_at": r.technical_decision_at.isoformat() if r.technical_decision_at else None,
                "technical_comment": r.technical_comment,
            }
        )
    return out


def count_opportunity_qualifications() -> int:
    """Cuenta cuántas oportunidades han sido registradas en persistencia."""
    try:
        with SessionLocal() as db:
            stmt = select(func.count(OpportunityQualificationORM.id))
            return int(db.scalar(stmt) or 0)
    except ProgrammingError as e:
        if _is_missing_table_error(e):
            return 0
        raise


def get_opportunity_qualification_by_id(opportunity_id: str) -> Dict[str, Any] | None:
    """Obtiene una oportunidad concreta a partir de su identificador funcional."""
    try:
        with SessionLocal() as db:
            stmt = select(OpportunityQualificationORM).where(
                OpportunityQualificationORM.opportunity_id == opportunity_id
            )
            r = db.scalar(stmt)
    except ProgrammingError as e:
        if _is_missing_table_error(e):
            return None
        raise
    if not r:
        return None
    return {
        "opportunity_id": r.opportunity_id,
        "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        "request": r.request_payload or {},
        "response": r.response_payload or {},
        "trace": r.trace_payload or [],
        "created_by_user_id": r.created_by_user_id,
        "created_by_email": r.created_by_email,
        "assigned_engineering_user_id": r.assigned_engineering_user_id,
        "technical_status": r.technical_status,
        "technical_decision_by_user_id": r.technical_decision_by_user_id,
        "technical_decision_at": r.technical_decision_at.isoformat() if r.technical_decision_at else None,
        "technical_comment": r.technical_comment,
    }


def set_technical_decision(
    *,
    opportunity_id: str,
    technical_status: str,
    technical_decision_by_user_id: str | None,
    technical_comment: str | None,
) -> bool:
    """Registra la decisión técnica GO/NO GO y sus metadatos de auditoría."""
    try:
        with SessionLocal() as db:
            stmt = select(OpportunityQualificationORM).where(
                OpportunityQualificationORM.opportunity_id == opportunity_id
            )
            row = db.scalar(stmt)
            if not row:
                return False
            row.technical_status = technical_status
            row.technical_decision_by_user_id = technical_decision_by_user_id
            row.technical_comment = technical_comment
            row.technical_decision_at = datetime.now(timezone.utc)
            db.commit()
            return True
    except ProgrammingError as e:
        if _is_missing_table_error(e):
            return False
        raise
