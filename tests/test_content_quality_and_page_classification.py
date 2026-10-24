"""Tests for content quality assessment, page classification, and JS-dependency detection."""

from pathlib import Path

from app.web.analysis.page_classifier import PageTypeClassifier
from app.web.analysis.quality_analyzer import ContentQualityAnalyzer
from app.web.models.document import ExtractedHeading, PageType
from app.web.retrieval.rendered_retriever import detect_js_dependency

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "html"


def test_content_quality_assessment() -> None:
    # 1. Substantial structured content
    headings = [
        ExtractedHeading(level=1, text="Scholarship Title"),
        ExtractedHeading(level=2, text="Eligibility"),
    ]
    long_text = "This is a detailed scholarship description with criteria and deadlines. " * 20
    score_good = ContentQualityAnalyzer.analyze(
        clean_text=long_text,
        raw_html="<html>" + long_text + "</html>",
        headings=headings,
        word_count=len(long_text.split()),
    )
    assert score_good.has_main_content is True
    assert score_good.quality_score >= 0.7
    assert "substantial_content" in score_good.quality_flags

    # 2. Very low content / poor quality
    score_poor = ContentQualityAnalyzer.analyze(
        clean_text="Error page",
        raw_html="<html>" + ("x" * 2000) + "</html>",
        headings=[],
        word_count=2,
    )
    assert score_poor.has_main_content is False
    assert score_poor.quality_score <= 0.3
    assert "very_short_text" in score_poor.quality_flags


def test_page_type_classification() -> None:
    # Opportunity Page
    type_opp = PageTypeClassifier.classify(
        title="Fulbright Foreign Student Fellowship Program",
        clean_text=(
            "The Fulbright grant covers tuition, living stipend, and health insurance. "
            "Submit application before deadline."
        ),
        url="https://fulbright.example.org/scholarships/apply",
    )
    assert type_opp == PageType.OPPORTUNITY_PAGE

    # University Program Page
    type_prog = PageTypeClassifier.classify(
        title="Master of Science in Artificial Intelligence",
        clean_text="The curriculum consists of 120 ECTS credit points over 4 semesters of study.",
        url="https://university.example.edu/programs/msc-ai",
    )
    assert type_prog == PageType.PROGRAM_PAGE

    # Home Page
    type_home = PageTypeClassifier.classify(
        title="Global University",
        clean_text="Welcome to the university website.",
        url="https://university.example.edu/",
    )
    assert type_home == PageType.HOME_PAGE


def test_js_dependency_detection() -> None:
    js_html = (FIXTURES_DIR / "js_dependent_page.html").read_text(encoding="utf-8")
    is_dependent = detect_js_dependency(
        raw_html=js_html,
        clean_text="You need to enable JavaScript to run this app.",
        word_count=8,
    )
    assert is_dependent is True
