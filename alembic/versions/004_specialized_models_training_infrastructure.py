"""specialized AI models, training jobs, artifacts, model cards, and registry extensions

Revision ID: 004_specialized_models_training_infrastructure
Revises: 003_feedback_analytics_evaluation
Create Date: 2026-10-07 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "004_specialized_models_training_infrastructure"
down_revision: str | None = "003_feedback_analytics_evaluation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. model_definitions extensions
    op.add_column(
        "model_definitions",
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PRODUCTION"),
    )
    op.add_column(
        "model_definitions",
        sa.Column("canary_percentage", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "model_definitions",
        sa.Column("rollback_model_id", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "model_definitions",
        sa.Column(
            "architecture",
            sa.String(length=100),
            nullable=True,
            server_default="transformer",
        ),
    )
    op.add_column(
        "model_definitions",
        sa.Column("cost_tier", sa.String(length=50), nullable=False, server_default="LOW"),
    )
    op.add_column(
        "model_definitions",
        sa.Column("health_status", sa.String(length=50), nullable=False, server_default="HEALTHY"),
    )
    op.create_index("ix_model_definitions_status", "model_definitions", ["status"])

    # 2. training_jobs
    op.create_table(
        "training_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("job_name", sa.String(length=150), nullable=False),
        sa.Column("task", sa.String(length=50), nullable=False),
        sa.Column(
            "dataset_version_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("dataset_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("base_model", sa.String(length=150), nullable=False),
        sa.Column("training_backend", sa.String(length=50), nullable=False, server_default="LOCAL"),
        sa.Column("hyperparameters", sa.JSON(), nullable=False),
        sa.Column("resource_limits", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="QUEUED"),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("logs", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_training_jobs_id", "training_jobs", ["id"])
    op.create_index("ix_training_jobs_job_name", "training_jobs", ["job_name"])
    op.create_index("ix_training_jobs_task", "training_jobs", ["task"])
    op.create_index("ix_training_jobs_status", "training_jobs", ["status"])
    op.create_index("ix_training_jobs_dataset_version_id", "training_jobs", ["dataset_version_id"])

    # 3. model_artifacts
    op.create_table(
        "model_artifacts",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "model_definition_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("model_definitions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "training_job_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("training_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("artifact_path", sa.String(length=500), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("framework", sa.String(length=50), nullable=False, server_default="pytorch"),
        sa.Column("artifact_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_model_artifacts_id", "model_artifacts", ["id"])
    op.create_index(
        "ix_model_artifacts_model_definition_id",
        "model_artifacts",
        ["model_definition_id"],
    )
    op.create_index(
        "ix_model_artifacts_training_job_id",
        "model_artifacts",
        ["training_job_id"],
    )

    # 4. model_cards
    op.create_table(
        "model_cards",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "model_definition_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("model_definitions.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("purpose", sa.Text(), nullable=False, server_default=""),
        sa.Column("task", sa.String(length=100), nullable=False),
        sa.Column("intended_use", sa.Text(), nullable=False, server_default=""),
        sa.Column("non_intended_use", sa.Text(), nullable=False, server_default=""),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("evaluation_metrics", sa.JSON(), nullable=False),
        sa.Column("training_data_provenance", sa.JSON(), nullable=False),
        sa.Column("license", sa.String(length=100), nullable=False, server_default="MIT"),
        sa.Column("ethical_considerations", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_model_cards_id", "model_cards", ["id"])
    op.create_index(
        "ix_model_cards_model_definition_id",
        "model_cards",
        ["model_definition_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("model_cards")
    op.drop_table("model_artifacts")
    op.drop_table("training_jobs")
    op.drop_index("ix_model_definitions_status", table_name="model_definitions")
    op.drop_column("model_definitions", "health_status")
    op.drop_column("model_definitions", "cost_tier")
    op.drop_column("model_definitions", "architecture")
    op.drop_column("model_definitions", "rollback_model_id")
    op.drop_column("model_definitions", "canary_percentage")
    op.drop_column("model_definitions", "status")
