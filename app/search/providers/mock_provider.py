import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import SearchProviderException
from app.search.interfaces.search_provider import SearchProvider
from app.search.models.search_models import SearchQuery, SearchResultItem, SearchResults
from app.search.models.search_result import NormalizedSearchResult
from app.search.normalization.url_normalizer import UrlNormalizer


class MockSearchProvider(SearchProvider):
    """Deterministic offline search provider returning realistic opportunity results.

    Used for tests, local development, and fallback when no API key is configured.
    """

    def __init__(self, provider_name: str = "mock") -> None:
        super().__init__(provider_name)
        self.simulate_timeout: bool = False
        self.simulate_rate_limit: bool = False
        self.simulate_failure: bool = False
        self.simulate_empty: bool = False

    async def search_items(
        self,
        query: str,
        max_results: int = 10,
        query_purpose: str = "general_search",
        **kwargs: Any,
    ) -> list[NormalizedSearchResult]:
        if self.simulate_timeout or kwargs.get("simulate_timeout"):
            await asyncio.sleep(2.0)
            raise TimeoutError("Mock provider simulated timeout")

        if self.simulate_rate_limit or kwargs.get("simulate_rate_limit"):
            raise SearchProviderException(
                message="Rate limit exceeded: HTTP 429 Too Many Requests",
                provider="mock",
            )

        if self.simulate_failure or kwargs.get("simulate_failure"):
            raise SearchProviderException(
                message="Internal provider error: HTTP 500",
                provider="mock",
            )

        if self.simulate_empty or kwargs.get("simulate_empty"):
            return []

        lowered = query.lower()
        results: list[NormalizedSearchResult] = []

        # Candidate result database for realistic simulation
        if "germany" in lowered or "daad" in lowered:
            results.extend(
                [
                    self._create_item(
                        title="DAAD Scholarship Database - Funding for Students and Academics",
                        raw_url=(
                            "https://www.daad.de/en/study-and-research-in-germany/"
                            "scholarships/?utm_source=google"
                        ),
                        snippet=(
                            "Find funding options for your study or research visit to Germany "
                            "in our extensive scholarship database for international students."
                        ),
                        query=query,
                        purpose=query_purpose,
                        rank=1,
                        is_official=True,
                    ),
                    self._create_item(
                        title="Technical University of Munich: International Master's Scholarships",
                        raw_url=(
                            "https://www.tum.de/en/studies/fees-and-financial-aid/"
                            "scholarships#masters"
                        ),
                        snippet=(
                            "TUM offers several scholarships for international students pursuing "
                            "master's degree programs in engineering and informatics."
                        ),
                        query=query,
                        purpose=query_purpose,
                        rank=2,
                        is_official=True,
                    ),
                    self._create_item(
                        title="Heidelberg University: Graduate Scholarships in Germany",
                        raw_url=(
                            "https://www.uni-heidelberg.de/en/study/management-studies/"
                            "finance-scholarships"
                        ),
                        snippet=(
                            "Financial assistance and full tuition coverage programs available "
                            "for international master's and doctoral students in Heidelberg."
                        ),
                        query=query,
                        purpose=query_purpose,
                        rank=3,
                        is_official=True,
                    ),
                ]
            )

        if "europe" in lowered or "erasmus" in lowered:
            results.extend(
                [
                    self._create_item(
                        title="Erasmus Mundus Joint Master Degrees - Official European Portal",
                        raw_url=(
                            "https://erasmus-plus.ec.europa.eu/opportunities/"
                            "opportunities-for-individuals/students/erasmus-mundus-joint-masters"
                            "?ref=portal"
                        ),
                        snippet=(
                            "Erasmus Mundus Joint Masters are prestigious international "
                            "programmes, delivered by an international consortium of institutions."
                        ),
                        query=query,
                        purpose=query_purpose,
                        rank=len(results) + 1,
                        is_official=True,
                    ),
                    self._create_item(
                        title="Study in Europe - European Higher Education Scholarships Directory",
                        raw_url="https://www.studyineurope.eu/scholarships?source=search",
                        snippet=(
                            "Guide to full government scholarships, grants, and living allowance "
                            "opportunities for studying in European universities."
                        ),
                        query=query,
                        purpose=query_purpose,
                        rank=len(results) + 2,
                        is_official=False,
                    ),
                ]
            )

        if "internship" in lowered:
            results.extend(
                [
                    self._create_item(
                        title="Max Planck Institute for Informatics: Research Internships in AI",
                        raw_url=(
                            "https://www.mpi-inf.mpg.de/departments/computer-vision/internships"
                        ),
                        snippet=(
                            "Paid research internships for undergraduate and graduate students "
                            "in computer vision, machine learning, and artificial intelligence."
                        ),
                        query=query,
                        purpose=query_purpose,
                        rank=len(results) + 1,
                        is_official=True,
                    ),
                    self._create_item(
                        title="CERN Summer Student Programme - Openlab Internships",
                        raw_url="https://openlab.cern/summer-student-programme",
                        snippet=(
                            "9-week computing internship in Geneva, Switzerland with full "
                            "monthly subsistence allowance and travel covered."
                        ),
                        query=query,
                        purpose=query_purpose,
                        rank=len(results) + 2,
                        is_official=True,
                    ),
                ]
            )

        if "fellowship" in lowered or "research" in lowered:
            results.extend(
                [
                    self._create_item(
                        title="Marie Skłodowska-Curie Actions (MSCA) Postdoctoral Fellowships",
                        raw_url=(
                            "https://marie-sklodowska-curie-actions.ec.europa.eu/actions/"
                            "postdoctoral-fellowships"
                        ),
                        snippet=(
                            "MSCA Postdoctoral Fellowships enhance creative and innovative "
                            "potential of researchers holding a PhD wishing to acquire new skills."
                        ),
                        query=query,
                        purpose=query_purpose,
                        rank=len(results) + 1,
                        is_official=True,
                    ),
                    self._create_item(
                        title="Alexander von Humboldt Foundation Research Fellowships",
                        raw_url=(
                            "https://www.humboldt-foundation.de/en/apply/"
                            "sponsorship-programmes/humboldt-research-fellowship"
                        ),
                        snippet=(
                            "Postdoctoral and experienced researchers from all nations can conduct "
                            "research in Germany with full monthly stipend and travel grant."
                        ),
                        query=query,
                        purpose=query_purpose,
                        rank=len(results) + 2,
                        is_official=True,
                    ),
                ]
            )

        if "startup" in lowered or "grant" in lowered or "funding" in lowered:
            results.extend(
                [
                    self._create_item(
                        title="European Innovation Council (EIC) Women Leadership Grants",
                        raw_url=(
                            "https://eic.ec.europa.eu/eic-funding-opportunities/"
                            "women-leadership-programme_en"
                        ),
                        snippet=(
                            "Dedicated non-dilutive grant funding, mentoring, and venture "
                            "support for female tech founders in Europe."
                        ),
                        query=query,
                        purpose=query_purpose,
                        rank=len(results) + 1,
                        is_official=True,
                    ),
                    self._create_item(
                        title="Global Innovation Fund: Seed Grants and Direct Investment",
                        raw_url="https://www.globalinnovation.fund/apply-for-funding",
                        snippet=(
                            "Grants and risk capital for social enterprises, innovators, "
                            "and women-led initiatives in emerging markets."
                        ),
                        query=query,
                        purpose=query_purpose,
                        rank=len(results) + 2,
                        is_official=True,
                    ),
                ]
            )

        # Generic fallback results if query doesn't match above patterns
        if not results:
            results.extend(
                [
                    self._create_item(
                        title=f"International Opportunity Portal: {query.title()}",
                        raw_url=(
                            "https://www.scholars4dev.com/category/target-group/"
                            "international-students/"
                        ),
                        snippet=(
                            f"Comprehensive listing of international scholarships, "
                            f"fellowships, and grants matching: {query}."
                        ),
                        query=query,
                        purpose=query_purpose,
                        rank=1,
                        is_official=False,
                    ),
                    self._create_item(
                        title="Global Scholarships Directory - Fully Funded Programs",
                        raw_url="https://globalscholarships.com/search-programs/?ref=web",
                        snippet=(
                            "Database of university scholarships, financial aid, and "
                            "fellowships with verified eligibility requirements."
                        ),
                        query=query,
                        purpose=query_purpose,
                        rank=2,
                        is_official=False,
                    ),
                ]
            )

        return results[:max_results]

    async def search(self, query: SearchQuery) -> SearchResults:
        """Backward-compatible search returning SearchResults."""
        items = await self.search_items(query.query_text, max_results=query.limit)
        return SearchResults(
            query=query,
            provider=self.provider_name,
            items=[
                SearchResultItem(
                    title=item.title,
                    url=item.url,
                    snippet=item.snippet,
                    domain=item.domain,
                    rank=item.rank,
                    published_date=item.published_at,
                    metadata=item.raw_metadata,
                )
                for item in items
            ],
            retrieved_at=datetime.now(UTC),
            total_results=len(items),
        )

    def _create_item(
        self,
        title: str,
        raw_url: str,
        snippet: str,
        query: str,
        purpose: str,
        rank: int,
        is_official: bool,
    ) -> NormalizedSearchResult:
        canonical_url = UrlNormalizer.normalize_url(raw_url)
        domain = UrlNormalizer.extract_domain(canonical_url)
        return NormalizedSearchResult(
            id=uuid.uuid4(),
            title=title,
            url=canonical_url,
            original_url=raw_url,
            snippet=snippet,
            domain=domain,
            rank=rank,
            provider=self.provider_name,
            query=query,
            query_purpose=purpose,
            published_at="2026-01-15",
            retrieved_at=datetime.now(UTC),
            is_official_source_candidate=is_official,
            relevance_score=0.90 if is_official else 0.75,
        )
