"""Structured metadata filter enforcing non-negotiable criteria without bypassing eligibility."""

from __future__ import annotations

from datetime import date

from app.discovery.interfaces import MetadataFilterService
from app.discovery.models import OpportunityCandidate, RetrievalFilters


class StructuredMetadataFilter(MetadataFilterService):
    """Enforces non-negotiable hard criteria to eliminate candidates before ranking."""

    def apply_hard_filters(
        self,
        candidates: list[OpportunityCandidate],
        filters: RetrievalFilters,
    ) -> list[OpportunityCandidate]:
        passed: list[OpportunityCandidate] = []
        today = filters.current_date or date.today()

        for c in candidates:
            doc = c.document
            rejection_reason: str | None = None

            # 1. Exclude expired opportunities
            if filters.exclude_expired and doc.deadline and doc.deadline < today:
                rejection_reason = f"Deadline passed on {doc.deadline.isoformat()}"

            # 2. Opportunity status filter
            elif filters.status and doc.status.lower() != filters.status.lower():
                rejection_reason = (
                    f"Status '{doc.status}' does not match required '{filters.status}'"
                )

            # 3. Opportunity category filter
            elif filters.category and doc.category.lower() != filters.category.lower():
                rejection_reason = f"Category '{doc.category}' does not match '{filters.category}'"

            # 4. Degree levels matching
            elif filters.degree_levels and doc.degree_levels:
                # Normalization check
                req_degrees = {d.lower().rstrip("s").rstrip("'") for d in filters.degree_levels}
                doc_degrees = {d.lower().rstrip("s").rstrip("'") for d in doc.degree_levels}
                if not req_degrees.intersection(doc_degrees):
                    rejection_reason = (
                        f"Degree levels {doc.degree_levels} do not match {filters.degree_levels}"
                    )

            # 5. Fully funded filter
            elif filters.fully_funded_only:
                f_summary = (doc.funding_summary or "").lower()
                if (
                    "full" not in f_summary
                    and "100%" not in f_summary
                    and "tuition-free" not in f_summary
                ):
                    rejection_reason = "Opportunity is not verified as fully funded"

            # 6. No application fee filter
            elif filters.no_application_fee and doc.application_fee_required:
                rejection_reason = "Opportunity requires an application fee"

            # 7. No IELTS required filter
            elif filters.no_ielts_required:
                tests = [t.lower() for t in doc.tests_required]
                if any("ielts" in t for t in tests):
                    rejection_reason = "Opportunity explicitly requires IELTS test score"

            # 8. Country location filter
            elif filters.countries and doc.countries:
                req_countries = {c.lower() for c in filters.countries}
                doc_countries = {c.lower() for c in doc.countries}
                if "global" not in doc_countries and not req_countries.intersection(doc_countries):
                    rejection_reason = (
                        f"Location {doc.countries} outside requested {filters.countries}"
                    )

            # 9. Eligible nationalities filter
            elif filters.eligible_nationalities and doc.nationalities:
                req_nats = {n.lower() for n in filters.eligible_nationalities}
                doc_nats = {n.lower() for n in doc.nationalities}
                if "global" not in doc_nats and not req_nats.intersection(doc_nats):
                    rejection_reason = (
                        f"Nationalities {doc.nationalities} do not match "
                        f"{filters.eligible_nationalities}"
                    )

            if rejection_reason is None:
                c.hard_filter_passed = True
                c.filter_rejection_reason = None
                passed.append(c)
            else:
                c.hard_filter_passed = False
                c.filter_rejection_reason = rejection_reason

        return passed
