from app.core.config import Settings, parse_cors_origins


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.APP_NAME == "AI Opportunity Assistant API"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.is_development is True
    assert settings.is_production is False
    assert settings.AI_MODEL_PROVIDER == "mock"
    assert settings.SEARCH_PROVIDER == "mock"


def test_cors_origins_parsing() -> None:
    assert parse_cors_origins("http://localhost:3000, http://127.0.0.1:3000") == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    assert parse_cors_origins(["https://example.com"]) == ["https://example.com"]
