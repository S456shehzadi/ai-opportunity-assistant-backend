import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class SearchSession(Base, UUIDMixin, TimestampMixin):
    """Records user search queries and session progress for future personalization."""

    __tablename__ = "search_sessions"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    query: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    user: Mapped["User | None"] = relationship("User", back_populates="search_sessions")
    ai_interactions: Mapped[list["AIInteraction"]] = relationship(
        "AIInteraction",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class AIInteraction(Base, UUIDMixin, TimestampMixin):
    """Tracks inputs, grounded outputs, and model references for user queries."""

    __tablename__ = "ai_interactions"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("search_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    input_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    output_response: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    user: Mapped["User | None"] = relationship("User", back_populates="ai_interactions")
    session: Mapped["SearchSession | None"] = relationship(
        "SearchSession", back_populates="ai_interactions"
    )
