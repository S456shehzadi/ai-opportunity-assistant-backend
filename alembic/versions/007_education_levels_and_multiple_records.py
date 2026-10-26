"""007 Education Levels and Multiple Records

Revision ID: 007_education_levels_and_multiple_records
Revises: 006_vector_embeddings_discovery_index
Create Date: 2026-10-26 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007_education_levels_and_multiple_records"
down_revision: str | None = "006_vector_embeddings_discovery_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Update user_profiles with current_education_level and education_status
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.add_column(
            sa.Column("current_education_level", sa.String(length=60), nullable=True)
        )
        batch_op.add_column(
            sa.Column("education_status", sa.String(length=50), nullable=True)
        )

    # 2. Update academic_records with new fields for global education tracking
    with op.batch_alter_table("academic_records") as batch_op:
        batch_op.add_column(
            sa.Column("education_level", sa.String(length=60), nullable=True)
        )
        batch_op.add_column(
            sa.Column("academic_stream", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("status", sa.String(length=50), nullable=True)
        )
        batch_op.add_column(
            sa.Column("grading_system", sa.String(length=50), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "is_highest", sa.Boolean(), nullable=False, server_default=sa.text("false")
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("academic_records") as batch_op:
        batch_op.drop_column("is_highest")
        batch_op.drop_column("grading_system")
        batch_op.drop_column("status")
        batch_op.drop_column("academic_stream")
        batch_op.drop_column("education_level")

    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.drop_column("education_status")
        batch_op.drop_column("current_education_level")
