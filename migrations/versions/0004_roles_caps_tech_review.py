from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_roles_caps_tech"
down_revision = "0003_auth_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users: capacidades separadas de admin
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("users", sa.Column("can_sales", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("users", sa.Column("can_engineering", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    # Actualizamos el rol con las opciones de ventas e ingeniería.
    op.execute(
        """
        UPDATE users
        SET is_admin = CASE WHEN lower(coalesce(role, '')) = 'admin' THEN true ELSE is_admin END,
            can_sales = CASE WHEN lower(coalesce(role, '')) = 'sales' THEN true ELSE can_sales END,
            can_engineering = CASE WHEN lower(coalesce(role, '')) = 'engineering' THEN true ELSE can_engineering END
        """
    )

    # opportunity_qualifications: auditoría de autoría + decisión técnica
    op.add_column("opportunity_qualifications", sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("opportunity_qualifications", sa.Column("created_by_email", sa.String(length=255), nullable=True))
    op.add_column("opportunity_qualifications", sa.Column("assigned_engineering_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("opportunity_qualifications", sa.Column("technical_status", sa.String(length=24), nullable=False, server_default="pending"))
    op.add_column("opportunity_qualifications", sa.Column("technical_decision_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("opportunity_qualifications", sa.Column("technical_decision_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("opportunity_qualifications", sa.Column("technical_comment", sa.Text(), nullable=True))

    op.create_index("idx_oppq_created_by_user_id", "opportunity_qualifications", ["created_by_user_id"])
    op.create_index("idx_oppq_technical_status", "opportunity_qualifications", ["technical_status"])


def downgrade() -> None:
    op.drop_index("idx_oppq_technical_status", table_name="opportunity_qualifications")
    op.drop_index("idx_oppq_created_by_user_id", table_name="opportunity_qualifications")

    op.drop_column("opportunity_qualifications", "technical_comment")
    op.drop_column("opportunity_qualifications", "technical_decision_at")
    op.drop_column("opportunity_qualifications", "technical_decision_by_user_id")
    op.drop_column("opportunity_qualifications", "technical_status")
    op.drop_column("opportunity_qualifications", "assigned_engineering_user_id")
    op.drop_column("opportunity_qualifications", "created_by_email")
    op.drop_column("opportunity_qualifications", "created_by_user_id")

    op.drop_column("users", "can_engineering")
    op.drop_column("users", "can_sales")
    op.drop_column("users", "is_admin")
