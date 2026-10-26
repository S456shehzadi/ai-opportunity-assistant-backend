"""Comprehensive verification of global education levels and opportunity eligibility matching.

Tests all 15 core scenarios specified in Prompt 25 Section 12:
1. Matriculation student gets scholarships for secondary school / Matric.
2. Matriculation student excluded from graduate/bachelor scholarships requiring degree completion.
3. Intermediate student (FSc/ICS) gets undergraduate entry scholarships and intermediate merit awards.
4. A-Levels student receives international undergraduate admissions scholarships.
5. Vocational / DAE student receives technical training grants and vocational transition scholarships.
6. Associate degree graduate matches completion-to-bachelor degree bridge opportunities.
7. Bachelor's graduate matches Master's scholarships and graduate fellowships.
8. Master's graduate matches PhD fellowships and research assistantships.
9. PhD graduate matches Postdoc fellowships.
10. Professional qualification holder (e.g. ACCA/CA) matches professional development awards.
11. User with No Formal Qualification matches skill-based, bootcamp, and open opportunities.
12. Multi-record profile (e.g. Bachelor's user with Intermediate & Matric records) matches both.
13. Opportunity with NO degree requirements matches ANY user level.
14. Natural progression eligibility (e.g. Completed Intermediate matches target Bachelor's program).
15. Search query understanding extracts Matriculation, Intermediate, A-Levels, DAE, and Vocational correctly.
"""

from __future__ import annotations

import pytest
from app.ai.query.query_understanding_service import QueryUnderstandingService
from app.models.profile import EducationLevel
from app.opportunities.eligibility.evaluators import AcademicEvaluator
from app.opportunities.eligibility.profile_adapter import UnifiedUserFacts
from app.opportunities.eligibility.requirement_adapter import OpportunityRequirementItem
from app.opportunities.eligibility.schemas import RequirementStatus
from app.services.normalization.education_normalizer import EducationNormalizer


class TestGlobalEducationLevelsAndEligibility:
    """Tests all 15 scenarios covering worldwide education levels and matching rules."""

    # Scenario 1: Matriculation student gets scholarships for secondary school / Matric
    def test_scenario_01_matriculation_matches_secondary_scholarship(self):
        user = UnifiedUserFacts(
            user_id="user_matric",
            current_education_level=EducationLevel.MATRICULATION.value,
            academic_records=[
                {
                    "degree": "Matriculation / Secondary School",
                    "education_level": EducationLevel.MATRICULATION.value,
                    "stream": "Science (Biology)",
                    "status": "Currently Studying",
                    "country": "Pakistan",
                }
            ],
        )
        req = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="Open to Matriculation / SSC / Secondary school students",
            required_value=["Matriculation / Secondary School"],
        )
        res = AcademicEvaluator.evaluate_degree_level(user, req)
        assert res.status == RequirementStatus.MATCH
        assert "Matriculation / Secondary School" in res.explanation

    # Scenario 2: Matriculation student excluded from graduate/bachelor scholarships requiring degree completion
    def test_scenario_02_matriculation_excluded_from_graduate_scholarships(self):
        user = UnifiedUserFacts(
            user_id="user_matric",
            current_education_level=EducationLevel.MATRICULATION.value,
            academic_records=[
                {
                    "degree": "Matriculation",
                    "education_level": EducationLevel.MATRICULATION.value,
                    "status": "Completed",
                }
            ],
        )
        req = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="Requires completed Bachelor's or Master's degree",
            required_value=["Bachelor's / Undergraduate", "Master's / Postgraduate"],
        )
        res = AcademicEvaluator.evaluate_degree_level(user, req)
        assert res.status == RequirementStatus.NO_MATCH

    # Scenario 3: Intermediate student (FSc/ICS) gets undergraduate entry scholarships and intermediate merit awards
    def test_scenario_03_intermediate_student_matches_awards_and_undergrad_entry(self):
        user = UnifiedUserFacts(
            user_id="user_inter",
            current_education_level=EducationLevel.INTERMEDIATE.value,
            target_degree_level=EducationLevel.BACHELORS.value,
            academic_records=[
                {
                    "degree": "Intermediate / Higher Secondary",
                    "education_level": EducationLevel.INTERMEDIATE.value,
                    "stream": "Pre-Engineering (FSc)",
                    "status": "Completed",
                }
            ],
        )
        # 3a: Intermediate merit award
        req_inter = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="Higher Secondary / Intermediate Merit Scholarship",
            required_value=["Intermediate / Higher Secondary"],
        )
        res_inter = AcademicEvaluator.evaluate_degree_level(user, req_inter)
        assert res_inter.status == RequirementStatus.MATCH

        # 3b: Undergraduate entry scholarship progression
        req_ug = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="Undergraduate Admissions Scholarship for incoming students",
            required_value=["Bachelor's / Undergraduate"],
        )
        res_ug = AcademicEvaluator.evaluate_degree_level(user, req_ug)
        assert res_ug.status == RequirementStatus.MATCH

    # Scenario 4: A-Levels student receives international undergraduate admissions scholarships
    def test_scenario_04_alevels_student_matches_international_undergrad(self):
        user = UnifiedUserFacts(
            user_id="user_alevels",
            current_education_level=EducationLevel.A_LEVELS_IB.value,
            academic_records=[
                {
                    "degree": "Cambridge A-Levels",
                    "education_level": EducationLevel.A_LEVELS_IB.value,
                    "stream": "STEM / Mathematics",
                    "status": "Completed",
                }
            ],
        )
        req = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="Undergraduate entry for A-Levels / IB Diploma holders",
            required_value=["A-Levels / IB Diploma / Equivalent", "Bachelor's / Undergraduate"],
        )
        res = AcademicEvaluator.evaluate_degree_level(user, req)
        assert res.status == RequirementStatus.MATCH

    # Scenario 5: Vocational / DAE student receives technical training grants and vocational transition scholarships
    def test_scenario_05_vocational_dae_student_matches_technical_grants(self):
        user = UnifiedUserFacts(
            user_id="user_dae",
            current_education_level=EducationLevel.VOCATIONAL.value,
            academic_records=[
                {
                    "degree": "Diploma of Associate Engineer (DAE)",
                    "education_level": EducationLevel.VOCATIONAL.value,
                    "stream": "Electrical Technology",
                    "status": "Completed",
                }
            ],
        )
        req = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="Technical and Vocational Training Grants (TVET / DAE)",
            required_value=["Certificate / Vocational Training", "Diploma / Associate Degree"],
        )
        res = AcademicEvaluator.evaluate_degree_level(user, req)
        assert res.status == RequirementStatus.MATCH

    # Scenario 6: Associate degree graduate matches completion-to-bachelor degree bridge opportunities
    def test_scenario_06_associate_degree_matches_bachelor_bridge(self):
        user = UnifiedUserFacts(
            user_id="user_associate",
            current_education_level=EducationLevel.ASSOCIATE.value,
            academic_records=[
                {
                    "degree": "Associate Degree in Computer Science (ADP)",
                    "education_level": EducationLevel.ASSOCIATE.value,
                    "status": "Completed",
                }
            ],
        )
        req = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="Degree bridge scholarship into Bachelor's program",
            required_value=["Bachelor's / Undergraduate", "Diploma / Associate Degree"],
        )
        res = AcademicEvaluator.evaluate_degree_level(user, req)
        assert res.status == RequirementStatus.MATCH

    # Scenario 7: Bachelor's graduate matches Master's scholarships and graduate fellowships
    def test_scenario_07_bachelors_graduate_matches_masters_scholarships(self):
        user = UnifiedUserFacts(
            user_id="user_bs",
            current_education_level=EducationLevel.BACHELORS.value,
            academic_records=[
                {
                    "degree": "BS Software Engineering",
                    "education_level": EducationLevel.BACHELORS.value,
                    "status": "Completed",
                }
            ],
        )
        req = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="Master's Degree Fellowship for graduates",
            required_value=["Master's / Postgraduate", "Bachelor's / Undergraduate"],
        )
        res = AcademicEvaluator.evaluate_degree_level(user, req)
        assert res.status == RequirementStatus.MATCH

    # Scenario 8: Master's graduate matches PhD fellowships and research assistantships
    def test_scenario_08_masters_graduate_matches_phd_fellowships(self):
        user = UnifiedUserFacts(
            user_id="user_ms",
            current_education_level=EducationLevel.MASTERS.value,
            academic_records=[
                {
                    "degree": "MS Computer Science",
                    "education_level": EducationLevel.MASTERS.value,
                    "status": "Completed",
                }
            ],
        )
        req = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="Doctoral Research Fellowship",
            required_value=["PhD / Doctorate"],
        )
        res = AcademicEvaluator.evaluate_degree_level(user, req)
        assert res.status == RequirementStatus.MATCH

    # Scenario 9: PhD graduate matches Postdoc fellowships
    def test_scenario_09_phd_graduate_matches_postdoc_fellowships(self):
        user = UnifiedUserFacts(
            user_id="user_phd",
            current_education_level=EducationLevel.DOCTORATE.value,
            academic_records=[
                {
                    "degree": "Doctor of Philosophy in Artificial Intelligence",
                    "education_level": EducationLevel.DOCTORATE.value,
                    "status": "Completed",
                }
            ],
        )
        req = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="Postdoctoral Research Fellowships",
            required_value=["Postdoctoral Research"],
        )
        res = AcademicEvaluator.evaluate_degree_level(user, req)
        assert res.status == RequirementStatus.MATCH

    # Scenario 10: Professional qualification holder (ACCA/CA) matches professional awards
    def test_scenario_10_professional_qualification_matches_professional_awards(self):
        user = UnifiedUserFacts(
            user_id="user_acca",
            current_education_level=EducationLevel.PROFESSIONAL.value,
            academic_records=[
                {
                    "degree": "ACCA Member / Chartered Certified Accountant",
                    "education_level": EducationLevel.PROFESSIONAL.value,
                    "status": "Completed",
                }
            ],
        )
        req = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="International Professional Development Award for Accountants",
            required_value=["Professional Qualification"],
        )
        res = AcademicEvaluator.evaluate_degree_level(user, req)
        assert res.status == RequirementStatus.MATCH

    # Scenario 11: User with No Formal Qualification matches skill-based & open opportunities
    def test_scenario_11_no_formal_qualification_matches_open_scholarships(self):
        user = UnifiedUserFacts(
            user_id="user_informal",
            current_education_level=EducationLevel.NO_FORMAL.value,
            academic_records=[
                {
                    "degree": "Self-Taught Python Developer",
                    "education_level": EducationLevel.NO_FORMAL.value,
                    "status": "Completed",
                }
            ],
        )
        req = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="Open to everyone, no formal qualifications required",
            required_value=["No Formal Qualification / Other", "Open to all"],
        )
        res = AcademicEvaluator.evaluate_degree_level(user, req)
        assert res.status == RequirementStatus.MATCH

    # Scenario 12: Multi-record profile matches both undergraduate and school-specific criteria
    def test_scenario_12_multi_record_profile_matches_across_records(self):
        user = UnifiedUserFacts(
            user_id="user_multi",
            current_education_level=EducationLevel.BACHELORS.value,
            academic_records=[
                {
                    "degree": "BS Software Engineering",
                    "education_level": EducationLevel.BACHELORS.value,
                    "institution": "FAST-NUCES",
                    "status": "Currently Studying",
                },
                {
                    "degree": "Intermediate (FSc Pre-Engineering)",
                    "education_level": EducationLevel.INTERMEDIATE.value,
                    "institution": "Government College",
                    "status": "Completed",
                },
                {
                    "degree": "Matriculation (Science)",
                    "education_level": EducationLevel.MATRICULATION.value,
                    "institution": "Army Public School",
                    "status": "Completed",
                },
            ],
        )
        # Check Intermediate scholarship match
        req_inter = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="Scholarship for Intermediate / Higher Secondary Alumni",
            required_value=["Intermediate / Higher Secondary"],
        )
        res_inter = AcademicEvaluator.evaluate_degree_level(user, req_inter)
        assert res_inter.status == RequirementStatus.MATCH

        # Check Bachelor's match
        req_bs = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="Undergraduate Student Grant",
            required_value=["Bachelor's / Undergraduate"],
        )
        res_bs = AcademicEvaluator.evaluate_degree_level(user, req_bs)
        assert res_bs.status == RequirementStatus.MATCH

    # Scenario 13: Opportunity with NO degree requirements matches ANY user level
    def test_scenario_13_no_degree_requirements_matches_any_user(self):
        user_primary = UnifiedUserFacts(
            user_id="user_prim",
            current_education_level=EducationLevel.PRIMARY.value,
        )
        req_open = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="Community Innovation Challenge open to all ages and backgrounds",
            required_value=[],
        )
        res = AcademicEvaluator.evaluate_degree_level(user_primary, req_open)
        assert res.status == RequirementStatus.MATCH
        assert "open to all" in res.explanation.lower()

    # Scenario 14: Natural progression eligibility (Completed Intermediate matches Bachelor's)
    def test_scenario_14_natural_progression_intermediate_to_bachelor(self):
        user = UnifiedUserFacts(
            user_id="user_graduated_inter",
            current_education_level=EducationLevel.INTERMEDIATE.value,
            academic_records=[
                {
                    "degree": "FSc Pre-Engineering",
                    "education_level": EducationLevel.INTERMEDIATE.value,
                    "status": "Completed",
                }
            ],
        )
        req = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="Bachelor's Degree Admissions Scholarship",
            required_value=["Bachelor's / Undergraduate"],
        )
        res = AcademicEvaluator.evaluate_degree_level(user, req)
        assert res.status == RequirementStatus.MATCH
        assert "Intermediate / Higher Secondary" in res.explanation

    # Scenario 15: Search query understanding extracts worldwide education levels correctly
    @pytest.mark.asyncio
    async def test_scenario_15_search_query_understanding_extracts_levels(self):
        service = QueryUnderstandingService()

        # 15a: Matriculation query
        q_matric = await service.analyze_intent("scholarships for matric students in Pakistan")
        assert "Matriculation / Secondary School" in q_matric.degree_levels

        # 15b: Intermediate query
        q_inter = await service.analyze_intent("scholarships after fsc pre engineering in lahore")
        assert "Intermediate / Higher Secondary" in q_inter.degree_levels

        # 15c: A-Levels query
        q_alevels = await service.analyze_intent("fully funded undergraduate scholarships for a-levels students")
        assert any(
            deg in q_alevels.degree_levels
            for deg in ["A-Levels / IB Diploma / Equivalent", "Bachelor's / Undergraduate"]
        )

        # 15d: DAE / Vocational query
        q_dae = await service.analyze_intent("technical education grants for DAE electrical graduates")
        assert any(
            deg in q_dae.degree_levels
            for deg in ["Certificate / Vocational Training", "Diploma / Associate Degree"]
        )

        # 15e: Informal / open query
        q_open = await service.analyze_intent("coding bootcamps for self-taught programmers without degree")
        assert "No Formal Qualification / Other" in q_open.degree_levels
