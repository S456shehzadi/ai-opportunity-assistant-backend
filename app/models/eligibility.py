"""SQLAlchemy models for persisting eligibility evaluations and audit logs."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity
    from app.models.user import User


class EligibilityEvaluation(Base, UUIDMixin, TimestampMixin):
    """Stores persistent eligibility evaluation conclusions and versioned snapshots."""

    __tablename__ = "eligibility_evaluations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    overall_status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    match_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    engine_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    profile_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    opportunity_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    cache_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Full evaluation snapshot and personalized intelligence
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship("User")
    opportunity: Mapped["Opportunity"] = relationship("Opportunity")
