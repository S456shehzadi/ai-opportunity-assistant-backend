"""011 Global Location Context, Worldwide Country Coverage and Geographic Flexibility

Revision ID: 011_global_location_and_worldwide_discovery
Revises: 010_comprehensive_opportunity_preferences
Create Date: 2026-10-26 23:25:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011_global_location_and_worldwide_discovery"
down_revision: str | None = "010_comprehensive_opportunity_preferences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. User Profiles
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.add_column(
            sa.Column("citizenships", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("previous_education_country", sa.String(length=100), nullable=True)
        )

    # 2. User Preferences
    with op.batch_alter_table("user_preferences") as batch_op:
        batch_op.add_column(
            sa.Column(
                "discovery_mode",
                sa.String(length=30),
                nullable=False,
                server_default="flexible",
            )
        )
        batch_op.add_column(
            sa.Column("acceptable_countries", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("willing_to_travel", sa.Boolean(), nullable=False, server_default="1")
        )
        batch_op.add_column(
            sa.Column("open_to_remote", sa.Boolean(), nullable=False, server_default="1")
        )

    # 3. Opportunities
    with op.batch_alter_table("opportunities") as batch_op:
        batch_op.add_column(
            sa.Column("host_countries", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("host_regions", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column(
                "location_type",
                sa.String(length=50),
                nullable=False,
                server_default="in_person",
            )
        )
        batch_op.add_column(
            sa.Column("is_remote", sa.Boolean(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column(
                "restricted_applicant_countries",
                sa.JSON(),
                nullable=False,
                server_default="[]",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("opportunities") as batch_op:
        batch_op.drop_column("restricted_applicant_countries")
        batch_op.drop_column("is_remote")
        batch_op.drop_column("location_type")
        batch_op.drop_column("host_regions")
        batch_op.drop_column("host_countries")

    with op.batch_alter_table("user_preferences") as batch_op:
        batch_op.drop_column("open_to_remote")
        batch_op.drop_column("willing_to_travel")
        batch_op.drop_column("acceptable_countries")
        batch_op.drop_column("discovery_mode")

    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.drop_column("previous_education_country")
        batch_op.drop_column("citizenships")
