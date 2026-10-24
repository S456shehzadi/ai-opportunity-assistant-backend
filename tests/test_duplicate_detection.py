"""Tests for exact and near-duplicate content detection using SHA-256 and SimHash."""

from app.web.analysis.duplicate_detector import DuplicateDetector


def test_exact_duplicate_detection() -> None:
    text1 = "This is a DAAD scholarship announcement for international master's students in 2026."
    text2 = (
        "  This is a DAAD scholarship announcement for international master's students in 2026.  \n"
    )
    text3 = "This is an Erasmus Mundus grant announcement for undergraduate students in 2027."

    hash1 = DuplicateDetector.compute_content_hash(text1)
    hash2 = DuplicateDetector.compute_content_hash(text2)
    hash3 = DuplicateDetector.compute_content_hash(text3)

    assert hash1 == hash2  # Whitespace-insensitive exact match
    assert DuplicateDetector.is_exact_duplicate(hash1, hash2) is True
    assert DuplicateDetector.is_exact_duplicate(hash1, hash3) is False


def test_near_duplicate_detection_simhash() -> None:
    # Identical article with minor variation (updated date / timestamp)
    base_text = (
        "The German Academic Exchange Service offers full funding for international students. "
        "Awardees receive €1,200 monthly stipend, health insurance, and travel allowance. "
        "Minimum requirement is a Bachelor degree with GPA 3.0. "
    ) * 5

    variant_text = base_text + " Published on 15 September 2026."
    distinct_text = (
        "CERN Summer Student Program offers undergraduate students in physics a chance "
        "to work on particle accelerators in Geneva Switzerland with laboratory sessions. "
    ) * 5

    sim1 = DuplicateDetector.compute_simhash(base_text)
    sim2 = DuplicateDetector.compute_simhash(variant_text)
    sim_distinct = DuplicateDetector.compute_simhash(distinct_text)

    # Near duplicate should have small Hamming distance (<= 6)
    assert DuplicateDetector.is_near_duplicate(sim1, sim2, max_hamming_distance=6) is True

    # Distinct content should not be considered near duplicate
    assert DuplicateDetector.is_near_duplicate(sim1, sim_distinct, max_hamming_distance=6) is False


def test_jaccard_similarity() -> None:
    t1 = "Full funding for master students in computer science in Germany"
    t2 = "Full funding for master students in artificial intelligence in Germany"
    t3 = "Completely different text about cooking recipes and food ingredients"

    sim_high = DuplicateDetector.compute_jaccard_similarity(t1, t2, n=2)
    sim_low = DuplicateDetector.compute_jaccard_similarity(t1, t3, n=2)

    assert sim_high > 0.4
    assert sim_low == 0.0
