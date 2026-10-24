"""Personalized Opportunity Ranking & Recommendation Engine coordinating discovery."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from app.opportunities.eligibility.profile_adapter import ProfileAdapter, UnifiedUserFacts
from app.opportunities.eligibility.schemas import EligibilityResult, OverallEligibilityStatus
from app.opportunities.ranking.confidence import RecommendationConfidenceCalculator
from app.opportunities.ranking.deduplication import CandidateDeduplicator
from app.opportunities.ranking.diversity import DiversityOptimizer
from app.opportunities.ranking.explanations import RankingExplanationBuilder
from app.opportunities.ranking.factors import (
    AcademicFitCalculator,
    DeadlineRelevanceCalculator,
    DegreeLevelFitCalculator,
    EligibilityCompletenessCalculator,
    FieldFitCalculator,
    FundingFitCalculator,
    LocationFitCalculator,
    QueryRelevanceCalculator,
    SourceQualityCalculator,
    get_opp_deadline,
    get_opp_funding_type,
    get_opp_host_country,
    get_opp_last_verified,
    get_opp_org,
    get_opp_title,
    get_opp_trust_score,
)
from app.opportunities.ranking.freshness import FreshnessCalculator
from app.opportunities.ranking.rules import HardFilterEngine, SoftPreferenceEngine
from app.opportunities.ranking.schemas import (
    OpportunityRankingContext,
    PreferencePriority,
    RankedOpportunity,
    RankedOpportunityResult,
    RankingFactorDetail,
    RankingFactorType,
)
from app.opportunities.ranking.scoring import ScoringEngine
from app.opportunities.ranking.validators import RankingGuardrails
from app.opportunities.ranking.weights import RankingWeightsConfig


class PersonalizedRankingEngine:
    """Production-grade transparent, personalized opportunity ranking engine."""

    ENGINE_VERSION = "1.0.0"

    def __init__(self, weights_config: RankingWeightsConfig | None = None):
        self.weights_config = weights_config or RankingWeightsConfig()

    def rank(self, context: OpportunityRankingContext) -> RankedOpportunityResult:
        """Executes transparent, multi-dimensional ranking across opportunity candidates."""
        # 1. Resolve user facts
        user_facts: UnifiedUserFacts | None = context.user_facts
        if user_facts is None and context.normalized_profile is not None:
            user_facts = ProfileAdapter.adapt(context.normalized_profile)

        # 2. Canonical Deduplication of Candidates
        raw_candidates = context.opportunities
        deduped_candidates = CandidateDeduplicator.deduplicate(raw_candidates)

        total_evaluated = len(deduped_candidates)
        filtered_out_count = 0

        weights = self.weights_config
        ranked_candidates: list[RankedOpportunity] = []

        # 3. Evaluate each candidate
        for opp in deduped_candidates:
            cand_key = CandidateDeduplicator.get_candidate_key(opp)
            cand_id = getattr(opp, "id", None) or cand_key

            # Find matching eligibility result if provided
            elig: EligibilityResult | None = (
                context.eligibility_results.get(str(cand_id))
                or context.eligibility_results.get(cand_key)
                or context.eligibility_results.get(get_opp_title(opp).lower().strip())
            )

            # Hard Filter Check
            filter_eval = HardFilterEngine.evaluate(
                opp=opp,
                preferences=context.preferences,
                eligibility=elig,
                include_ineligible=context.include_ineligible,
            )

            if not filter_eval.passed:
                filtered_out_count += 1
                continue

            # Calculate individual factor dimensions
            academic_fac = AcademicFitCalculator.calculate(opp, user_facts, elig)
            field_fac = FieldFitCalculator.calculate(opp, user_facts, context.preferences)
            funding_fac = FundingFitCalculator.calculate(opp, context.preferences)
            location_fac = LocationFitCalculator.calculate(opp, context.preferences)
            degree_fac = DegreeLevelFitCalculator.calculate(opp, user_facts, context.preferences)
            deadline_fac = DeadlineRelevanceCalculator.calculate(opp)

            freshness_eval = FreshnessCalculator.calculate(get_opp_last_verified(opp))
            freshness_fac = RankingFactorDetail(
                factor_type=RankingFactorType.FRESHNESS,
                score=freshness_eval.score,
                status="HIGH"
                if freshness_eval.is_fresh
                else ("LOW" if freshness_eval.is_stale else "MEDIUM"),
                reason=freshness_eval.summary,
            )

            source_fac = SourceQualityCalculator.calculate(opp)
            query_fac = QueryRelevanceCalculator.calculate(opp, context.search_intent)
            elig_completeness_fac = EligibilityCompletenessCalculator.calculate(elig)

            factors_map: dict[RankingFactorType, RankingFactorDetail] = {
                RankingFactorType.ACADEMIC_FIT: academic_fac,
                RankingFactorType.FIELD_FIT: field_fac,
                RankingFactorType.FUNDING_FIT: funding_fac,
                RankingFactorType.LOCATION_FIT: location_fac,
                RankingFactorType.DEGREE_LEVEL_FIT: degree_fac,
                RankingFactorType.DEADLINE_RELEVANCE: deadline_fac,
                RankingFactorType.FRESHNESS: freshness_fac,
                RankingFactorType.SOURCE_QUALITY: source_fac,
                RankingFactorType.QUERY_RELEVANCE: query_fac,
                RankingFactorType.ELIGIBILITY_COMPLETENESS: elig_completeness_fac,
            }

            # Apply Soft Preference Boosts where applicable
            for pref in context.preferences:
                if pref.priority in (
                    PreferencePriority.HIGH,
                    PreferencePriority.MEDIUM,
                    PreferencePriority.LOW,
                ):
                    multiplier = SoftPreferenceEngine.get_boost_multiplier(pref.priority)
                    cat = pref.category.upper()
                    if cat == "FUNDING" and funding_fac.score >= 0.8:
                        funding_fac.score = min(1.0, funding_fac.score * multiplier)
                    elif cat in ("LOCATION", "COUNTRY") and location_fac.score >= 0.8:
                        location_fac.score = min(1.0, location_fac.score * multiplier)
                    elif cat in ("DEGREE_LEVEL", "DEGREE") and degree_fac.score >= 0.8:
                        degree_fac.score = min(1.0, degree_fac.score * multiplier)

            # Compute combined normalized relevance score
            relevance_score = ScoringEngine.calculate_relevance(factors_map, weights)

            # Determine recommendation confidence
            confidence_tier, _ = RecommendationConfidenceCalculator.calculate(
                eligibility_result=elig,
                source_trust_score=get_opp_trust_score(opp),
                user_facts=user_facts,
            )

            # Build transparent explanations
            (
                fit_summary,
                pos_factors,
                neg_factors,
                unk_factors,
                structured_notes,
            ) = RankingExplanationBuilder.build_explanations(
                opp=opp,
                factors=factors_map,
                eligibility=elig,
                user_facts=user_facts,
            )

            # Derive overall eligibility state
            overall_elig = (
                elig.overall_status if elig else OverallEligibilityStatus.POTENTIALLY_ELIGIBLE
            )

            # Format deadline string
            dl_obj = get_opp_deadline(opp)
            deadline_str = str(dl_obj) if dl_obj else None

            ranked_opp = RankedOpportunity(
                opportunity_id=str(cand_id),
                canonical_key=cand_key,
                title=get_opp_title(opp),
                organization=get_opp_org(opp),
                rank=1,
                relevance_score=relevance_score,
                eligibility_status=overall_elig,
                fit_summary=fit_summary,
                ranking_factors={k.value: v for k, v in factors_map.items()},
                positive_factors=pos_factors,
                negative_factors=neg_factors,
                unknown_factors=unk_factors,
                confidence=confidence_tier,
                freshness=freshness_eval.score,
                explanations=structured_notes,
                deadline=deadline_str,
                funding_type=get_opp_funding_type(opp),
                host_country=get_opp_host_country(opp),
                opportunity=opp if hasattr(opp, "created_at") else None,
            )

            # Run safety and integrity guardrails
            RankingGuardrails.validate_ranked_opportunity(ranked_opp, elig)
            ranked_candidates.append(ranked_opp)

        # 4. Sort candidates according to SortMode
        ranked_candidates.sort(key=lambda item: ScoringEngine.get_sort_key(item, context.sort_mode))

        # 5. Apply Diversity Optimizer
        diversified_candidates = DiversityOptimizer.optimize(ranked_candidates)

        # 6. Generate deterministic cache key
        config_hash = weights.version_hash()
        cache_seed = (
            f"{self.ENGINE_VERSION}::{config_hash}::{context.sort_mode}::"
            f"{[r.canonical_key for r in diversified_candidates]}"
        )
        cache_key = hashlib.sha256(cache_seed.encode("utf-8")).hexdigest()[:16]

        return RankedOpportunityResult(
            opportunities=diversified_candidates,
            total_evaluated=total_evaluated,
            filtered_out_count=filtered_out_count,
            sort_mode=context.sort_mode,
            engine_version=self.ENGINE_VERSION,
            config_version=config_hash,
            cache_key=cache_key,
            created_at=datetime.now(UTC),
        )
