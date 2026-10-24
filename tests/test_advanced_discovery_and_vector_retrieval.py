import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_current_dev_user
from app.discovery.embedding.pipeline import (
    OpportunityEmbeddingPipeline,
)
from app.discovery.engine import AdvancedDiscoveryEngine
from app.discovery.evaluation.benchmark import get_default_retrieval_benchmark
from app.discovery.evaluation.evaluator import RetrievalEvaluator
from app.discovery.models import (
    FusionMethod,
    OpportunityCandidate,
    OpportunitySearchDocument,
    RetrievalFilters,
    SearchStrategy,
)
from app.discovery.query.expansion import QueryExpansionService
from app.discovery.query.rewriter import SemanticQueryRewriter
from app.discovery.retrieval.deduplication import OpportunityIdentityService
from app.discovery.retrieval.diversity import DiversityOptimizer
from app.discovery.retrieval.fusion import CandidateFusionService
from app.discovery.retrieval.metadata_filter import StructuredMetadataFilter
from app.discovery.vector_store.memory_store import InMemoryVectorStore, _cosine_similarity
from app.models.user import User, UserRole


def _create_sample_doc(
    opp_id: str,
    title: str,
    provider: str,
    category: str = "Scholarship",
    fields: list[str] | None = None,
    degree_levels: list[str] | None = None,
    funding_summary: str = "Fully Funded",
    deadline: date | None = None,
    source_type: str = "Official Website",
    tests_required: list[str] | None = None,
    has_fee: bool = False,
) -> OpportunitySearchDocument:
    return OpportunitySearchDocument(
        opportunity_id=opp_id,
        title=title,
        provider=provider,
        category=category,
        description=f"{title} provided by {provider}. Covers full tuition and stipend.",
        fields=fields or ["Computer Science", "Artificial Intelligence"],
        degree_levels=degree_levels or ["Master's"],
        funding_summary=funding_summary,
        countries=["Germany"],
        nationalities=["Global"],
        tests_required=tests_required or [],
        application_fee_required=has_fee,
        deadline=deadline or (date.today() + timedelta(days=60)),
        status="active",
        source_type=source_type,
        source_url=f"https://example.com/apply/{opp_id}",
        verified_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_vector_store_operations() -> None:
    store = InMemoryVectorStore()

    v1 = [1.0, 0.0, 0.0]
    v2 = [0.0, 1.0, 0.0]
    v3 = [0.707, 0.707, 0.0]

    await store.upsert("doc1", v1, {"title": "Doc 1"})
    await store.upsert("doc2", v2, {"title": "Doc 2"})
    await store.upsert("doc3", v3, {"title": "Doc 3"})

    assert store.count() == 3
    assert await store.get("doc1") == v1

    # Search with query close to doc1
    results = await store.search([1.0, 0.0, 0.0], limit=2)
    assert len(results) == 2
    assert results[0].document_id == "doc1"
    assert results[0].score == 1.0

    # Delete
    assert await store.delete("doc1") is True
    assert await store.get("doc1") is None
    assert store.count() == 2


def test_cosine_similarity_edge_cases() -> None:
    assert _cosine_similarity([], []) == 0.0
    assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert _cosine_similarity([1.0, 1.0], [1.0, 1.0]) == pytest.approx(1.0)
    assert _cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


def test_query_expansion_domain_and_multilingual() -> None:
    service = QueryExpansionService(max_expansions=4)

    # 1. English domain synonym expansion
    q1 = "master's scholarships in AI"
    exp1 = service.expand(q1)
    assert len(exp1) >= 2
    assert exp1[0] == q1
    assert any("msc" in e.lower() or "funding" in e.lower() for e in exp1)

    # 2. Multilingual concept expansion (Arabic)
    q2 = "منح ماجستير للطلاب"
    exp2 = service.expand(q2)
    assert len(exp2) >= 2
    assert any("scholarship" in e.lower() or "master's" in e.lower() for e in exp2)

    # 3. Multilingual concept expansion (Urdu)
    q3 = "ماسٹرز کے لیے اسکالرشپ"
    exp3 = service.expand(q3)
    assert len(exp3) >= 2
    assert any("scholarship" in e.lower() or "master's" in e.lower() for e in exp3)


def test_semantic_query_rewriter() -> None:
    rewriter = SemanticQueryRewriter()

    query = "Find me fully funded master's programs in computer science without IELTS"
    clean_q, filters = rewriter.rewrite_and_extract_filters(query)

    assert "fully funded" not in clean_q.lower() or "find me" not in clean_q.lower()
    assert filters.fully_funded_only is True
    assert filters.no_ielts_required is True
    assert "Master's" in filters.degree_levels


@pytest.mark.asyncio
async def test_metadata_hard_filters() -> None:
    filter_svc = StructuredMetadataFilter()

    today = date.today()
    doc_active = _create_sample_doc("1", "Valid MSc", "Uni A", deadline=today + timedelta(days=30))
    doc_expired = _create_sample_doc(
        "2", "Expired MSc", "Uni B", deadline=today - timedelta(days=5)
    )
    doc_ielts = _create_sample_doc("3", "MSc With IELTS", "Uni C", tests_required=["IELTS 7.0"])
    doc_fee = _create_sample_doc("4", "MSc With Fee", "Uni D", has_fee=True)

    candidates = [
        OpportunityCandidate(
            opportunity_id=d.opportunity_id,
            title=d.title,
            provider=d.provider,
            category=d.category,
            document=d,
        )
        for d in [doc_active, doc_expired, doc_ielts, doc_fee]
    ]

    # Filter 1: Exclude expired
    f1 = RetrievalFilters(exclude_expired=True, current_date=today)
    passed1 = filter_svc.apply_hard_filters(candidates, f1)
    passed_ids1 = {c.opportunity_id for c in passed1}
    assert "1" in passed_ids1
    assert "2" not in passed_ids1

    # Filter 2: No IELTS required
    f2 = RetrievalFilters(no_ielts_required=True, exclude_expired=False)
    passed2 = filter_svc.apply_hard_filters(candidates, f2)
    passed_ids2 = {c.opportunity_id for c in passed2}
    assert "3" not in passed_ids2

    # Filter 3: No Application Fee
    f3 = RetrievalFilters(no_application_fee=True, exclude_expired=False)
    passed3 = filter_svc.apply_hard_filters(candidates, f3)
    passed_ids3 = {c.opportunity_id for c in passed3}
    assert "4" not in passed_ids3


def test_candidate_fusion_rrf_and_weighted() -> None:
    doc1 = _create_sample_doc("doc-1", "Opportunity 1", "Uni A")
    doc2 = _create_sample_doc("doc-2", "Opportunity 2", "Uni B")

    c1 = OpportunityCandidate(
        opportunity_id="doc-1",
        title="Opportunity 1",
        provider="Uni A",
        category="Scholarship",
        document=doc1,
        keyword_score=0.9,
        retrieval_sources=["KEYWORD"],
    )
    c2 = OpportunityCandidate(
        opportunity_id="doc-2",
        title="Opportunity 2",
        provider="Uni B",
        category="Scholarship",
        document=doc2,
        keyword_score=0.4,
        retrieval_sources=["KEYWORD"],
    )

    c2_sem = OpportunityCandidate(
        opportunity_id="doc-2",
        title="Opportunity 2",
        provider="Uni B",
        category="Scholarship",
        document=doc2,
        semantic_score=0.95,
        retrieval_sources=["SEMANTIC"],
    )
    c1_sem = OpportunityCandidate(
        opportunity_id="doc-1",
        title="Opportunity 1",
        provider="Uni A",
        category="Scholarship",
        document=doc1,
        semantic_score=0.5,
        retrieval_sources=["SEMANTIC"],
    )

    # RRF Fusion
    fusion_rrf = CandidateFusionService(method=FusionMethod.RRF, rrf_k=60)
    fused_rrf = fusion_rrf.fuse(keyword_candidates=[c1, c2], semantic_candidates=[c2_sem, c1_sem])
    assert len(fused_rrf) == 2
    assert "KEYWORD" in fused_rrf[0].retrieval_sources
    assert "SEMANTIC" in fused_rrf[0].retrieval_sources

    # Weighted Fusion
    fusion_weighted = CandidateFusionService(
        method=FusionMethod.WEIGHTED, keyword_weight=0.5, semantic_weight=0.5
    )
    fused_weighted = fusion_weighted.fuse(
        keyword_candidates=[c1, c2], semantic_candidates=[c2_sem, c1_sem]
    )
    assert len(fused_weighted) == 2
    assert fused_weighted[0].fusion_score > 0.0


def test_opportunity_identity_deduplication() -> None:
    id_svc = OpportunityIdentityService()

    doc_uni = _create_sample_doc(
        "opp-1", "Erasmus Mundus AI", "European Commission", source_type="Official Website"
    )
    doc_uni.source_url = "https://ec.europa.eu/erasmus-ai"

    doc_agg = _create_sample_doc(
        "opp-2", "Erasmus Mundus AI", "European Commission", source_type="Aggregator"
    )
    doc_agg.source_url = "https://scholarship-directory.com/erasmus-ai"

    c1 = OpportunityCandidate(
        opportunity_id="opp-1",
        title=doc_uni.title,
        provider=doc_uni.provider,
        category="Scholarship",
        document=doc_uni,
        canonical_source_url=doc_uni.source_url,
    )
    c2 = OpportunityCandidate(
        opportunity_id="opp-2",
        title=doc_agg.title,
        provider=doc_agg.provider,
        category="Scholarship",
        document=doc_agg,
        canonical_source_url=doc_agg.source_url,
    )

    deduped = id_svc.cluster_and_deduplicate([c1, c2])
    assert len(deduped) == 1
    assert len(deduped[0].cluster_source_urls) >= 1
    assert "Official Website" in deduped[0].document.source_type


def test_diversity_optimizer() -> None:
    optimizer = DiversityOptimizer(max_per_provider=2)

    docs = [
        _create_sample_doc(f"opp-{i}", f"Program {i}", "Monopolist University") for i in range(5)
    ]
    docs.append(_create_sample_doc("opp-other", "Unique Program", "Other University"))

    candidates = [
        OpportunityCandidate(
            opportunity_id=d.opportunity_id,
            title=d.title,
            provider=d.provider,
            category="Scholarship",
            document=d,
        )
        for d in docs
    ]

    selected = optimizer.optimize(candidates, limit=3)
    assert len(selected) == 3
    mono_count = sum(1 for c in selected if c.provider == "Monopolist University")
    assert mono_count <= 2
    assert any(c.provider == "Other University" for c in selected)


@pytest.mark.asyncio
async def test_end_to_end_discovery_engine() -> None:
    vector_store = InMemoryVectorStore()
    pipeline = OpportunityEmbeddingPipeline(dimension=64)
    engine = AdvancedDiscoveryEngine(vector_store=vector_store, embedding_pipeline=pipeline)

    doc1 = _create_sample_doc(
        "opp-cs-masters-full-1",
        "Global AI Master's Scholarship",
        "TUM Munich",
        fields=["Computer Science", "Artificial Intelligence"],
        funding_summary="Fully Funded 100%",
    )
    doc2 = _create_sample_doc(
        "opp-cs-masters-full-2",
        "Software Systems Graduate Fellowship",
        "ETH Zurich",
        fields=["Computer Science"],
        funding_summary="Fully Funded",
    )
    doc3 = _create_sample_doc(
        "opp-undergrad-arts-1",
        "Undergraduate Fine Arts Grant",
        "Arts Academy",
        fields=["Fine Arts"],
        degree_levels=["Bachelor's"],
        funding_summary="Partial Tuition",
    )

    for doc in [doc1, doc2, doc3]:
        vec = await pipeline.embed_document(doc)
        await vector_store.upsert(
            doc.opportunity_id, vec, {"title": doc.title, "category": doc.category}
        )
        engine.index_document(doc)

    res = await engine.search("funded master's in AI and computer science", limit=5)
    assert res.total_candidates_found >= 1
    top_ids = [c.opportunity_id for c in res.candidates]
    assert "opp-cs-masters-full-1" in top_ids
    assert top_ids[0] != "opp-undergrad-arts-1"

    # Multilingual discovery (Arabic)
    res_ar = await engine.search("منح ماجستير حاسوب ممولة", limit=5)
    assert res_ar.total_candidates_found >= 1
    assert any("opp-cs-masters" in c.opportunity_id for c in res_ar.candidates)


@pytest.mark.asyncio
async def test_engine_graceful_degradation_on_vector_failure() -> None:
    class FailingVectorStore(InMemoryVectorStore):
        async def search(
            self,
            query_vector: list[float],
            limit: int = 100,
            filter_metadata: dict | None = None,
        ) -> list:
            raise ConnectionError("Simulated Vector DB Down")

    failing_store = FailingVectorStore()
    engine = AdvancedDiscoveryEngine(vector_store=failing_store)

    doc = _create_sample_doc("opp-fallback-1", "Robotics Research Fellowship", "MIT")
    engine.index_document(doc)

    res = await engine.search("Robotics Fellowship", strategy=SearchStrategy.HYBRID)
    assert res.total_candidates_found == 1
    assert res.candidates[0].opportunity_id == "opp-fallback-1"
    assert "KEYWORD" in res.candidates[0].retrieval_sources


@pytest.mark.asyncio
async def test_retrieval_evaluation_benchmark() -> None:
    vector_store = InMemoryVectorStore()
    pipeline = OpportunityEmbeddingPipeline(dimension=64)
    engine = AdvancedDiscoveryEngine(vector_store=vector_store, embedding_pipeline=pipeline)

    benchmark_docs = [
        _create_sample_doc(
            "opp-cs-masters-full-1",
            "Master's Scholarship in Computer Science",
            "Uni A",
            funding_summary="Fully Funded",
        ),
        _create_sample_doc(
            "opp-cs-masters-full-2",
            "Fully Funded CS Graduate Program",
            "Uni B",
            funding_summary="Fully Funded",
        ),
        _create_sample_doc(
            "opp-ai-fellowship-eu-1",
            "AI Research Fellowship in Europe",
            "EU Institute",
            fields=["Artificial Intelligence"],
        ),
        _create_sample_doc(
            "opp-no-fee-no-ielts-1",
            "Global Fellowship No IELTS No Fee",
            "Uni C",
            tests_required=[],
            has_fee=False,
        ),
        _create_sample_doc(
            "opp-se-internship-1",
            "Software Engineering Internship",
            "Tech Corp",
            category="Internship",
        ),
        _create_sample_doc(
            "opp-tech-internship-2",
            "Industrial Placement Software",
            "Inno Corp",
            category="Internship",
        ),
        _create_sample_doc(
            "opp-undergrad-arts-1",
            "Fine Arts Undergraduate",
            "Arts Uni",
            degree_levels=["Bachelor's"],
        ),
        _create_sample_doc(
            "opp-unfunded-masters-1",
            "Unfunded Master's Tuition",
            "Uni D",
            funding_summary="Self Funded",
        ),
    ]

    for d in benchmark_docs:
        vec = await pipeline.embed_document(d)
        await vector_store.upsert(d.opportunity_id, vec, {"title": d.title})
        engine.index_document(d)

    evaluator = RetrievalEvaluator(engine=engine, k=5)
    bench_items = get_default_retrieval_benchmark()

    report_hybrid = await evaluator.evaluate_strategy(SearchStrategy.HYBRID_RERANK, bench_items)
    assert report_hybrid.precision_at_k > 0.0
    assert report_hybrid.hit_rate > 0.0
    assert report_hybrid.evaluated_queries == len(bench_items)


@pytest.mark.asyncio
async def test_discovery_api_endpoints(client: AsyncClient) -> None:
    # 1. Status endpoint
    status_resp = await client.get("/api/v1/discovery/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "healthy"
    assert status_data["vector_store_healthy"] is True

    # 2. Search endpoint
    search_payload = {
        "query": "Fully funded computer science master's",
        "limit": 10,
    }
    search_resp = await client.post("/api/v1/discovery/search", json=search_payload)
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert "query" in search_data
    assert "results" in search_data
    assert "strategy" in search_data

    # 3. Setup reviewer user for restricted endpoints
    reviewer_user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
        email="reviewer_disc@example.com",
        role=UserRole.ADMIN,
        is_active=True,
    )
    if hasattr(client, "_transport") and hasattr(client._transport, "app"):
        client._transport.app.dependency_overrides[get_current_dev_user] = lambda: reviewer_user

    # 4. Retrieve diagnostics endpoint
    retrieve_payload = {
        "query": "AI scholarships in Europe",
        "limit": 5,
    }
    diag_resp = await client.post("/api/v1/discovery/retrieve", json=retrieve_payload)
    assert diag_resp.status_code == 200
    diag_data = diag_resp.json()
    assert "candidates" in diag_data
    assert "normalized_query" in diag_data

    # 5. Metrics evaluation endpoint
    metrics_resp = await client.get("/api/v1/discovery/metrics")
    assert metrics_resp.status_code == 200
    metrics_data = metrics_resp.json()
    assert "metrics_by_strategy" in metrics_data
    assert "KEYWORD" in metrics_data["metrics_by_strategy"]
    assert "SEMANTIC" in metrics_data["metrics_by_strategy"]
    assert "HYBRID_RERANK" in metrics_data["metrics_by_strategy"]
