"""Tests for robots.txt parsing, ethical policy compliance, and domain caching."""

from unittest.mock import AsyncMock, patch
from urllib.robotparser import RobotFileParser

import pytest

from app.web.policies.robots_service import RobotsPolicyService


@pytest.mark.asyncio
async def test_robots_allowed_and_disallowed_paths() -> None:
    service = RobotsPolicyService(cache_ttl_seconds=3600)

    # Build mock parser
    mock_parser = RobotFileParser()
    robots_txt = """
User-agent: *
Disallow: /private/
Disallow: /admin/
Allow: /scholarships/
    """
    mock_parser.parse(robots_txt.splitlines())

    with patch.object(service, "_fetch_and_parse_robots", new=AsyncMock(return_value=mock_parser)):
        # Allowed path
        allowed = await service.is_allowed("https://example.org/scholarships/daad-2026")
        assert allowed is True

        # Disallowed path
        disallowed = await service.is_allowed("https://example.org/private/internal-doc")
        assert disallowed is False


@pytest.mark.asyncio
async def test_robots_caching_behavior() -> None:
    service = RobotsPolicyService(cache_ttl_seconds=3600)
    mock_parser = RobotFileParser()
    mock_parser.allow_all = True

    fetch_mock = AsyncMock(return_value=mock_parser)
    with patch.object(service, "_fetch_and_parse_robots", new=fetch_mock):
        # First call fetches
        await service.is_allowed("https://example.org/page1")
        assert fetch_mock.call_count == 1

        # Second call for same domain hits cache
        await service.is_allowed("https://example.org/page2")
        assert fetch_mock.call_count == 1


@pytest.mark.asyncio
async def test_robots_user_agent_specific_rule() -> None:
    service = RobotsPolicyService(cache_ttl_seconds=3600)
    mock_parser = RobotFileParser()
    robots_txt = """
User-agent: AIOpportunityAssistantBot
Disallow: /restricted-bot/

User-agent: *
Allow: /
    """
    mock_parser.parse(robots_txt.splitlines())

    with patch.object(service, "_fetch_and_parse_robots", new=AsyncMock(return_value=mock_parser)):
        # Specific user-agent disallowed
        res_bot = await service.is_allowed(
            "https://example.org/restricted-bot/info",
            user_agent="AIOpportunityAssistantBot/1.0",
        )
        assert res_bot is False

        # Other user agent allowed
        res_other = await service.is_allowed(
            "https://example.org/restricted-bot/info",
            user_agent="OtherCrawler/1.0",
        )
        assert res_other is True
