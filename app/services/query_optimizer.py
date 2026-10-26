from app.ai.query.intent_schemas import SearchIntent, TestRequirementType
from app.schemas.ai_profile import NormalizedAIProfile
from app.schemas.search_context import SearchQuery


class QueryOptimizer:
    """Generates structured, diverse search queries from search intent and profile context."""

    @classmethod
    def optimize_queries(
        cls,
        intent: SearchIntent,
        profile: NormalizedAIProfile | None = None,
    ) -> list[SearchQuery]:
        queries: list[SearchQuery] = []

        # If informational, generate factual search query
        if not intent.is_search_intent:
            queries.append(
                SearchQuery(
                    query=f'"{intent.original_query.strip(" ?.")}" official portal requirements',
                    purpose="factual_information_lookup",
                    priority=1,
                    source_type="official_portal",
                    required_constraints=[intent.original_query],
                    excluded_terms=[],
                )
            )
            return queries

        # Base terms
        categories = intent.opportunity_categories or ["opportunities"]
        cat_term = categories[0].lower() if categories else "scholarship"

        degree_terms = intent.degree_levels or []
        deg_str = " ".join(degree_terms) if degree_terms else ""

        loc_terms = intent.countries or intent.regions or []
        loc_str = " ".join(loc_terms) if loc_terms else ""

        field_terms = intent.fields or []
        field_str = " ".join(field_terms) if field_terms else ""

        funding_full = any(fc.is_fully_funded for fc in intent.funding_constraints)
        funding_str = "fully funded" if funding_full else ""

        # 1. Primary Direct Constraint Query
        parts_p1 = [p for p in [funding_str, deg_str, field_str, loc_str, cat_term] if p]
        p1_query = " ".join(parts_p1)
        if not p1_query:
            p1_query = intent.original_query

        # Excluded terms to reduce noise
        excluded: list[str] = ["expired", "closed"]
        if any("master" in d.lower() for d in degree_terms):
            excluded.extend(["bachelor", "undergraduate"])
        elif any("bachelor" in d.lower() for d in degree_terms):
            excluded.extend(["master", "phd", "doctorate"])

        # Incorporate user excluded countries from profile
        discovery_mode = "flexible"
        if profile and hasattr(profile, "matching_signals"):
            discovery_mode = profile.matching_signals.get("discovery_mode", "flexible")
            profile_excluded = profile.matching_signals.get("excluded_countries", [])
            for exc in profile_excluded:
                if exc and exc.lower() not in excluded:
                    excluded.append(exc.lower())

        queries.append(
            SearchQuery(
                query=p1_query,
                purpose="direct_constraint_search",
                priority=1,
                source_type="general_web",
                required_constraints=[p for p in [deg_str, loc_str, cat_term] if p],
                excluded_terms=excluded,
            )
        )

        # 2. Test-Specific Query (e.g. "without IELTS" / "no GRE")
        for tc in intent.language_test_constraints:
            if tc.requirement_type == TestRequirementType.NOT_REQUIRED:
                test_term = (
                    f'("without {tc.test_name}" OR "{tc.test_name} not required" '
                    f'OR "{tc.test_name} exempt")'
                )
                p2_parts = [
                    p for p in [funding_str, deg_str, field_str, loc_str, cat_term, test_term] if p
                ]
                queries.append(
                    SearchQuery(
                        query=" ".join(p2_parts),
                        purpose=f"no_{tc.test_name.lower()}_targeted_search",
                        priority=2,
                        source_type="general_web",
                        required_constraints=[tc.test_name, "exempt/not required"],
                        excluded_terms=excluded,
                    )
                )

        # 3. Country / Portal Specific Query
        if "Germany" in (intent.countries or []):
            queries.append(
                SearchQuery(
                    query=f"DAAD scholarship {deg_str} {field_str} Germany international students",
                    purpose="official_portal_search",
                    priority=2,
                    source_type="official_portal",
                    required_constraints=["DAAD", "Germany"],
                    excluded_terms=excluded,
                )
            )
        elif "Europe" in (intent.regions or []):
            queries.append(
                SearchQuery(
                    query=f"Erasmus Mundus {deg_str} scholarship Europe {field_str}",
                    purpose="official_portal_search",
                    priority=2,
                    source_type="official_portal",
                    required_constraints=["Erasmus Mundus", "Europe"],
                    excluded_terms=excluded,
                )
            )

        # Worldwide & Global Discovery Planner Queries
        if discovery_mode == "worldwide" or not loc_terms or any(l.lower() in ("worldwide", "global") for l in loc_terms):
            global_parts = [p for p in [funding_str, deg_str, field_str, "scholarships international students worldwide"] if p]
            queries.append(
                SearchQuery(
                    query=" ".join(global_parts),
                    purpose="worldwide_open_applicant_search",
                    priority=2,
                    source_type="official_portal",
                    required_constraints=["worldwide", cat_term],
                    excluded_terms=excluded,
                )
            )
            remote_parts = [p for p in ["global remote", cat_term, field_str, "international applicants"] if p]
            queries.append(
                SearchQuery(
                    query=" ".join(remote_parts),
                    purpose="global_remote_opportunity_search",
                    priority=3,
                    source_type="general_web",
                    required_constraints=["global remote"],
                    excluded_terms=excluded,
                )
            )

        # 4. Profile-Enriched Query (if user has profile details and query was broad)
        if profile and profile.identity_context.nationality:
            nat = profile.identity_context.nationality
            # Don't add nationality if already in query
            if nat.lower() not in intent.original_query.lower():
                p_parts = [
                    p
                    for p in [
                        funding_str,
                        deg_str,
                        field_str,
                        loc_str,
                        cat_term,
                        f"for {nat} students",
                    ]
                    if p
                ]
                queries.append(
                    SearchQuery(
                        query=" ".join(p_parts),
                        purpose="nationality_eligible_search",
                        priority=3,
                        source_type="general_web",
                        required_constraints=[nat],
                        excluded_terms=excluded,
                    )
                )

        return queries
