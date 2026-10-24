import pytest

from app.search.agent.search_agent import SearchAgent
from app.search.models.search_result import SearchResponse
from app.search.providers.mock_provider import MockSearchProvider


@pytest.mark.asyncio
async def test_search_agent_scenario_germany_scholarships() -> None:
    agent = SearchAgent(provider=MockSearchProvider())
    response: SearchResponse = await agent.execute_search(
        "Find fully funded master's scholarships in Germany for international students."
    )

    assert response.total_results > 0
    assert len(response.executed_queries) >= 1
    # Check that DAAD or TUM was discovered as an official source candidate
    assert any(r.is_official_source_candidate for r in response.results)
    # Check canonical URL normalization (no tracking parameters)
    assert all("utm_source" not in r.url for r in response.results)


@pytest.mark.asyncio
async def test_search_agent_scenario_ai_internships_europe() -> None:
    agent = SearchAgent(provider=MockSearchProvider())
    response: SearchResponse = await agent.execute_search("Find AI internships in Europe.")

    assert response.total_results > 0
    domains = [r.domain for r in response.results]
    assert any("mpi-inf.mpg.de" in d or "cern" in d for d in domains)


@pytest.mark.asyncio
async def test_search_agent_scenario_research_fellowships_ml() -> None:
    agent = SearchAgent(provider=MockSearchProvider())
    response: SearchResponse = await agent.execute_search(
        "Find research fellowships in machine learning."
    )

    assert response.total_results > 0
    # Marie Curie or Humboldt fellowships discovered
    snippets = [r.snippet.lower() for r in response.results]
    assert any("fellowship" in s or "postdoctoral" in s for s in snippets)


@pytest.mark.asyncio
async def test_search_agent_scenario_startup_funding() -> None:
    agent = SearchAgent(provider=MockSearchProvider())
    response: SearchResponse = await agent.execute_search(
        "Find startup funding programs available internationally."
    )

    assert response.total_results > 0
    titles = [r.title.lower() for r in response.results]
    assert any("funding" in t or "grant" in t or "eic" in t for t in titles)


@pytest.mark.asyncio
async def test_search_agent_scenario_government_scholarships() -> None:
    agent = SearchAgent(provider=MockSearchProvider())
    response: SearchResponse = await agent.execute_search(
        "Find government scholarships for master's students."
    )

    assert response.total_results > 0
    assert response.provider_used == "mock"
    assert response.duration_ms >= 0.0
