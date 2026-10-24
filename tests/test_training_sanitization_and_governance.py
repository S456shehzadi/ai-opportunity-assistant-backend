"""Tests for data sanitization, PII redaction, and group-aware splitting."""

from __future__ import annotations

from app.evaluation.models.dataset import SplitType
from app.learning.models.model_registry import ModelType
from app.learning.pipelines.dataset_builder import DatasetBuilder
from app.learning.sanitizers.training_sanitizer import TrainingDataSanitizer


def test_training_sanitizer_redacts_pii_and_secrets() -> None:
    sanitizer = TrainingDataSanitizer()

    sample_text = (
        "Contact applicant at john.doe@example.org or call +1 555-123-4567. "
        "SSN is 123-45-6789. Card is 4111-2222-3333-4444. "
        "Authorization header: Bearer sk-live-secrettoken1234567890abcdef. "
        "Address is 742 Evergreen Terrace."
    )

    cleaned, was_redacted = sanitizer.sanitize_text(sample_text)

    assert was_redacted is True
    assert "john.doe@example.org" not in cleaned
    assert "[REDACTED_EMAIL]" in cleaned
    assert "555-123-4567" not in cleaned
    assert "[REDACTED_PHONE]" in cleaned
    assert "123-45-6789" not in cleaned
    assert "[REDACTED_SSN]" in cleaned
    assert "4111-2222-3333-4444" not in cleaned
    assert "[REDACTED_CARD]" in cleaned
    assert "sk-live-secrettoken1234567890abcdef" not in cleaned
    assert "[REDACTED_KEY]" in cleaned
    assert "742 Evergreen Terrace" not in cleaned
    assert "[REDACTED_ADDRESS]" in cleaned


def test_training_sanitizer_verifies_provenance_and_consent() -> None:
    sanitizer = TrainingDataSanitizer()

    # 1. Private user interaction without consent -> Rejected
    unconsented_private = {
        "input_data": {"message": "How do I apply?"},
        "expected_output": {"response": "Click here."},
        "metadata": {"is_user_interaction": True, "user_consent": False},
    }
    assert sanitizer.verify_provenance_and_consent(unconsented_private) is False

    # 2. Private user interaction with explicit consent -> Accepted
    consented_private = {
        "input_data": {"message": "How do I apply?"},
        "expected_output": {"response": "Click here."},
        "metadata": {
            "is_user_interaction": True,
            "user_consent": True,
            "source_id": "session-123",
        },
    }
    assert sanitizer.verify_provenance_and_consent(consented_private) is True

    # 3. Proprietary forbidden license -> Rejected
    forbidden_license = {
        "input_data": {"text": "Scholarship info"},
        "expected_output": {"funding": "1000"},
        "metadata": {"source_url": "https://example.com", "license": "PROPRIETARY"},
    }
    assert sanitizer.verify_provenance_and_consent(forbidden_license) is False

    # 4. Verified public benchmark source -> Accepted
    valid_benchmark = {
        "input_data": {"text": "DAAD scholarship criteria"},
        "expected_output": {"eligibility": "BSc"},
        "provenance_review_id": "00000000-0000-0000-0000-000000000001",
        "metadata": {"benchmark_name": "daad_v1", "license": "CC-BY-4.0"},
    }
    assert sanitizer.verify_provenance_and_consent(valid_benchmark) is True


def test_dataset_builder_deduplication() -> None:
    builder = DatasetBuilder()

    examples = [
        {"input_data": {"query": "Erasmus Mundus scholarship"}, "expected_output": {"task": "q"}},
        {"input_data": {"query": "Erasmus Mundus scholarship"}, "expected_output": {"task": "q"}},
        {
            "input_data": {"query": "Erasmus Mundus scholarship master program fully funded"},
            "expected_output": {"task": "q"},
        },
        {
            "input_data": {"query": "DAAD Helmut Schmidt Fellowship"},
            "expected_output": {"task": "q"},
        },
    ]

    deduped = builder.deduplicate_examples(examples, near_duplicate_threshold=0.90)
    # The duplicate should be filtered out
    assert len(deduped) < len(examples)
    assert any("DAAD" in str(e["input_data"]) for e in deduped)


def test_group_aware_split_prevents_leakage() -> None:
    builder = DatasetBuilder()

    # Create 20 examples across 4 distinct opportunity groups
    examples = []
    for group_num in range(1, 5):
        opp_id = f"opp_group_{group_num}"
        for item_idx in range(5):
            examples.append(
                {
                    "input_data": {"query": f"item {item_idx} for {opp_id}"},
                    "expected_output": {"label": "match"},
                    "metadata": {"opportunity_id": opp_id},
                }
            )

    splits = builder.group_aware_split(
        examples=examples,
        train_ratio=0.50,
        val_ratio=0.25,
        test_ratio=0.25,
        holdout_ratio=0.0,
        group_key="opportunity_id",
    )

    train_opps = {e["metadata"]["opportunity_id"] for e in splits[SplitType.TRAIN]}
    val_opps = {e["metadata"]["opportunity_id"] for e in splits[SplitType.VALIDATION]}
    test_opps = {e["metadata"]["opportunity_id"] for e in splits[SplitType.TEST]}

    # Strictly disjoint sets - zero overlap of opportunity groups across splits
    assert train_opps.isdisjoint(val_opps)
    assert train_opps.isdisjoint(test_opps)
    assert val_opps.isdisjoint(test_opps)


def test_build_task_dataset_end_to_end() -> None:
    builder = DatasetBuilder()

    raw_data = [
        {
            "input_data": {"text": "John Doe email john.doe@example.com applies for opp_A"},
            "expected_output": {"status": "eligible"},
            "provenance_review_id": "00000000-0000-0000-0000-000000000001",
            "metadata": {"opportunity_id": "opp_A", "license": "MIT"},
        },
        {
            "input_data": {"text": "Unconsented private message"},
            "expected_output": {"status": "none"},
            "metadata": {"is_user_interaction": True, "user_consent": False},
        },
    ]

    splits = builder.build_task_dataset(
        task=ModelType.ELIGIBILITY_ASSIST,
        raw_examples=raw_data,
        train_ratio=1.0,
        val_ratio=0.0,
        test_ratio=0.0,
    )

    # Unconsented was rejected, valid example was sanitized
    train_set = splits[SplitType.TRAIN]
    assert len(train_set) == 1
    assert "[REDACTED_EMAIL]" in str(train_set[0]["input_data"])
    assert "john.doe@example.com" not in str(train_set[0]["input_data"])
