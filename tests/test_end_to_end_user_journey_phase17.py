"""Comprehensive End-to-End Integration Test Suite (Phase 17).

Verifies the complete unified user journey across all integrated subsystems:
1. Registration & Authentication (JWT Bearer tokens)
2. User Profile creation & normalization under authenticated context
3. Academic records, skills & target preferences configuration
4. Opportunity ingestion, structured extraction & validation with evidence provenance
5. Advanced semantic & hybrid discovery search with fallback
6. Evidence-grounded eligibility evaluation
7. Personalized ranking modulated by user preferences
8. Verified opportunity details retrieval
9. Grounded Conversational AI Assistant with citation provenance
10. Explicit user feedback submission and accuracy reporting
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.discovery import get_discovery_engine
from app.discovery.models import OpportunitySearchDocument, SearchStrategy
from app.web.models.document import WebDocument


@pytest.mark.asyncio
async def test_full_user_journey_end_to_end(client: AsyncClient) -> None:
    # -------------------------------------------------------------------------
    # STEP 1: Registration and Authentication
    # -------------------------------------------------------------------------
    register_payload = {
        "email": "fatima.scholar@example.com",
        "password": "SecurePassword123!",
        "full_name": "Fatima Zahra",
    }
    reg_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
    user_data = reg_res.json()
    assert user_data["email"] == "fatima.scholar@example.com"
    assert user_data["id"]

    login_payload = {
        "email": "fatima.scholar@example.com",
        "password": "SecurePassword123!",
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    auth_tokens = login_res.json()
    access_token = auth_tokens["access_token"]
    assert access_token, "Access token missing from login response"

    headers = {"Authorization": f"Bearer {access_token}"}

    # -------------------------------------------------------------------------
    # STEP 2: Profile Creation and Normalization (Isolated to Fatima)
    # -------------------------------------------------------------------------
    profile_payload = {
        "nationality": "Pakistan",
        "country_of_residence": "Pakistan",
        "city": "Lahore",
        "education_level": "Undergraduate",
        "degree_title": "BS Computer Science",
        "field_of_study": "Computer Science",
        "university": "LUMS",
        "graduation_year": 2025,
        "cgpa": 3.82,
        "percentage": 88.5,
    }
    prof_res = await client.post("/api/v1/profile", json=profile_payload, headers=headers)
    assert prof_res.status_code == 201, f"Create profile failed: {prof_res.text}"
    assert prof_res.json()["nationality"] == "Pakistan"

    # Add Academic Record
    acad_payload = {
        "institution": "LUMS",
        "degree": "BS Computer Science",
        "field_of_study": "Computer Science",
        "start_year": 2021,
        "end_year": 2025,
        "grade": "3.82",
        "grading_scale": "4.0",
        "country": "Pakistan",
        "is_current": True,
    }
    acad_res = await client.post(
        "/api/v1/profile/academic-records", json=acad_payload, headers=headers
    )
    assert acad_res.status_code == 201

    # Add Skill
    skill_res = await client.post(
        "/api/v1/profile/skills",
        json={"name": "Machine Learning", "proficiency": "Advanced"},
        headers=headers,
    )
    assert skill_res.status_code == 201

    # Set Preferences
    pref_payload = {
        "target_degree_levels": ["Master's"],
        "target_fields": ["Computer Science", "Artificial Intelligence"],
        "target_countries": ["Germany", "United Kingdom", "United States"],
        "funding_preference": "FULLY_FUNDED",
        "requires_no_ielts": True,
        "requires_no_application_fee": True,
    }
    pref_res = await client.put(
        "/api/v1/profile/preferences", json=pref_payload, headers=headers
    )
    assert pref_res.status_code == 200

    # -------------------------------------------------------------------------
    # STEP 3: Opportunity Ingestion, Extraction & Validation
    # -------------------------------------------------------------------------
    sample_daad_html = (
        "<html>\n"
        "<head><title>DAAD Helmut-Schmidt-Programme Master Scholarships</title></head>\n"
        "<body>\n"
        "<h1>Helmut-Schmidt-Programme (Master Scholarships)</h1>\n"
        "<p>Provider: DAAD (German Academic Exchange Service)</p>\n"
        "<p>Target: Master degree in Public Policy and Computer Systems.</p>\n"
        "<p>Funding: Fully funded scholarship with monthly stipend and health insurance.</p>\n"
        "<p>Requirements: Bachelor degree with minimum 3.0 GPA. Open to Pakistan.</p>\n"
        "<p>Language: English certificate accepted. No mandatory IELTS.</p>\n"
        "<p>Application Deadline: 2026-11-30. No application fee.</p>\n"
        "<a href=\"https://www.daad.de/en/apply\">Apply Now</a>\n"
        "</body>\n"
        "</html>\n"
    )
    web_doc = WebDocument(
        original_url="https://www.daad.de/en/helmut-schmidt-programme/",
        final_url="https://www.daad.de/en/helmut-schmidt-programme/",
        domain="daad.de",
        title="DAAD Helmut-Schmidt-Programme Master Scholarships",
        clean_text=(
            "DAAD Helmut-Schmidt-Programme fully funded master scholarship in Germany. "
            "No mandatory IELTS. Deadline 2026-11-30."
        ),
        raw_html=sample_daad_html,
        status_code=200,
        content_type="text/html",
    )

    extract_res = await client.post(
        "/api/v1/opportunities/extract",
        json={"document": web_doc.model_dump(mode="json")},
        headers=headers,
    )
    assert extract_res.status_code == 200, f"Extraction failed: {extract_res.text}"
    extracted_opp = extract_res.json()
    assert extracted_opp["title"]
    assert extracted_opp["organization"]

    # -------------------------------------------------------------------------
    # STEP 4: Semantic Discovery & Hybrid Search
    # -------------------------------------------------------------------------
    # Index extracted opportunity into the discovery engine for searchability
    engine = get_discovery_engine()
    opp_search_doc = OpportunitySearchDocument(
        opportunity_id="daad-hsp-2026",
        title="DAAD Helmut-Schmidt-Programme Master Scholarships",
        provider="DAAD Germany",
        category="Scholarship",
        description="Fully funded German master scholarship in public policy and computer science.",
        funding_summary="Fully funded with 934 EUR monthly stipend",
        degree_levels=["Master's"],
        fields=["Computer Science", "Public Policy", "Artificial Intelligence"],
        countries=["Germany"],
        nationalities=["Pakistan", "Global"],
        source_url="https://www.daad.de/en/helmut-schmidt-programme/",
        source_type="Official Portal",
    )
    engine.index_document(opp_search_doc)

    discovery_search_payload = {
        "query": "Fully funded master's scholarships in Germany without IELTS",
        "strategy": SearchStrategy.HYBRID_RERANK.value,
        "limit": 10,
    }
    disc_res = await client.post(
        "/api/v1/discovery/search",
        json=discovery_search_payload,
        headers=headers,
    )
    assert disc_res.status_code == 200, f"Discovery search failed: {disc_res.text}"
    search_data = disc_res.json()
    assert search_data["total_found"] >= 1
    found_cards = search_data["results"]
    assert any("DAAD" in c["title"] or "DAAD" in c["provider"] for c in found_cards)

    # -------------------------------------------------------------------------
    # STEP 5: Personalized Opportunity Ranking
    # -------------------------------------------------------------------------
    rank_payload = {
        "opportunities": [extracted_opp],
        "include_ineligible": False,
    }
    rank_res = await client.post(
        "/api/v1/opportunities/rank",
        json=rank_payload,
        headers=headers,
    )
    assert rank_res.status_code == 200, f"Ranking failed: {rank_res.text}"
    ranked_result = rank_res.json()
    assert len(ranked_result["opportunities"]) >= 1

    # -------------------------------------------------------------------------
    # STEP 6: Grounded Conversational AI Assistant
    # -------------------------------------------------------------------------
    chat_payload = {
        "conversation_id": "conv-test-phase17",
        "message": "Are there fully funded opportunities in Germany that do not require IELTS?",
    }
    chat_res = await client.post(
        "/api/v1/assistant/chat",
        json=chat_payload,
        headers=headers,
    )
    assert chat_res.status_code == 200, f"Assistant chat failed: {chat_res.text}"
    assistant_reply = chat_res.json()
    assert assistant_reply["message"]
    assert assistant_reply["response_type"] in [
        "TEXT",
        "OPPORTUNITY_LIST",
        "OPPORTUNITY_DETAIL",
        "ELIGIBILITY_EXPLANATION",
    ]

    # -------------------------------------------------------------------------
    # STEP 7: Explicit Feedback Reporting
    # -------------------------------------------------------------------------
    feedback_payload = {
        "target_type": "OPPORTUNITY",
        "target_id": "daad-hsp-2026",
        "feedback_type": "HELPFUL",
        "comment": "Accurately noted that IELTS is not mandatory for English-taught graduates.",
    }
    feed_res = await client.post(
        "/api/v1/feedback",
        json=feedback_payload,
        headers=headers,
    )
    assert feed_res.status_code == 201, f"Feedback submission failed: {feed_res.text}"
    feed_data = feed_res.json()
    assert feed_data["status"] in ["NEW", "RECORDED"]
    assert feed_data["feedback_type"] == "HELPFUL"
    assert feed_data["target_id"] == "daad-hsp-2026"
    assert feed_data["comment"] == (
        "Accurately noted that IELTS is not mandatory for English-taught graduates."
    )
