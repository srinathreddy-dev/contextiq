
from pathlib import Path

import pytest

from app.evaluation.retrieval_evaluator import RetrievalEvaluator
from app.evaluation.retrieval_metrics import EvaluationQuery
from app.ingestion.pipeline import DocumentIngestionPipeline


@pytest.fixture
def sample_chunks():
    """Load the same sample documents used by the retrieval benchmark."""

    documents = DocumentIngestionPipeline().process_directory(
        Path("data/sample")
    )

    return [
        chunk
        for document in documents
        for chunk in document.chunks
    ]


def assert_valid_metrics(evaluation):
    """Verify that all retrieval metrics are between 0 and 1."""

    metrics = [
        evaluation.recall_at_1,
        evaluation.recall_at_3,
        evaluation.recall_at_5,
        evaluation.precision_at_1,
        evaluation.precision_at_3,
        evaluation.precision_at_5,
        evaluation.mean_reciprocal_rank,
    ]

    for metric in metrics:
        assert 0.0 <= metric <= 1.0


def test_evaluator_runs_bm25(sample_chunks):
    evaluator = RetrievalEvaluator(chunks=sample_chunks)
    evaluation = evaluator.evaluate_bm25(k=5)
    assert_valid_metrics(evaluation)


def test_evaluator_runs_semantic(sample_chunks):
    evaluator = RetrievalEvaluator(chunks=sample_chunks)
    evaluation = evaluator.evaluate_semantic(k=5)
    assert_valid_metrics(evaluation)


def test_evaluator_runs_hybrid(sample_chunks):
    evaluator = RetrievalEvaluator(chunks=sample_chunks)
    evaluation = evaluator.evaluate_hybrid(k=5)
    assert_valid_metrics(evaluation)


def test_evaluator_runs_weighted_rrf(sample_chunks):
    evaluator = RetrievalEvaluator(chunks=sample_chunks)

    evaluation = evaluator.evaluate_weighted_rrf(
        k=5,
        bm25_weight=0.70,
        semantic_weight=0.30,
    )

    assert_valid_metrics(evaluation)


def test_evaluator_accepts_custom_evaluation_queries(sample_chunks):
    custom_queries = [
        EvaluationQuery(
            query="How many vacation days do employees receive?",
            relevant_chunk_ids={
                "employee_handbook-page-1-chunk-0"
            },
        )
    ]

    evaluator = RetrievalEvaluator(
        chunks=sample_chunks,
        evaluation_queries=custom_queries,
    )

    evaluation = evaluator.evaluate_bm25(k=1)

    assert evaluation.recall_at_1 == 1.0
    assert evaluation.recall_at_3 == 1.0
    assert evaluation.recall_at_5 == 1.0

    assert evaluation.precision_at_1 == 1.0
    assert evaluation.precision_at_3 == pytest.approx(1 / 3)
    assert evaluation.precision_at_5 == pytest.approx(1 / 5)

    assert evaluation.mean_reciprocal_rank == 1.0


def test_evaluator_runs_hybrid_with_reranking(sample_chunks):
    evaluator = RetrievalEvaluator(chunks=sample_chunks)

    evaluation = evaluator.evaluate_hybrid_with_reranking(
        k=5,
        candidate_k=10,
    )

    assert_valid_metrics(evaluation)


def test_evaluator_rejects_invalid_candidate_k(sample_chunks):
    evaluator = RetrievalEvaluator(chunks=sample_chunks)

    with pytest.raises(ValueError):
        evaluator.evaluate_hybrid_with_reranking(
            k=5,
            candidate_k=0,
        )


# ---------------------------------------------------------
# Candidate Recall@10 tests
# ---------------------------------------------------------


def test_evaluator_runs_candidate_recall(sample_chunks):
    evaluator = RetrievalEvaluator(chunks=sample_chunks)

    candidate_recall = evaluator.evaluate_candidate_recall(
        candidate_k=10,
    )

    assert 0.0 <= candidate_recall <= 1.0


def test_candidate_recall_rejects_invalid_candidate_k(sample_chunks):
    evaluator = RetrievalEvaluator(chunks=sample_chunks)

    with pytest.raises(ValueError):
        evaluator.evaluate_candidate_recall(
            candidate_k=0,
        )


def test_candidate_recall_returns_zero_without_queries(sample_chunks):
    evaluator = RetrievalEvaluator(
        chunks=sample_chunks,
        evaluation_queries=[],
    )

    candidate_recall = evaluator.evaluate_candidate_recall(
        candidate_k=10,
    )

    assert candidate_recall == 0.0


# ---------------------------------------------------------
# Per-query diagnostic tests
# ---------------------------------------------------------


def test_diagnose_returns_per_query_results(sample_chunks):
    custom_queries = [
        EvaluationQuery(
            query="How many vacation days do employees receive?",
            relevant_chunk_ids={
                "employee_handbook-page-1-chunk-0"
            },
        )
    ]

    evaluator = RetrievalEvaluator(
        chunks=sample_chunks,
        evaluation_queries=custom_queries,
    )

    diagnostics = evaluator.diagnose(
        strategy="bm25",
        k=3,
        candidate_k=10,
    )

    assert len(diagnostics) == 1

    diagnostic = diagnostics[0]

    assert diagnostic.query == custom_queries[0].query

    assert diagnostic.relevant_chunk_ids == {
        "employee_handbook-page-1-chunk-0"
    }

    assert isinstance(diagnostic.retrieved_chunk_ids, list)
    assert len(diagnostic.retrieved_chunk_ids) <= 3

    assert isinstance(diagnostic.first_result_relevant, bool)

    assert isinstance(
        diagnostic.missed_relevant_chunk_ids,
        set,
    )

    assert (
        diagnostic.first_relevant_rank is None
        or diagnostic.first_relevant_rank >= 1
    )


def test_diagnose_identifies_missed_relevant_chunks(sample_chunks):
    custom_queries = [
        EvaluationQuery(
            query="How many vacation days do employees receive?",
            relevant_chunk_ids={
                "employee_handbook-page-1-chunk-0",
                "nonexistent-relevant-chunk",
            },
        )
    ]

    evaluator = RetrievalEvaluator(
        chunks=sample_chunks,
        evaluation_queries=custom_queries,
    )

    diagnostics = evaluator.diagnose(
        strategy="bm25",
        k=3,
        candidate_k=10,
    )

    diagnostic = diagnostics[0]

    assert (
        "nonexistent-relevant-chunk"
        in diagnostic.missed_relevant_chunk_ids
    )


def test_diagnose_rejects_unsupported_strategy(sample_chunks):
    evaluator = RetrievalEvaluator(chunks=sample_chunks)

    with pytest.raises(ValueError, match="Unsupported retrieval strategy"):
        evaluator.diagnose(
            strategy="unsupported",
            k=5,
            candidate_k=10,
        )

