"""010 Comprehensive Opportunity Preferences and Decision Support

Revision ID: 010_comprehensive_opportunity_preferences
Revises: 009_experience_system_and_career_summary
Create Date: 2026-10-26 22:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010_comprehensive_opportunity_preferences"
down_revision: str | None = "009_experience_system_and_career_summary"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("user_preferences") as batch_op:
        batch_op.add_column(
            sa.Column("target_degree_levels", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("excluded_countries", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("willing_to_relocate", sa.Boolean(), nullable=False, server_default="1")
        )
        batch_op.add_column(
            sa.Column("funding_types", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("funding_priorities", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(sa.Column("max_annual_tuition", sa.Float(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "financial_currency",
                sa.String(length=10),
                nullable=False,
                server_default="USD",
            )
        )
        batch_op.add_column(
            sa.Column("requires_no_application_fee", sa.Boolean(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("requires_no_ielts", sa.Boolean(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("language_preferences", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("language_test_status", sa.JSON(), nullable=False, server_default="{}")
        )
        batch_op.add_column(
            sa.Column("admission_test_status", sa.JSON(), nullable=False, server_default="{}")
        )
        batch_op.add_column(
            sa.Column("study_formats", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("duration_preferences", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("preferred_start_terms", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("career_priorities", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("hard_constraints", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("preferences_metadata", sa.JSON(), nullable=False, server_default="{}")
        )


def downgrade() -> None:
    with op.batch_alter_table("user_preferences") as batch_op:
        batch_op.drop_column("preferences_metadata")
        batch_op.drop_column("hard_constraints")
        batch_op.drop_column("career_priorities")
        batch_op.drop_column("preferred_start_terms")
        batch_op.drop_column("duration_preferences")
        batch_op.drop_column("study_formats")
        batch_op.drop_column("admission_test_status")
        batch_op.drop_column("language_test_status")
        batch_op.drop_column("language_preferences")
        batch_op.drop_column("requires_no_ielts")
        batch_op.drop_column("requires_no_application_fee")
        batch_op.drop_column("financial_currency")
        batch_op.drop_column("max_annual_tuition")
        batch_op.drop_column("funding_priorities")
        batch_op.drop_column("funding_types")
        batch_op.drop_column("willing_to_relocate")
        batch_op.drop_column("excluded_countries")
        batch_op.drop_column("target_degree_levels")
