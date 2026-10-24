"""Unit tests for individual deterministic eligibility evaluators."""

from __future__ import annotations

from app.opportunities.eligibility.evaluators import (
    AcademicEvaluator,
    ApplicationFeeEvaluator,
    DeadlineEvaluator,
    ExperienceEvaluator,
    NationalityResidencyEvaluator,
    TestEvaluator,
)
from app.opportunities.eligibility.profile_adapter import UnifiedUserFacts
from app.opportunities.eligibility.requirement_adapter import OpportunityRequirementItem
from app.opportunities.eligibility.schemas import (
    RequirementPriority,
    RequirementStatus,
)


class TestAcademicEvaluator:
    """Tests AcademicEvaluator for CGPA, percentage, degree level, and field of study."""

    def test_evaluate_cgpa_match(self):
        user = UnifiedUserFacts(user_id="u1", highest_cgpa=3.65)
        req = OpportunityRequirementItem(
            requirement_type="cgpa",
            description="Minimum CGPA 3.0",
            operator=">=",
            required_value=3.0,
        )
        res = AcademicEvaluator.evaluate_cgpa(user, req)
        assert res.status == RequirementStatus.MATCH
        assert res.user_value == 3.65
        assert res.user_evidence is not None
        assert "3.65 >= 3.00" in res.comparison

    def test_evaluate_cgpa_no_match(self):
        user = UnifiedUserFacts(user_id="u1", highest_cgpa=2.70)
        req = OpportunityRequirementItem(
            requirement_type="cgpa",
            description="Minimum CGPA 3.2",
            operator=">=",
            required_value=3.2,
        )
        res = AcademicEvaluator.evaluate_cgpa(user, req)
        assert res.status == RequirementStatus.NO_MATCH
        assert "does not meet" in res.explanation

    def test_evaluate_cgpa_unknown_when_missing(self):
        # Strict zero-assumption: missing CGPA MUST evaluate to UNKNOWN, never NO_MATCH
        user = UnifiedUserFacts(user_id="u1", highest_cgpa=None, normalized_gpa_4_scale=None)
        req = OpportunityRequirementItem(
            requirement_type="cgpa",
            description="Minimum CGPA 3.0",
            operator=">=",
            required_value=3.0,
        )
        res = AcademicEvaluator.evaluate_cgpa(user, req)
        assert res.status == RequirementStatus.UNKNOWN
        assert res.user_value is None
        assert "not provided" in res.explanation

    def test_evaluate_cgpa_from_academic_records(self):
        user = UnifiedUserFacts(
            user_id="u1",
            academic_records=[{"degree_title": "BS CS", "cgpa": 3.82, "institution": "NUST"}],
        )
        req = OpportunityRequirementItem(
            requirement_type="cgpa",
            description="Minimum CGPA 3.5",
            operator=">=",
            required_value=3.5,
        )
        res = AcademicEvaluator.evaluate_cgpa(user, req)
        assert res.status == RequirementStatus.MATCH
        assert res.user_value == 3.82
        assert res.user_evidence.context == "NUST"

    def test_evaluate_percentage_match_and_no_match(self):
        user_match = UnifiedUserFacts(user_id="u1", highest_percentage=82.5)
        req = OpportunityRequirementItem(
            requirement_type="percentage",
            description="Minimum 75% in undergraduate studies",
            operator=">=",
            required_value=75.0,
        )
        res_match = AcademicEvaluator.evaluate_percentage(user_match, req)
        assert res_match.status == RequirementStatus.MATCH

        user_low = UnifiedUserFacts(user_id="u2", highest_percentage=68.0)
        res_low = AcademicEvaluator.evaluate_percentage(user_low, req)
        assert res_low.status == RequirementStatus.NO_MATCH

        user_missing = UnifiedUserFacts(user_id="u3", highest_percentage=None)
        res_missing = AcademicEvaluator.evaluate_percentage(user_missing, req)
        assert res_missing.status == RequirementStatus.UNKNOWN

    def test_evaluate_degree_level_matching(self):
        user = UnifiedUserFacts(
            user_id="u1",
            academic_records=[
                {
                    "degree_title": "Bachelor of Science in CS",
                    "normalized_degree_level": "Bachelor's",
                }
            ],
        )
        req = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="Requires Bachelor's degree",
            required_value=["Bachelor's"],
        )
        res = AcademicEvaluator.evaluate_degree_level(user, req)
        assert res.status == RequirementStatus.MATCH

    def test_evaluate_degree_level_no_match_and_unknown(self):
        user_high_school = UnifiedUserFacts(
            user_id="u1",
            academic_records=[
                {"degree_title": "High School Diploma", "normalized_degree_level": "High School"}
            ],
        )
        req = OpportunityRequirementItem(
            requirement_type="degree_level",
            description="Requires Master's degree",
            required_value=["Master's"],
        )
        res = AcademicEvaluator.evaluate_degree_level(user_high_school, req)
        assert res.status == RequirementStatus.NO_MATCH

        user_empty = UnifiedUserFacts(user_id="u2", academic_records=[])
        res_empty = AcademicEvaluator.evaluate_degree_level(user_empty, req)
        assert res_empty.status == RequirementStatus.UNKNOWN

    def test_evaluate_field_of_study_taxonomic_match(self):
        user = UnifiedUserFacts(
            user_id="u1",
            academic_records=[
                {
                    "field_of_study": "Software Engineering",
                    "normalized_field": "Software Engineering",
                }
            ],
        )
        req = OpportunityRequirementItem(
            requirement_type="field_of_study",
            description="Eligible fields: Computer Science, Software Engineering",
            required_value=["Computer Science", "Software Engineering"],
        )
        res = AcademicEvaluator.evaluate_field_of_study(user, req)
        assert res.status == RequirementStatus.MATCH


class TestNationalityResidencyEvaluator:
    """Tests NationalityResidencyEvaluator for strict declared nationality checks."""

    def test_nationality_exact_match(self):
        user = UnifiedUserFacts(user_id="u1", nationality="Pakistan")
        req = OpportunityRequirementItem(
            requirement_type="nationality",
            description="Open to applicants from Pakistan, India, Bangladesh",
            required_value=["Pakistan", "India", "Bangladesh"],
        )
        res = NationalityResidencyEvaluator.evaluate_nationality(user, req)
        assert res.status == RequirementStatus.MATCH
        assert res.user_value == "Pakistan"

    def test_nationality_global_open(self):
        user = UnifiedUserFacts(user_id="u1", nationality="Pakistan")
        req = OpportunityRequirementItem(
            requirement_type="nationality",
            description="Open to all international students globally",
            required_value=["Global"],
        )
        res = NationalityResidencyEvaluator.evaluate_nationality(user, req)
        assert res.status == RequirementStatus.MATCH
        assert "Global" in res.comparison

    def test_nationality_no_match(self):
        user = UnifiedUserFacts(user_id="u1", nationality="Pakistan")
        req = OpportunityRequirementItem(
            requirement_type="nationality",
            description="Open to EU citizens only",
            required_value=["Germany", "France", "Spain"],
        )
        res = NationalityResidencyEvaluator.evaluate_nationality(user, req)
        assert res.status == RequirementStatus.NO_MATCH

    def test_nationality_unknown_when_not_declared(self):
        # Must NEVER hallucinate or infer nationality from IP / location
        user = UnifiedUserFacts(user_id="u1", nationality=None)
        req = OpportunityRequirementItem(
            requirement_type="nationality",
            description="Open to citizens of Germany only",
            required_value=["Germany"],
        )
        res = NationalityResidencyEvaluator.evaluate_nationality(user, req)
        assert res.status == RequirementStatus.UNKNOWN
        assert "not declared" in res.explanation


class TestTestEvaluator:
    """Tests TestEvaluator with numeric comparisons and English-medium degree waivers."""

    def test_ielts_score_match(self):
        user = UnifiedUserFacts(
            user_id="u1",
            tests={"IELTS": {"score": "7.5", "test_date": "2025-06-10"}},
        )
        req = OpportunityRequirementItem(
            requirement_type="ielts",
            description="IELTS minimum 6.5",
            operator=">=",
            required_value=6.5,
        )
        res = TestEvaluator.evaluate_test(user, req)
        assert res.status == RequirementStatus.MATCH
        assert res.user_value == 7.5

    def test_ielts_score_no_match(self):
        user = UnifiedUserFacts(
            user_id="u1",
            tests={"IELTS": {"score": "6.0", "test_date": "2025-06-10"}},
        )
        req = OpportunityRequirementItem(
            requirement_type="ielts",
            description="IELTS minimum 7.0",
            operator=">=",
            required_value=7.0,
        )
        res = TestEvaluator.evaluate_test(user, req)
        assert res.status == RequirementStatus.NO_MATCH

    def test_ielts_missing_without_waiver_is_unknown(self):
        user = UnifiedUserFacts(user_id="u1", tests={})
        req = OpportunityRequirementItem(
            requirement_type="ielts",
            description="IELTS minimum 6.5",
            operator=">=",
            required_value=6.5,
            waiver_allowed=False,
        )
        res = TestEvaluator.evaluate_test(user, req)
        assert res.status == RequirementStatus.UNKNOWN

    def test_ielts_missing_with_verified_emi_waiver(self):
        # Scenario D: User has no IELTS test, but has verified English-medium degree
        user = UnifiedUserFacts(
            user_id="u1",
            tests={},
            has_english_medium_degree=True,
        )
        req = OpportunityRequirementItem(
            requirement_type="ielts",
            description="IELTS minimum 6.5 (waivers allowed for English-instructed degrees)",
            operator=">=",
            required_value=6.5,
            waiver_allowed=True,
        )
        res = TestEvaluator.evaluate_test(user, req)
        assert res.status == RequirementStatus.MATCH
        assert "waived" in res.explanation.lower()
        assert res.user_evidence is not None

    def test_ielts_missing_with_unverified_waiver_is_conditional(self):
        # Opportunity allows waiver, but user profile does NOT declare EMI
        user = UnifiedUserFacts(
            user_id="u1",
            tests={},
            has_english_medium_degree=False,
        )
        req = OpportunityRequirementItem(
            requirement_type="ielts",
            description="IELTS minimum 6.5 (waiver allowed)",
            operator=">=",
            required_value=6.5,
            waiver_allowed=True,
        )
        res = TestEvaluator.evaluate_test(user, req)
        assert res.status == RequirementStatus.CONDITIONAL
        assert res.requires_verification is True
        assert "waiver" in res.explanation.lower()


class TestDeadlineAndExperienceEvaluator:
    """Tests DeadlineEvaluator and ExperienceEvaluator."""

    def test_deadline_rolling_is_match(self):
        user = UnifiedUserFacts(user_id="u1")
        req = OpportunityRequirementItem(
            requirement_type="deadline",
            description="Rolling admissions",
            required_value="ROLLING",
        )
        res = DeadlineEvaluator.evaluate_deadline(user, req)
        assert res.status == RequirementStatus.MATCH
        assert "rolling" in res.explanation.lower()

    def test_deadline_future_is_match(self):
        user = UnifiedUserFacts(user_id="u1")
        req = OpportunityRequirementItem(
            requirement_type="deadline",
            description="Application deadline",
            required_value="2099-12-31",
        )
        res = DeadlineEvaluator.evaluate_deadline(user, req)
        assert res.status == RequirementStatus.MATCH

    def test_deadline_past_is_no_match(self):
        user = UnifiedUserFacts(user_id="u1")
        req = OpportunityRequirementItem(
            requirement_type="deadline",
            description="Application deadline",
            required_value="2020-01-01",
        )
        res = DeadlineEvaluator.evaluate_deadline(user, req)
        assert res.status == RequirementStatus.NO_MATCH

    def test_experience_evaluator_match_and_no_match(self):
        user_exp = UnifiedUserFacts(user_id="u1", work_experience_years=3.0)
        req = OpportunityRequirementItem(
            requirement_type="work_experience",
            description="Minimum 2 years of work experience",
            operator=">=",
            required_value=2.0,
        )
        res_match = ExperienceEvaluator.evaluate_experience(user_exp, req)
        assert res_match.status == RequirementStatus.MATCH

        user_junior = UnifiedUserFacts(user_id="u2", work_experience_years=1.0)
        res_junior = ExperienceEvaluator.evaluate_experience(user_junior, req)
        assert res_junior.status == RequirementStatus.NO_MATCH

    def test_fee_evaluator(self):
        user = UnifiedUserFacts(user_id="u1")
        req_free = OpportunityRequirementItem(
            requirement_type="application_fee",
            description="Free application",
            required_value="NO_FEE",
            priority=RequirementPriority.INFORMATIONAL,
        )
        res_free = ApplicationFeeEvaluator.evaluate_fee(user, req_free)
        assert res_free.status == RequirementStatus.MATCH
        assert "no application fee" in res_free.explanation.lower()
