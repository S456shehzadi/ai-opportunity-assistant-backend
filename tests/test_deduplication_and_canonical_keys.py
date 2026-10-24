"""Tests for opportunity deduplication, URL normalization, and canonical keys."""

from app.opportunities.extraction.deduplication import OpportunityDeduplicator


def test_clean_canonical_url():
    """Tests URL cleaning: stripping tracking parameters, fragments, and www."""
    url1 = "https://www.daad.de/en/study-and-research-in-germany/scholarships/?utm_source=facebook&utm_medium=cpc#apply"
    url2 = "https://daad.de/en/study-and-research-in-germany/scholarships"

    clean1 = OpportunityDeduplicator.clean_canonical_url(url1)
    clean2 = OpportunityDeduplicator.clean_canonical_url(url2)

    assert clean1 == clean2
    assert "utm_source" not in clean1
    assert "#apply" not in clean1
    assert clean1 == "daad.de/en/study-and-research-in-germany/scholarships"


def test_canonical_key_generation_deterministic():
    """Tests that identical opportunity records produce identical canonical keys."""
    key1 = OpportunityDeduplicator.generate_canonical_key(
        title="Rhodes Scholarship for Global Leaders 2026",
        organization="University of Oxford",
        category="Scholarship",
        official_url="https://www.rhodeshouse.ox.ac.uk/scholarships/?ref=ad",
    )
    key2 = OpportunityDeduplicator.generate_canonical_key(
        title="Rhodes Scholarship for Global Leaders 2026",
        organization="Oxford University",  # Normalizes to University of Oxford
        category="Scholarship",
        official_url="https://rhodeshouse.ox.ac.uk/scholarships",
    )

    assert key1 == key2
    assert key1.startswith("opp_")


def test_are_duplicates():
    """Tests identifying duplicate programs while avoiding false positive merges."""
    # Duplicates with tracking differences
    is_dup = OpportunityDeduplicator.are_duplicates(
        title_a="Schwarzman Scholars Program",
        org_a="Tsinghua University",
        url_a="https://schwarzmanscholars.org/apply?ref=twitter",
        title_b="Schwarzman Scholars Program",
        org_b="Tsinghua University",
        url_b="https://schwarzmanscholars.org/apply",
    )
    assert is_dup is True

    # Different programs at same university
    not_dup = OpportunityDeduplicator.are_duplicates(
        title_a="Undergraduate Merit Scholarship",
        org_a="Stanford University",
        url_a="https://stanford.edu/undergraduate-aid",
        title_b="Knight-Hennessy Scholars Graduate Program",
        org_b="Stanford University",
        url_b="https://knight-hennessy.stanford.edu",
    )
    assert not_dup is False
