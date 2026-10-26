"""009 Experience System and Career Summary

Revision ID: 009_experience_system_and_career_summary
Revises: 008_fields_skills_certifications_projects
Create Date: 2026-10-26 21:55:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009_experience_system_and_career_summary"
down_revision: str | None = "008_fields_skills_certifications_projects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Update user_profiles with headline and summary
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.add_column(sa.Column("headline", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("summary", sa.Text(), nullable=True))

    # 2. Update work_experiences with category, industry, department, city, work_arrangement, achievements, metadata_json
    with op.batch_alter_table("work_experiences") as batch_op:
        batch_op.add_column(
            sa.Column("category", sa.String(length=50), nullable=False, server_default="Employment")
        )
        batch_op.add_column(sa.Column("industry", sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column("department", sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column("city", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("work_arrangement", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("achievements", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("metadata_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("work_experiences") as batch_op:
        batch_op.drop_column("metadata_json")
        batch_op.drop_column("achievements")
        batch_op.drop_column("work_arrangement")
        batch_op.drop_column("city")
        batch_op.drop_column("department")
        batch_op.drop_column("industry")
        batch_op.drop_column("category")

    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.drop_column("summary")
        batch_op.drop_column("headline")
