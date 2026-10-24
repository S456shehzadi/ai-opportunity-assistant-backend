"""monitoring and notifications data foundation

Revision ID: 002_monitoring_and_notifications
Revises: 001_initial_foundation
Create Date: 2026-09-25 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002_monitoring_and_notifications"
down_revision: str | None = "001_initial_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. opportunity_change_events
    op.create_table(
        "opportunity_change_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "opportunity_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("opportunity_sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("change_type", sa.String(length=50), nullable=False),
        sa.Column("affected_field", sa.String(length=100), nullable=False),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("source_trust", sa.String(length=50), nullable=False, server_default="HIGH"),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "notification_priority", sa.String(length=20), nullable=False, server_default="NORMAL"
        ),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_opportunity_change_events_id", "opportunity_change_events", ["id"])
    op.create_index(
        "ix_opportunity_change_events_opportunity_id",
        "opportunity_change_events",
        ["opportunity_id"],
    )
    op.create_index(
        "ix_opportunity_change_events_source_id",
        "opportunity_change_events",
        ["source_id"],
    )
    op.create_index(
        "ix_opportunity_change_events_change_type",
        "opportunity_change_events",
        ["change_type"],
    )
    op.create_index(
        "ix_opportunity_change_events_affected_field",
        "opportunity_change_events",
        ["affected_field"],
    )
    op.create_index(
        "ix_opportunity_change_events_verified",
        "opportunity_change_events",
        ["verified"],
    )
    op.create_index(
        "ix_opportunity_change_events_notification_priority",
        "opportunity_change_events",
        ["notification_priority"],
    )
    op.create_index(
        "ix_opportunity_change_events_processed",
        "opportunity_change_events",
        ["processed"],
    )
    op.create_index(
        "ix_opportunity_change_events_detected_at",
        "opportunity_change_events",
        ["detected_at"],
    )

    # 2. opportunity_subscriptions
    op.create_table(
        "opportunity_subscriptions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opportunity_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("monitoring_frequency", sa.String(length=50), nullable=False),
        sa.Column("monitoring_status", sa.String(length=50), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notification_channels", sa.JSON(), nullable=False),
        sa.Column("important_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "deadline_alerts_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "funding_change_alerts_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "requirement_change_alerts_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "status_change_alerts_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_opportunity_subscriptions_id", "opportunity_subscriptions", ["id"])
    op.create_index(
        "ix_opportunity_subscriptions_user_id",
        "opportunity_subscriptions",
        ["user_id"],
    )
    op.create_index(
        "ix_opportunity_subscriptions_opportunity_id",
        "opportunity_subscriptions",
        ["opportunity_id"],
    )
    op.create_index(
        "ix_opportunity_subscriptions_monitoring_status",
        "opportunity_subscriptions",
        ["monitoring_status"],
    )
    op.create_index(
        "ix_opportunity_subscriptions_next_check_at",
        "opportunity_subscriptions",
        ["next_check_at"],
    )

    # 3. search_subscriptions
    op.create_table(
        "search_subscriptions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("query", sa.String(length=500), nullable=False),
        sa.Column("normalized_search_intent", sa.JSON(), nullable=True),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("monitoring_frequency", sa.String(length=50), nullable=False),
        sa.Column("monitoring_status", sa.String(length=50), nullable=False),
        sa.Column("last_searched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_search_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_result_fingerprint", sa.String(length=255), nullable=True),
        sa.Column("known_opportunity_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_search_subscriptions_id", "search_subscriptions", ["id"])
    op.create_index("ix_search_subscriptions_user_id", "search_subscriptions", ["user_id"])
    op.create_index(
        "ix_search_subscriptions_monitoring_status",
        "search_subscriptions",
        ["monitoring_status"],
    )
    op.create_index(
        "ix_search_subscriptions_next_search_at",
        "search_subscriptions",
        ["next_search_at"],
    )

    # 4. monitoring_jobs
    op.create_table(
        "monitoring_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_monitoring_jobs_id", "monitoring_jobs", ["id"])
    op.create_index("ix_monitoring_jobs_job_type", "monitoring_jobs", ["job_type"])
    op.create_index("ix_monitoring_jobs_target_id", "monitoring_jobs", ["target_id"])
    op.create_index("ix_monitoring_jobs_status", "monitoring_jobs", ["status"])
    op.create_index("ix_monitoring_jobs_scheduled_at", "monitoring_jobs", ["scheduled_at"])

    # 5. monitoring_executions
    op.create_table(
        "monitoring_executions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("monitoring_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_monitoring_executions_id", "monitoring_executions", ["id"])
    op.create_index("ix_monitoring_executions_job_id", "monitoring_executions", ["job_id"])

    # 6. notifications
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opportunity_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "change_event_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("opportunity_change_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("deduplication_key", sa.String(length=255), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notifications_id", "notifications", ["id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_opportunity_id", "notifications", ["opportunity_id"])
    op.create_index("ix_notifications_change_event_id", "notifications", ["change_event_id"])
    op.create_index("ix_notifications_notification_type", "notifications", ["notification_type"])
    op.create_index("ix_notifications_priority", "notifications", ["priority"])
    op.create_index("ix_notifications_deduplication_key", "notifications", ["deduplication_key"])
    op.create_index("ix_notifications_read_at", "notifications", ["read_at"])

    # 7. notification_deliveries
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "notification_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("notifications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notification_deliveries_id", "notification_deliveries", ["id"])
    op.create_index(
        "ix_notification_deliveries_notification_id",
        "notification_deliveries",
        ["notification_id"],
    )

    # 8. notification_preferences
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("enable_notifications", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("enable_in_app", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("enable_push", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("enable_email", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("enable_deadline_alerts", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("enable_funding_alerts", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "enable_eligibility_alerts", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "enable_new_opportunity_alerts", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("enable_status_alerts", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "important_changes_only", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("daily_notification_limit", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("quiet_hours_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("quiet_hours_start", sa.String(length=5), nullable=True, server_default="22:00"),
        sa.Column("quiet_hours_end", sa.String(length=5), nullable=True, server_default="08:00"),
        sa.Column(
            "quiet_hours_timezone", sa.String(length=50), nullable=False, server_default="UTC"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notification_preferences_id", "notification_preferences", ["id"])
    op.create_index(
        "ix_notification_preferences_user_id",
        "notification_preferences",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
    op.drop_table("notification_deliveries")
    op.drop_table("notifications")
    op.drop_table("monitoring_executions")
    op.drop_table("monitoring_jobs")
    op.drop_table("search_subscriptions")
    op.drop_table("opportunity_subscriptions")
    op.drop_table("opportunity_change_events")
