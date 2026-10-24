"""Lexical BM25-style keyword retriever for structured opportunities."""

from __future__ import annotations

import re

from app.discovery.interfaces import KeywordRetriever
from app.discovery.models import OpportunityCandidate, OpportunitySearchDocument, RetrievalFilters


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


class LexicalKeywordRetriever(KeywordRetriever):
    """Retrieves candidates using lexical matching over indexed documents or database records."""

    def __init__(self, documents: list[OpportunitySearchDocument] | None = None) -> None:
        self.documents: dict[str, OpportunitySearchDocument] = {}
        if documents:
            for d in documents:
                self.documents[d.opportunity_id] = d

    def index_document(self, doc: OpportunitySearchDocument) -> None:
        self.documents[doc.opportunity_id] = doc

    async def search(
        self,
        query: str,
        filters: RetrievalFilters | None = None,
        limit: int = 100,
    ) -> list[OpportunityCandidate]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        candidates: list[OpportunityCandidate] = []

        for doc_id, doc in self.documents.items():
            # Calculate token overlap score
            title_tokens = set(_tokenize(doc.title))
            desc_tokens = set(_tokenize(doc.description))
            field_tokens = set(_tokenize(" ".join(doc.fields)))
            provider_tokens = set(_tokenize(doc.provider))

            score = 0.0
            matched_tokens = 0

            for t in query_tokens:
                if t in title_tokens:
                    score += 4.0
                    matched_tokens += 1
                elif t in provider_tokens:
                    score += 3.0
                    matched_tokens += 1
                elif t in field_tokens:
                    score += 2.5
                    matched_tokens += 1
                elif t in desc_tokens:
                    score += 1.0
                    matched_tokens += 1

            if matched_tokens > 0:
                # Normalize score
                max_possible = len(query_tokens) * 4.0
                norm_score = min(1.0, score / max_possible if max_possible > 0 else 0.0)

                candidate = OpportunityCandidate(
                    opportunity_id=doc_id,
                    title=doc.title,
                    provider=doc.provider,
                    category=doc.category,
                    document=doc,
                    keyword_score=round(norm_score, 4),
                    retrieval_sources=["KEYWORD"],
                    canonical_source_url=doc.source_url,
                    cluster_source_urls=[doc.source_url] if doc.source_url else [],
                )
                candidates.append(candidate)

        # Sort descending by keyword score
        candidates.sort(key=lambda x: x.keyword_score, reverse=True)
        return candidates[:limit]
