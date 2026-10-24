"""initial data foundation

Revision ID: 001_initial_foundation
Revises:
Create Date: 2026-09-23 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. user_profiles
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nationality", sa.String(length=100), nullable=True),
        sa.Column("country_of_residence", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("education_level", sa.String(length=50), nullable=True),
        sa.Column("degree_title", sa.String(length=200), nullable=True),
        sa.Column("field_of_study", sa.String(length=200), nullable=True),
        sa.Column("university", sa.String(length=255), nullable=True),
        sa.Column("graduation_year", sa.Integer(), nullable=True),
        sa.Column("cgpa", sa.Float(), nullable=True),
        sa.Column("percentage", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_profiles_id", "user_profiles", ["id"])
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"], unique=True)

    # 3. academic_records
    op.create_table(
        "academic_records",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("institution", sa.String(length=255), nullable=False),
        sa.Column("degree", sa.String(length=200), nullable=False),
        sa.Column("field_of_study", sa.String(length=200), nullable=False),
        sa.Column("start_year", sa.Integer(), nullable=True),
        sa.Column("end_year", sa.Integer(), nullable=True),
        sa.Column("grade", sa.String(length=50), nullable=True),
        sa.Column("grading_scale", sa.String(length=50), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_academic_records_id", "academic_records", ["id"])
    op.create_index("ix_academic_records_user_id", "academic_records", ["user_id"])

    # 4. test_results
    op.create_table(
        "test_results",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("test_name", sa.String(length=100), nullable=False),
        sa.Column("test_type", sa.String(length=50), nullable=False),
        sa.Column("score", sa.String(length=50), nullable=False),
        sa.Column("score_details", sa.JSON(), nullable=False),
        sa.Column("test_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_test_results_id", "test_results", ["id"])
    op.create_index("ix_test_results_user_id", "test_results", ["user_id"])

    # 5. user_skills
    op.create_table(
        "user_skills",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("proficiency", sa.String(length=50), nullable=False),
        sa.Column("years_of_experience", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_skills_id", "user_skills", ["id"])
    op.create_index("ix_user_skills_user_id", "user_skills", ["user_id"])

    # 6. work_experiences
    op.create_table(
        "work_experiences",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("organization", sa.String(length=255), nullable=False),
        sa.Column("job_title", sa.String(length=200), nullable=False),
        sa.Column("employment_type", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_work_experiences_id", "work_experiences", ["id"])
    op.create_index("ix_work_experiences_user_id", "work_experiences", ["user_id"])

    # 7. research_experiences
    op.create_table(
        "research_experiences",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("research_area", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("institution", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=150), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_research_experiences_id", "research_experiences", ["id"])
    op.create_index("ix_research_experiences_user_id", "research_experiences", ["user_id"])

    # 8. publications
    op.create_table(
        "publications",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("publication_type", sa.String(length=100), nullable=True),
        sa.Column("venue", sa.String(length=255), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("doi", sa.String(length=150), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("authors", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_publications_id", "publications", ["id"])
    op.create_index("ix_publications_user_id", "publications", ["user_id"])

    # 9. projects
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("technologies", sa.JSON(), nullable=False),
        sa.Column("project_url", sa.String(length=500), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_projects_id", "projects", ["id"])
    op.create_index("ix_projects_user_id", "projects", ["user_id"])

    # 10. user_languages
    op.create_table(
        "user_languages",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("language_name", sa.String(length=100), nullable=False),
        sa.Column("proficiency", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_languages_id", "user_languages", ["id"])
    op.create_index("ix_user_languages_user_id", "user_languages", ["user_id"])

    # 11. user_preferences
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("preferred_countries", sa.JSON(), nullable=False),
        sa.Column("preferred_regions", sa.JSON(), nullable=False),
        sa.Column("preferred_opportunity_categories", sa.JSON(), nullable=False),
        sa.Column("preferred_fields", sa.JSON(), nullable=False),
        sa.Column("funding_preference", sa.String(length=100), nullable=True),
        sa.Column("remote_preference", sa.String(length=100), nullable=True),
        sa.Column("study_mode", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_preferences_id", "user_preferences", ["id"])
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"], unique=True)

    # 12. opportunities
    op.create_table(
        "opportunities",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("organization", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False, server_default="Global"),
        sa.Column("eligible_countries", sa.JSON(), nullable=False),
        sa.Column("eligible_nationalities", sa.JSON(), nullable=False),
        sa.Column("degree_levels", sa.JSON(), nullable=False),
        sa.Column("fields", sa.JSON(), nullable=False),
        sa.Column("funding_type", sa.String(length=100), nullable=False, server_default="Unknown"),
        sa.Column("funding_amount", sa.String(length=100), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("opening_date", sa.Date(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("application_url", sa.String(length=1000), nullable=True),
        sa.Column("official_source_url", sa.String(length=1000), nullable=False),
        sa.Column("source_domain", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_opportunities_id", "opportunities", ["id"])
    op.create_index("ix_opportunities_category", "opportunities", ["category"])
    op.create_index("ix_opportunities_deadline", "opportunities", ["deadline"])
    op.create_index("ix_opportunities_source_domain", "opportunities", ["source_domain"])
    op.create_index("ix_opportunities_status", "opportunities", ["status"])

    # 13. opportunity_sources
    op.create_table(
        "opportunity_sources",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "opportunity_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("is_official", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "verification_status", sa.String(length=50), nullable=False, server_default="unverified"
        ),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_opportunity_sources_id", "opportunity_sources", ["id"])
    op.create_index(
        "ix_opportunity_sources_opportunity_id", "opportunity_sources", ["opportunity_id"]
    )
    op.create_index("ix_opportunity_sources_domain", "opportunity_sources", ["domain"])

    # 14. opportunity_requirements
    op.create_table(
        "opportunity_requirements",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "opportunity_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requirement_type", sa.String(length=100), nullable=False),
        sa.Column("operator", sa.String(length=20), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_opportunity_requirements_id", "opportunity_requirements", ["id"])
    op.create_index(
        "ix_opportunity_requirements_opportunity_id", "opportunity_requirements", ["opportunity_id"]
    )
    op.create_index(
        "ix_opportunity_requirements_requirement_type",
        "opportunity_requirements",
        ["requirement_type"],
    )

    # 15. search_sessions
    op.create_table(
        "search_sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("query", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_search_sessions_id", "search_sessions", ["id"])
    op.create_index("ix_search_sessions_user_id", "search_sessions", ["user_id"])

    # 16. ai_interactions
    op.create_table(
        "ai_interactions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "session_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("search_sessions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("input_prompt", sa.Text(), nullable=False),
        sa.Column("output_response", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_interactions_id", "ai_interactions", ["id"])
    op.create_index("ix_ai_interactions_user_id", "ai_interactions", ["user_id"])
    op.create_index("ix_ai_interactions_session_id", "ai_interactions", ["session_id"])


def downgrade() -> None:
    op.drop_table("ai_interactions")
    op.drop_table("search_sessions")
    op.drop_table("opportunity_requirements")
    op.drop_table("opportunity_sources")
    op.drop_table("opportunities")
    op.drop_table("user_preferences")
    op.drop_table("user_languages")
    op.drop_table("projects")
    op.drop_table("publications")
    op.drop_table("research_experiences")
    op.drop_table("work_experiences")
    op.drop_table("user_skills")
    op.drop_table("test_results")
    op.drop_table("academic_records")
    op.drop_table("user_profiles")
    op.drop_table("users")
