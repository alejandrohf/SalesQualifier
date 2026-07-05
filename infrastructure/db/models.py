"""Modelos ORM persistentes de la plataforma.

Define las tablas principales de referencias, embeddings, oportunidades,
usuarios y tokens de reseteo de contraseña.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from pgvector.sqlalchemy import Vector

from infrastructure.db.base import Base


class CustomerReferenceORM(Base):
    """Entidad ORM que representa una referencia corporativa reusable y su metadata."""
    __tablename__ = "customer_references"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    customer: Mapped[str] = mapped_column(Text, nullable=False)

    industry: Mapped[str] = mapped_column(Text, nullable=False)
    area: Mapped[str] = mapped_column(Text, nullable=False)
    cloud: Mapped[str] = mapped_column(Text, nullable=False)
    size: Mapped[str] = mapped_column(Text, nullable=False)

    document_path: Mapped[str] = mapped_column(Text, nullable=False)
    document_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    embeddings: Mapped[list["ReferenceEmbeddingORM"]] = relationship(
        back_populates="reference",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("idx_refs_customer", "customer"),
        Index("idx_refs_industry", "industry"),
        Index("idx_refs_area", "area"),
        Index("idx_refs_updated_at", "updated_at"),
    )


class ReferenceEmbeddingORM(Base):
    """Fragmento indexado de una referencia con su embedding vectorial asociado."""
    __tablename__ = "reference_embeddings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    reference_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_references.id", ondelete="CASCADE"),
        nullable=False,
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256 hex
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ⚠️ Ajusta dimensión si usas embedding 3072
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    reference: Mapped["CustomerReferenceORM"] = relationship(back_populates="embeddings")

    __table_args__ = (
        Index("uq_ref_chunk", "reference_id", "chunk_index", unique=True),
        # ivfflat index se crea normalmente por SQL (o migración), pero aquí lo dejamos como DDL externo
    )


class OpportunityQualificationORM(Base):
    """Persistencia de una oportunidad cualificada y de su ciclo de revisión técnica."""
    __tablename__ = "opportunity_qualifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    request_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    response_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    trace_payload: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    assigned_engineering_user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), nullable=True)
    technical_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    technical_decision_by_user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), nullable=True)
    technical_decision_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    technical_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_oppq_timestamp", "timestamp"),
        Index("idx_oppq_created_at", "created_at"),
        Index("idx_oppq_opportunity_id", "opportunity_id", unique=True),
        Index("idx_oppq_created_by_user_id", "created_by_user_id"),
        Index("idx_oppq_technical_status", "technical_status"),
    )


class UserORM(Base):
    """Modelo ORM de usuario con capacidades, trazabilidad y estado de acceso."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_sales: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_engineering: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    password_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    engineering_manager_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), nullable=True)
    disabled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_users_email", "email", unique=True),
        Index("idx_users_role", "role"),
        Index("idx_users_is_active", "is_active"),
    )


class UserPasswordResetTokenORM(Base):
    """Token de un solo uso para alta inicial o reseteo de contraseña."""
    __tablename__ = "user_password_reset_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_uprt_user_id", "user_id"),
        Index("idx_uprt_expires_at", "expires_at"),
        Index("idx_uprt_used_at", "used_at"),
    )
