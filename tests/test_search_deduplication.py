from app.search.deduplication.deduplicator import SearchResultDeduplicator
from app.search.models.search_result import NormalizedSearchResult


def _make_result(
    raw_url: str, domain: str, title: str = "Test", rank: int = 1
) -> NormalizedSearchResult:
    return NormalizedSearchResult(
        title=title,
        url=raw_url,
        original_url=raw_url,
        snippet="Snippet text",
        domain=domain,
        rank=rank,
        provider="mock",
        query="query",
    )


def test_deduplicator_removes_duplicate_canonical_urls() -> None:
    items = [
        _make_result(
            "https://www.daad.de/page?utm_source=twitter", "daad.de", title="Item 1", rank=1
        ),
        _make_result("https://www.daad.de/page#fragment", "daad.de", title="Item 2", rank=2),
        _make_result("https://www.daad.de/other-page", "daad.de", title="Item 3", rank=3),
    ]

    deduped = SearchResultDeduplicator.deduplicate(items)
    # Item 1 and Item 2 point to the same canonical URL -> only 1 retained
    assert len(deduped) == 2
    assert deduped[0].title == "Item 1"
    assert deduped[1].title == "Item 3"


def test_deduplicator_domain_diversification() -> None:
    # 5 items from the same domain
    items = [_make_result(f"https://www.daad.de/page{i}", "daad.de", rank=i) for i in range(1, 6)]
    # 2 items from another domain
    items.extend(
        [_make_result(f"https://www.tum.de/page{i}", "tum.de", rank=i) for i in range(1, 3)]
    )

    # max_per_domain = 2
    deduped = SearchResultDeduplicator.deduplicate(items, max_per_domain=2, max_total=4)
    domain_counts = {}
    for d in deduped:
        domain_counts[d.domain] = domain_counts.get(d.domain, 0) + 1

    assert len(deduped) == 4
    assert domain_counts["daad.de"] <= 2
    assert domain_counts["tum.de"] <= 2
