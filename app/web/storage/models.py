"""Storage models for web crawling history, versioning, and document content."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class WebPage(Base, UUIDMixin, TimestampMixin):
    """Represents a unique crawled web page resource."""

    __tablename__ = "web_pages"

    url: Mapped[str] = mapped_column(String(2048), unique=True, index=True, nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    domain: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    versions: Mapped[list["WebPageVersion"]] = relationship(
        "WebPageVersion", back_populates="page", cascade="all, delete-orphan"
    )


class WebPageVersion(Base, UUIDMixin):
    """Tracks historical retrieval snapshots and status for a web page."""

    __tablename__ = "web_page_versions"

    page_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("web_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    simhash: Mapped[str] = mapped_column(String(16), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="success", nullable=False)
    page_type: Mapped[str] = mapped_column(String(50), default="UNKNOWN", nullable=False)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)

    page: Mapped["WebPage"] = relationship("WebPage", back_populates="versions")
    content: Mapped["WebPageContent"] = relationship(
        "WebPageContent", back_populates="version", uselist=False, cascade="all, delete-orphan"
    )


class WebPageContent(Base, UUIDMixin):
    """Structured and cleaned content body for a specific webpage version snapshot."""

    __tablename__ = "web_page_contents"

    version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("web_page_versions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    clean_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    headings_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    tables_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    links_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    dates_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    version: Mapped["WebPageVersion"] = relationship("WebPageVersion", back_populates="content")
