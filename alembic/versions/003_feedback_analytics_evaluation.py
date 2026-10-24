"""feedback, analytics, evaluation, review, and learning foundations

Revision ID: 003_feedback_analytics_evaluation
Revises: 002_monitoring_and_notifications
Create Date: 2026-09-25 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003_feedback_analytics_evaluation"
down_revision: str | None = "002_monitoring_and_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. users: add role column
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=20), nullable=False, server_default="USER"),
    )

    # 2. feedback_records
    op.create_table(
        "feedback_records",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.String(length=255), nullable=False),
        sa.Column("feedback_type", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.String(length=100), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("context_snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="NEW"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_feedback_records_id", "feedback_records", ["id"])
    op.create_index("ix_feedback_records_user_id", "feedback_records", ["user_id"])
    op.create_index("ix_feedback_records_target_type", "feedback_records", ["target_type"])
    op.create_index("ix_feedback_records_target_id", "feedback_records", ["target_id"])
    op.create_index("ix_feedback_records_feedback_type", "feedback_records", ["feedback_type"])
    op.create_index("ix_feedback_records_reason", "feedback_records", ["reason"])
    op.create_index("ix_feedback_records_status", "feedback_records", ["status"])

    # 3. user_events
    op.create_table(
        "user_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("anonymous_session_id", sa.String(length=100), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("entity_type", sa.String(length=100), nullable=True),
        sa.Column("entity_id", sa.String(length=255), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("session_id", sa.String(length=100), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "application_version", sa.String(length=50), nullable=False, server_default="1.0.0"
        ),
        sa.Column("platform", sa.String(length=50), nullable=False, server_default="mobile"),
        sa.Column("locale", sa.String(length=20), nullable=False, server_default="en"),
    )
    op.create_index("ix_user_events_id", "user_events", ["id"])
    op.create_index("ix_user_events_user_id", "user_events", ["user_id"])
    op.create_index("ix_user_events_event_type", "user_events", ["event_type"])
    op.create_index("ix_user_events_timestamp", "user_events", ["timestamp"])

    # 4. search_evaluation_records
    op.create_table(
        "search_evaluation_records",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("query", sa.String(length=500), nullable=False),
        sa.Column("search_session_id", sa.String(length=100), nullable=True),
        sa.Column("results_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_domains_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("no_results", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("source_quality_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_search_evaluation_records_id", "search_evaluation_records", ["id"])
    op.create_index("ix_search_evaluation_records_query", "search_evaluation_records", ["query"])

    # 5. datasets
    op.create_table(
        "datasets",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("task_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_datasets_id", "datasets", ["id"])
    op.create_index("ix_datasets_name", "datasets", ["name"], unique=True)
    op.create_index("ix_datasets_task_type", "datasets", ["task_type"])

    # 6. dataset_versions
    op.create_table(
        "dataset_versions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_tag", sa.String(length=50), nullable=False),
        sa.Column("example_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("schema_version", sa.String(length=20), nullable=False, server_default="1.0.0"),
        sa.Column("quality_status", sa.String(length=50), nullable=False, server_default="DRAFT"),
        sa.Column("split_counts", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dataset_versions_id", "dataset_versions", ["id"])
    op.create_index("ix_dataset_versions_dataset_id", "dataset_versions", ["dataset_id"])
    op.create_index("ix_dataset_versions_version_tag", "dataset_versions", ["version_tag"])

    # 7. dataset_examples
    op.create_table(
        "dataset_examples",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_version_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("split", sa.String(length=20), nullable=False, server_default="TRAIN"),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("expected_output", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("provenance_review_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dataset_examples_id", "dataset_examples", ["id"])
    op.create_index(
        "ix_dataset_examples_dataset_version_id", "dataset_examples", ["dataset_version_id"]
    )
    op.create_index("ix_dataset_examples_split", "dataset_examples", ["split"])

    # 8. evaluation_runs
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "model_provider", sa.String(length=50), nullable=False, server_default="deterministic"
        ),
        sa.Column("model_name", sa.String(length=100), nullable=False, server_default="rules"),
        sa.Column("model_version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column("prompt_name", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column(
            "dataset_version_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("dataset_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("metrics_summary", sa.JSON(), nullable=False),
        sa.Column("claim_evaluations", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("code_version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column("environment", sa.String(length=50), nullable=False, server_default="test"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evaluation_runs_id", "evaluation_runs", ["id"])
    op.create_index(
        "ix_evaluation_runs_dataset_version_id", "evaluation_runs", ["dataset_version_id"]
    )
    op.create_index("ix_evaluation_runs_status", "evaluation_runs", ["status"])

    # 9. error_clusters
    op.create_table(
        "error_clusters",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("error_type", sa.String(length=50), nullable=False),
        sa.Column("fingerprint", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("affected_field", sa.String(length=100), nullable=True),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sample_feedback_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="ACTIVE"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_error_clusters_id", "error_clusters", ["id"])
    op.create_index("ix_error_clusters_fingerprint", "error_clusters", ["fingerprint"], unique=True)
    op.create_index("ix_error_clusters_error_type", "error_clusters", ["error_type"])

    # 10. review_queue_items
    op.create_table(
        "review_queue_items",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence_url", sa.String(length=1000), nullable=True),
        sa.Column("current_system_output", sa.JSON(), nullable=False),
        sa.Column(
            "user_feedback_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("feedback_records.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="NORMAL"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column(
            "assigned_to",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_review_queue_items_id", "review_queue_items", ["id"])
    op.create_index("ix_review_queue_items_category", "review_queue_items", ["category"])
    op.create_index("ix_review_queue_items_status", "review_queue_items", ["status"])

    # 11. human_corrections
    op.create_table(
        "human_corrections",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "review_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("review_queue_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_value", sa.JSON(), nullable=False),
        sa.Column("corrected_value", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column(
            "reviewer_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reason", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_human_corrections_id", "human_corrections", ["id"])
    op.create_index("ix_human_corrections_review_id", "human_corrections", ["review_id"])

    # 12. model_definitions
    op.create_table(
        "model_definitions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("model_id", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_type", sa.String(length=50), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("configuration_reference", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_model_definitions_id", "model_definitions", ["id"])
    op.create_index("ix_model_definitions_model_id", "model_definitions", ["model_id"], unique=True)

    # 13. prompt_versions
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("prompt_name", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("task", sa.String(length=100), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prompt_versions_id", "prompt_versions", ["id"])
    op.create_index("ix_prompt_versions_prompt_name", "prompt_versions", ["prompt_name"])
    op.create_index("ix_prompt_versions_prompt_version", "prompt_versions", ["prompt_version"])

    # 14. experiments
    op.create_table(
        "experiments",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("hypothesis", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="DRAFT"),
        sa.Column("target_metric", sa.String(length=100), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_experiments_id", "experiments", ["id"])
    op.create_index("ix_experiments_name", "experiments", ["name"], unique=True)

    # 15. experiment_variants
    op.create_table(
        "experiment_variants",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "experiment_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("variant_key", sa.String(length=50), nullable=False),
        sa.Column("traffic_percentage", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_experiment_variants_id", "experiment_variants", ["id"])
    op.create_index(
        "ix_experiment_variants_experiment_id", "experiment_variants", ["experiment_id"]
    )

    # 16. experiment_assignments
    op.create_table(
        "experiment_assignments",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "experiment_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("variant_key", sa.String(length=50), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_experiment_assignments_id", "experiment_assignments", ["id"])
    op.create_index(
        "ix_experiment_assignments_experiment_id", "experiment_assignments", ["experiment_id"]
    )
    op.create_index("ix_experiment_assignments_user_id", "experiment_assignments", ["user_id"])


def downgrade() -> None:
    op.drop_table("experiment_assignments")
    op.drop_table("experiment_variants")
    op.drop_table("experiments")
    op.drop_table("prompt_versions")
    op.drop_table("model_definitions")
    op.drop_table("human_corrections")
    op.drop_table("review_queue_items")
    op.drop_table("error_clusters")
    op.drop_table("evaluation_runs")
    op.drop_table("dataset_examples")
    op.drop_table("dataset_versions")
    op.drop_table("datasets")
    op.drop_table("search_evaluation_records")
    op.drop_table("user_events")
    op.drop_table("feedback_records")
    op.drop_column("users", "role")
