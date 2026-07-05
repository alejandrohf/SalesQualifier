from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0002_opp_qualifications"
down_revision = "0001_create_references_pgvector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "opportunity_qualifications",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("opportunity_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("trace_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_index("idx_oppq_timestamp", "opportunity_qualifications", ["timestamp"])
    op.create_index("idx_oppq_created_at", "opportunity_qualifications", ["created_at"])
    op.create_index("idx_oppq_opportunity_id", "opportunity_qualifications", ["opportunity_id"], unique=True)


def downgrade() -> None:
    op.drop_index("idx_oppq_opportunity_id", table_name="opportunity_qualifications")
    op.drop_index("idx_oppq_created_at", table_name="opportunity_qualifications")
    op.drop_index("idx_oppq_timestamp", table_name="opportunity_qualifications")
    op.drop_table("opportunity_qualifications")
