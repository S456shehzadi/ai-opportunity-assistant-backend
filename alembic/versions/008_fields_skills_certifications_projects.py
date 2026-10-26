"""008 Fields Skills Certifications Projects

Revision ID: 008_fields_skills_certifications_projects
Revises: 007_education_levels_and_multiple_records
Create Date: 2026-10-26 18:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "008_fields_skills_certifications_projects"
down_revision: str | None = "007_education_levels_and_multiple_records"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Update user_profiles
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.add_column(sa.Column("primary_field", sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column("secondary_fields", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("specializations", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("career_goals", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("learning_goals", sa.JSON(), nullable=True))

    # 2. Update skills
    with op.batch_alter_table("skills") as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(length=30), nullable=False, server_default="have")
        )
        batch_op.add_column(sa.Column("acquisition_source", sa.String(length=100), nullable=True))

    # 3. Update work_experiences
    with op.batch_alter_table("work_experiences") as batch_op:
        batch_op.add_column(sa.Column("skills_used", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("portfolio_url", sa.String(length=255), nullable=True))

    # 4. Update projects
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column("project_type", sa.String(length=50), nullable=False, server_default="Personal")
        )
        batch_op.add_column(sa.Column("role", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("skills", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("outcome", sa.Text(), nullable=True))

    # 5. Create certifications table
    op.create_table(
        "certifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("issuing_organization", sa.String(length=150), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="Completed"),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("credential_id", sa.String(length=100), nullable=True),
        sa.Column("verification_url", sa.String(length=255), nullable=True),
        sa.Column("skills", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_certifications_user_id", "certifications", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_certifications_user_id", table_name="certifications")
    op.drop_table("certifications")

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("outcome")
        batch_op.drop_column("skills")
        batch_op.drop_column("role")
        batch_op.drop_column("project_type")

    with op.batch_alter_table("work_experiences") as batch_op:
        batch_op.drop_column("portfolio_url")
        batch_op.drop_column("skills_used")

    with op.batch_alter_table("skills") as batch_op:
        batch_op.drop_column("acquisition_source")
        batch_op.drop_column("status")

    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.drop_column("learning_goals")
        batch_op.drop_column("career_goals")
        batch_op.drop_column("specializations")
        batch_op.drop_column("secondary_fields")
        batch_op.drop_column("primary_field")
