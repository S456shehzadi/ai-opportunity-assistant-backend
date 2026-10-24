import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_profile_endpoints(client: AsyncClient) -> None:
    # 1. Create Profile
    create_payload = {
        "nationality": "Pakistan",
        "country_of_residence": "Pakistan",
        "city": "Lahore",
        "education_level": "Undergraduate",
        "degree_title": "BS Software Engineering",
        "field_of_study": "Software Engineering",
        "university": "PUCIT",
        "graduation_year": 2025,
        "cgpa": 3.75,
        "percentage": 85.0,
    }
    res = await client.post("/api/v1/profile", json=create_payload)
    assert res.status_code == 201
    profile_data = res.json()
    assert profile_data["nationality"] == "Pakistan"
    assert profile_data["cgpa"] == 3.75

    # 2. Get Consolidated Profile
    get_res = await client.get("/api/v1/profile")
    assert get_res.status_code == 200
    full_profile = get_res.json()
    assert full_profile["profile"]["city"] == "Lahore"
    assert full_profile["email"] == "developer@example.com"

    # 3. Patch Profile
    patch_res = await client.patch("/api/v1/profile", json={"city": "Islamabad"})
    assert patch_res.status_code == 200
    assert patch_res.json()["city"] == "Islamabad"


@pytest.mark.asyncio
async def test_academic_records_and_sub_resources(client: AsyncClient) -> None:
    # Add Academic Record
    record_payload = {
        "institution": "National University of Sciences and Technology (NUST)",
        "degree": "MS Artificial Intelligence",
        "field_of_study": "Computer Science",
        "start_year": 2023,
        "end_year": 2025,
        "grade": "3.88",
        "grading_scale": "4.0",
        "country": "Pakistan",
        "is_current": True,
    }
    rec_res = await client.post("/api/v1/profile/academic-records", json=record_payload)
    assert rec_res.status_code == 201
    record_id = rec_res.json()["id"]

    # Add Skill
    skill_res = await client.post(
        "/api/v1/profile/skills",
        json={
            "name": "PyTorch",
            "category": "AI/ML",
            "proficiency": "Advanced",
            "years_of_experience": 3.0,
        },
    )
    assert skill_res.status_code == 201
    assert skill_res.json()["name"] == "PyTorch"

    # Add Test Result
    test_res = await client.post(
        "/api/v1/profile/test-results",
        json={
            "test_name": "IELTS Academic",
            "test_type": "Language",
            "score": "8.0",
            "score_details": {"overall": 8.0, "reading": 8.5, "listening": 8.0},
        },
    )
    assert test_res.status_code == 201
    assert test_res.json()["score"] == "8.0"

    # Verify AI Context endpoint aggregates these sub-records
    ai_ctx_res = await client.get("/api/v1/profile/ai-context")
    assert ai_ctx_res.status_code == 200
    ai_context = ai_ctx_res.json()
    assert "PyTorch" in ai_context["skills"]
    assert "IELTS Academic" in ai_context["standardized_tests"]["test_scores"]

    # Delete Academic Record
    del_res = await client.delete(f"/api/v1/profile/academic-records/{record_id}")
    assert del_res.status_code == 204
