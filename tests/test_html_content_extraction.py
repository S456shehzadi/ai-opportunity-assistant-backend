"""Tests for HTML parsing, main content extraction, tables, links, metadata, and dates."""

from pathlib import Path

from app.web.extraction.date_extractor import DateExtractor
from app.web.extraction.html_parser import parse_html_tree
from app.web.extraction.link_extractor import LinkExtractor
from app.web.extraction.main_content import MainContentExtractor
from app.web.extraction.metadata_extractor import MetadataExtractor
from app.web.extraction.table_extractor import TableExtractor
from app.web.models.document import LinkType

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "html"


def load_fixture(name: str) -> str:
    path = FIXTURES_DIR / name
    return path.read_text(encoding="utf-8")


def test_scholarship_page_extraction() -> None:
    html = load_fixture("scholarship_page.html")
    tree = parse_html_tree(html)

    # 1. Metadata
    title, metadata, canonical, lang = MetadataExtractor.extract_metadata(tree)
    assert "Global Master's Excellence Scholarship" in title
    assert canonical == "https://scholarships.example.org/excellence-2026"
    assert metadata["description"] is not None

    # 2. Tables
    tables = TableExtractor.extract_tables(tree)
    assert len(tables) >= 1
    sched_table = tables[0]
    assert sched_table.caption == "Application Stages & Deadlines"
    assert "Round" in sched_table.columns
    assert len(sched_table.rows) == 2
    assert "15 December 2026" in sched_table.rows[0]

    # 3. Main Content & Boilerplate Stripping
    clean_text, headings, word_count = MainContentExtractor.extract_clean_content(tree, tables)
    assert word_count > 50
    # Boilerplate removed
    assert "cookie" not in clean_text.lower()
    assert "privacy policy" not in clean_text.lower()

    # Headings preserved
    heading_texts = [h.text for h in headings]
    assert "Eligibility Criteria" in heading_texts
    assert "Funding & Benefits" in heading_texts

    # 4. Links
    links = LinkExtractor.extract_links(
        tree, base_url="https://scholarships.example.org/excellence-2026"
    )
    link_types = {link.link_type for link in links}
    assert LinkType.APPLICATION in link_types
    assert LinkType.PDF in link_types
    assert LinkType.ELIGIBILITY in link_types

    # 5. Date Candidates (Extracted without semantic assignment)
    dates = DateExtractor.extract_dates(clean_text)
    raw_dates = [d.raw_text for d in dates]
    assert any("15 December 2026" in rd for rd in raw_dates)
    assert any("1 October 2026" in rd for rd in raw_dates)


def test_noisy_page_boilerplate_pruning() -> None:
    html = load_fixture("noisy_page.html")
    tree = parse_html_tree(html)

    tables = TableExtractor.extract_tables(tree)
    clean_text, headings, word_count = MainContentExtractor.extract_clean_content(tree, tables)

    # Verify ads, cookie banner, newsletter, and sidebar stories are pruned
    assert "Sponsored Commercial Ads" not in clean_text
    assert "Accept all tracking cookies" not in clean_text
    assert "Best Coffee Shops in Berlin" not in clean_text
    assert "Subscribe to our daily promotional newsletter" not in clean_text

    # Main content remains intact
    assert "DAAD Master Studies Scholarship Opportunities" in clean_text
    assert "€934 per month" in clean_text


def test_table_heavy_page_extraction() -> None:
    html = load_fixture("table_heavy_page.html")
    tree = parse_html_tree(html)

    tables = TableExtractor.extract_tables(tree)
    assert len(tables) == 3

    # Check first table (stipends)
    assert tables[0].caption == "Monthly Stipend Rates"
    assert "London Rate" in tables[0].columns

    # Check second table (quotas)
    assert tables[1].caption == "Scholarship Seats per Region"
    assert len(tables[1].rows) == 3

    # Formatted markdown table check
    md = TableExtractor.format_table_as_markdown(tables[0])
    assert "| London Rate |" in md
    assert "| --- |" in md
