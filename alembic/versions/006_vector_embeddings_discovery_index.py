"""006 Vector Embeddings and Discovery Search Index

Revision ID: 006_vector_embeddings_discovery_index
Revises: 005_production_infrastructure_auth_security
Create Date: 2026-10-08 16:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_vector_embeddings_discovery_index"
down_revision: str | None = "005_production_infrastructure_auth_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create opportunity_embeddings table
    op.create_table(
        "opportunity_embeddings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("embedding_type", sa.String(length=50), nullable=False, server_default="FULL"),
        sa.Column("vector_data", sa.JSON(), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column(
            "embedding_provider", sa.String(length=50), nullable=False, server_default="LOCAL"
        ),
        sa.Column(
            "embedding_version", sa.String(length=50), nullable=False, server_default="v1.0.0"
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_opportunity_embeddings_opportunity_id",
        "opportunity_embeddings",
        ["opportunity_id"],
    )
    op.create_index(
        "ix_opportunity_embeddings_type",
        "opportunity_embeddings",
        ["embedding_type"],
    )
    op.create_index(
        "ix_opportunity_embeddings_content_hash",
        "opportunity_embeddings",
        ["content_hash"],
    )
    op.create_index(
        "ix_opportunity_embeddings_version",
        "opportunity_embeddings",
        ["embedding_version"],
    )
    op.create_index(
        "ix_opportunity_embeddings_active",
        "opportunity_embeddings",
        ["is_active"],
    )

    # 2. Create discovery_search_sessions table
    op.create_table(
        "discovery_search_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("original_query", sa.Text(), nullable=False),
        sa.Column("normalized_query", sa.Text(), nullable=False),
        sa.Column("expanded_queries", sa.JSON(), nullable=False),
        sa.Column(
            "retrieval_strategy", sa.String(length=50), nullable=False, server_default="HYBRID"
        ),
        sa.Column("filters_applied", sa.JSON(), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_ids", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("embedding_model_used", sa.String(length=100), nullable=True),
        sa.Column("reranker_used", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_discovery_search_sessions_user_id",
        "discovery_search_sessions",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_table("discovery_search_sessions")
    op.drop_table("opportunity_embeddings")
