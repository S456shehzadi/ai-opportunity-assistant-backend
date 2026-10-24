"""End-to-end orchestration service for web retrieval and content extraction."""

import asyncio
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.search.models.search_result import NormalizedSearchResult
from app.web.analysis.duplicate_detector import DuplicateDetector
from app.web.analysis.language_detector import LanguageDetector
from app.web.analysis.page_classifier import PageTypeClassifier
from app.web.analysis.quality_analyzer import ContentQualityAnalyzer
from app.web.cache import WebDocumentCache
from app.web.extraction.date_extractor import DateExtractor
from app.web.extraction.html_parser import parse_html_tree
from app.web.extraction.link_extractor import LinkExtractor
from app.web.extraction.main_content import MainContentExtractor
from app.web.extraction.metadata_extractor import MetadataExtractor
from app.web.extraction.table_extractor import TableExtractor
from app.web.models.document import WebDocument
from app.web.policies.rate_limiter import DomainRateLimiter
from app.web.policies.robots_service import RobotsPolicyService
from app.web.retrieval.batch_retriever import BatchWebRetriever
from app.web.retrieval.rendered_retriever import detect_js_dependency
from app.web.retrieval.web_retriever import HttpWebRetriever, WebRetriever
from app.web.security.url_validator import URLValidator
from app.web.storage.models import WebPage, WebPageContent, WebPageVersion

logger = logging.getLogger(__name__)


class WebRetrievalService:
    """Coordinates URL validation, retrieval, HTML processing, and structured content extraction."""

    def __init__(
        self,
        retriever: WebRetriever | None = None,
        cache: WebDocumentCache | None = None,
        robots_service: RobotsPolicyService | None = None,
        rate_limiter: DomainRateLimiter | None = None,
    ) -> None:
        self.settings = get_settings()
        self.robots_service = robots_service or RobotsPolicyService()
        self.rate_limiter = rate_limiter or DomainRateLimiter()
        self.retriever = retriever or HttpWebRetriever(
            robots_service=self.robots_service,
            rate_limiter=self.rate_limiter,
        )
        self.cache = cache or WebDocumentCache()
        self.batch_retriever = BatchWebRetriever(
            retriever=self.retriever,
            max_concurrency=self.settings.WEB_MAX_CONCURRENT_RETRIEVALS,
        )

    async def retrieve_document(
        self,
        url: str,
        force_refresh: bool = False,
        db_session: AsyncSession | None = None,
    ) -> WebDocument:
        """Processes a single URL through validation, retrieval, parsing, and extraction.

        Args:
            url: Target URL to retrieve.
            force_refresh: If True, bypasses cache and forces network retrieval.
            db_session: Optional database session for storing crawl snapshots.

        Returns:
            WebDocument: High-fidelity structured representation of the target webpage.
        """
        # 1. URL Validation
        normalized_url, hostname = URLValidator.validate_and_normalize(url)

        # 2. Cache Check
        if not force_refresh:
            cached = await self.cache.get(normalized_url)
            if cached is not None:
                logger.debug("Cache hit for URL: %s", normalized_url)
                return cached

        # 3. Web Retrieval (Includes SSRF, Robots, Rate Limiting, Retries, Size Limits)
        raw_doc = await self.retriever.fetch(normalized_url)

        # 4. HTML Tree Parsing
        tree = parse_html_tree(raw_doc.raw_html)

        # 5. Tabular Data Extraction
        tables = TableExtractor.extract_tables(tree)

        # 6. Main Content Extraction & Heading Preservation
        clean_text, headings, word_count = MainContentExtractor.extract_clean_content(
            root=tree,
            extracted_tables=tables,
        )

        # 7. Contextual Link Extraction
        links = LinkExtractor.extract_links(tree, base_url=raw_doc.final_url)

        # 8. Metadata and OG Extraction
        meta_title, metadata, canonical_url, meta_lang = MetadataExtractor.extract_metadata(tree)
        page_title = meta_title or raw_doc.final_url

        # 9. Date Extraction Foundation
        extracted_dates = DateExtractor.extract_dates(clean_text)

        # 10. Quality Assessment
        quality_score = ContentQualityAnalyzer.analyze(
            clean_text=clean_text,
            raw_html=raw_doc.raw_html,
            headings=headings,
            word_count=word_count,
        )

        # 11. Page Type Classification
        page_type = PageTypeClassifier.classify(
            title=page_title,
            clean_text=clean_text,
            url=raw_doc.final_url,
        )

        # 12. Language Detection
        detected_language = LanguageDetector.detect(clean_text=clean_text, html_lang=meta_lang)

        # 13. Exact & Near Duplicate Fingerprints
        content_hash = DuplicateDetector.compute_content_hash(clean_text)
        simhash = DuplicateDetector.compute_simhash(clean_text)

        # 14. Client-side JS Dependency Check
        is_js_dependent = detect_js_dependency(
            raw_html=raw_doc.raw_html,
            clean_text=clean_text,
            word_count=word_count,
        )

        warnings: list[str] = []
        if is_js_dependent:
            warnings.append(
                "Page indicates heavy client-side JavaScript rendering; content may be incomplete."
            )
        if word_count < 30:
            warnings.append("Low text content extracted from page.")

        # 15. Build WebDocument
        web_doc = WebDocument(
            original_url=raw_doc.original_url,
            final_url=raw_doc.final_url,
            domain=raw_doc.domain,
            status_code=raw_doc.status_code,
            content_type=raw_doc.content_type,
            retrieved_at=raw_doc.retrieved_at,
            title=page_title,
            clean_text=clean_text,
            language=detected_language,
            word_count=word_count,
            headings=headings,
            tables=tables,
            links=links,
            metadata=metadata,
            extracted_dates=extracted_dates,
            content_quality=quality_score,
            page_type=page_type,
            content_hash=content_hash,
            simhash=simhash,
            is_js_dependent=is_js_dependent,
            redirect_chain=raw_doc.redirect_chain,
            warnings=warnings,
        )

        # 16. Cache Document
        await self.cache.set(normalized_url, web_doc)
        if canonical_url and canonical_url != normalized_url:
            await self.cache.set(canonical_url, web_doc)

        # 17. Optional Database Snapshot Persistence
        if db_session:
            await self._persist_snapshot_safely(db_session, web_doc, raw_doc.raw_html)

        return web_doc

    retrieve_and_process = retrieve_document

    async def retrieve_batch(
        self,
        urls: list[str],
        force_refresh: bool = False,
        db_session: AsyncSession | None = None,
    ) -> list[WebDocument | dict[str, Any]]:
        """Retrieves and processes multiple URLs in parallel with controlled concurrency."""
        tasks = [
            self._retrieve_safe_single(url, force_refresh=force_refresh, db_session=db_session)
            for url in urls
        ]
        return await asyncio.gather(*tasks)

    async def retrieve_search_results(
        self,
        results: list[NormalizedSearchResult],
        db_session: AsyncSession | None = None,
    ) -> list[WebDocument]:
        """Bridges search results into retrieved and cleaned WebDocuments."""
        urls = [r.canonical_url or r.url for r in results]
        raw_results = await self.retrieve_batch(urls, db_session=db_session)

        successful_docs: list[WebDocument] = []
        for item in raw_results:
            if isinstance(item, WebDocument):
                successful_docs.append(item)
            elif isinstance(item, dict):
                logger.warning(
                    "Search result retrieval failed for '%s': %s",
                    item.get("url"),
                    item.get("error"),
                )

        return successful_docs

    async def _retrieve_safe_single(
        self,
        url: str,
        force_refresh: bool = False,
        db_session: AsyncSession | None = None,
    ) -> WebDocument | dict[str, Any]:
        """Safely processes a single URL, catching errors and returning error info."""
        try:
            return await self.retrieve_document(
                url, force_refresh=force_refresh, db_session=db_session
            )
        except Exception as exc:
            logger.warning("Batch item retrieval error for '%s': %s", url, exc)
            return {
                "url": url,
                "error": type(exc).__name__,
                "message": str(exc),
            }

    async def _persist_snapshot_safely(
        self,
        db: AsyncSession,
        doc: WebDocument,
        raw_html: str | None = None,
    ) -> None:
        """Persists webpage snapshot with safe rollback handling if DB is offline or throws."""
        try:
            # Query existing page
            stmt = select(WebPage).where(WebPage.url == doc.final_url)
            result = await db.execute(stmt)
            page = result.scalar_one_or_none()

            if page is None:
                page = WebPage(
                    url=doc.final_url,
                    canonical_url=doc.metadata.get("canonical_url"),
                    domain=doc.domain,
                )
                db.add(page)
                await db.flush()

            # Determine next version number
            stmt_v = (
                select(WebPageVersion)
                .where(WebPageVersion.page_id == page.id)
                .order_by(WebPageVersion.version_number.desc())
            )
            res_v = await db.execute(stmt_v)
            latest_v = res_v.scalars().first()
            next_ver_num = (latest_v.version_number + 1) if latest_v else 1

            version = WebPageVersion(
                page_id=page.id,
                version_number=next_ver_num,
                retrieved_at=doc.retrieved_at,
                content_hash=doc.content_hash,
                simhash=doc.simhash,
                status_code=doc.status_code,
                status="js_dependent" if doc.is_js_dependent else "success",
                page_type=doc.page_type.value,
                language=doc.language,
            )
            db.add(version)
            await db.flush()

            content = WebPageContent(
                version_id=version.id,
                title=doc.title,
                clean_text=doc.clean_text,
                word_count=doc.word_count,
                metadata_json=doc.metadata,
                headings_json=[h.model_dump() for h in doc.headings],
                tables_json=[t.model_dump() for t in doc.tables],
                links_json=[link.model_dump() for link in doc.links],
                dates_json=[d.model_dump() for d in doc.extracted_dates],
                raw_html=raw_html,
            )
            db.add(content)
            await db.commit()
        except Exception as exc:
            logger.warning("Could not persist WebPage version to DB: %s", exc)
            try:
                await db.rollback()
            except Exception:
                pass
