"""Prompt versioning and template metadata model."""

from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class PromptVersionRecord(Base, UUIDMixin, TimestampMixin):
    """Auditable prompt record ensuring benchmark runs reference explicit templates."""

    __tablename__ = "prompt_versions"

    prompt_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    task: Mapped[str] = mapped_column(String(100), nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
