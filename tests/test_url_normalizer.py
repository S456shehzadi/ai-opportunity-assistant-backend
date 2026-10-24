from app.search.normalization.url_normalizer import UrlNormalizer


def test_url_normalizer_strips_tracking_parameters() -> None:
    raw = "https://www.daad.de/en/scholarships/?utm_source=google&utm_medium=cpc&utm_campaign=daad_2026&ref=search"
    clean = UrlNormalizer.normalize_url(raw)
    assert clean == "https://www.daad.de/en/scholarships"
    assert "utm_source" not in clean
    assert "ref" not in clean


def test_url_normalizer_preserves_meaningful_query_params() -> None:
    raw = "https://example.org/search?program=ai&degree=masters&utm_source=facebook"
    clean = UrlNormalizer.normalize_url(raw)
    assert "program=ai" in clean
    assert "degree=masters" in clean
    assert "utm_source" not in clean


def test_url_normalizer_strips_fragments_and_trailing_slashes() -> None:
    raw = "https://www.tum.de/en/studies/fees-and-financial-aid/scholarships/#eligibility-criteria"
    clean = UrlNormalizer.normalize_url(raw)
    assert clean == "https://www.tum.de/en/studies/fees-and-financial-aid/scholarships"
    assert "#" not in clean
    assert not clean.endswith("/")


def test_url_normalizer_extracts_domain() -> None:
    assert UrlNormalizer.extract_domain("https://www.daad.de/en/path") == "daad.de"
    assert UrlNormalizer.extract_domain("http://tum.de:8080/studies") == "tum.de"
    assert (
        UrlNormalizer.extract_domain("https://erasmus-plus.ec.europa.eu/")
        == "erasmus-plus.ec.europa.eu"
    )


def test_url_normalizer_is_same_resource() -> None:
    u1 = "https://www.daad.de/en/scholarships/?utm_source=email"
    u2 = "https://www.daad.de/en/scholarships/#top"
    assert UrlNormalizer.is_same_resource(u1, u2) is True
