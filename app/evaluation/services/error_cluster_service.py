"""Service for deterministic error clustering and recurring defect detection."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluation.models.taxonomy import ErrorCluster, ErrorTaxonomyType

logger = logging.getLogger(__name__)


class ErrorClusterService:
    """Aggregates similar platform failures into deterministic clusters."""

    @staticmethod
    def generate_fingerprint(
        error_type: ErrorTaxonomyType,
        domain: str | None = None,
        affected_field: str | None = None,
    ) -> str:
        """Constructs a deterministic SHA256 signature for defect clustering."""
        key_raw = f"{error_type}:{domain or '*'}:{affected_field or '*'}"
        return hashlib.sha256(key_raw.encode("utf-8")).hexdigest()[:16]

    async def record_error(
        self,
        db: AsyncSession,
        error_type: ErrorTaxonomyType,
        domain: str | None = None,
        affected_field: str | None = None,
        feedback_id: UUID | None = None,
    ) -> ErrorCluster:
        """Finds or creates an error cluster, incrementing occurrence counter."""
        fingerprint = self.generate_fingerprint(error_type, domain, affected_field)

        query = select(ErrorCluster).where(ErrorCluster.fingerprint == fingerprint)
        result = await db.execute(query)
        cluster = result.scalar_one_or_none()

        now = datetime.now(UTC)
        fb_id_str = str(feedback_id) if feedback_id else None

        if cluster:
            cluster.occurrence_count += 1
            cluster.last_seen_at = now
            if fb_id_str and fb_id_str not in cluster.sample_feedback_ids:
                cluster.sample_feedback_ids = list(cluster.sample_feedback_ids) + [fb_id_str]
        else:
            cluster = ErrorCluster(
                error_type=error_type,
                fingerprint=fingerprint,
                domain=domain,
                affected_field=affected_field,
                occurrence_count=1,
                sample_feedback_ids=[fb_id_str] if fb_id_str else [],
                status="ACTIVE",
                last_seen_at=now,
            )
            db.add(cluster)

        await db.commit()
        await db.refresh(cluster)
        return cluster
