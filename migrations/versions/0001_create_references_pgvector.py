from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "0001_create_references_pgvector"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extensiones
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # customer_references
    op.create_table(
        "customer_references",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("customer", sa.Text(), nullable=False),
        sa.Column("industry", sa.Text(), nullable=False),
        sa.Column("area", sa.Text(), nullable=False),
        sa.Column("cloud", sa.Text(), nullable=False),
        sa.Column("size", sa.Text(), nullable=False),
        sa.Column("document_path", sa.Text(), nullable=False),
        sa.Column("document_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_index("idx_refs_customer", "customer_references", ["customer"])
    op.create_index("idx_refs_industry", "customer_references", ["industry"])
    op.create_index("idx_refs_area", "customer_references", ["area"])
    op.execute("CREATE INDEX IF NOT EXISTS idx_refs_updated_at ON customer_references(updated_at DESC);")

    # reference_embeddings (Vector 1536)
    op.create_table(
        "reference_embeddings",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "reference_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customer_references.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_hash", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=False),  # text-embedding-3-small
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_index("uq_ref_chunk", "reference_embeddings", ["reference_id", "chunk_index"], unique=True)

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ref_embed_ivfflat
        ON reference_embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_ref_embed_ivfflat;")
    op.drop_index("uq_ref_chunk", table_name="reference_embeddings")
    op.drop_table("reference_embeddings")

    op.execute("DROP INDEX IF EXISTS idx_refs_updated_at;")
    op.drop_index("idx_refs_area", table_name="customer_references")
    op.drop_index("idx_refs_industry", table_name="customer_references")
    op.drop_index("idx_refs_customer", table_name="customer_references")
    op.drop_table("customer_references")
