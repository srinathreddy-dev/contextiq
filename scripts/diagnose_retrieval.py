
from pathlib import Path

from app.evaluation.dataset import EVALUATION_QUERIES
from app.evaluation.offline_embedder import OfflineEmbedder
from app.evaluation.retrieval_evaluator import RetrievalEvaluator
from app.ingestion.pipeline import DocumentIngestionPipeline


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIRECTORY = PROJECT_ROOT / "data" / "sample"

TOP_K = 5
CANDIDATE_K = 10
STRATEGY = "hybrid_reranked"


def main() -> None:
    print("=" * 100)
    print("ENTERPRISE AI KNOWLEDGE PLATFORM")
    print("PER-QUERY RETRIEVAL DIAGNOSTICS")
    print("=" * 100)

    print("\nLoading evaluation documents...")

    documents = DocumentIngestionPipeline().process_directory(
        DATA_DIRECTORY
    )

    chunks = [
        chunk
        for document in documents
        for chunk in document.chunks
    ]

    available_chunk_ids = {
        chunk.chunk_id for chunk in chunks
    }

    missing_ids = {
        chunk_id
        for query in EVALUATION_QUERIES
        for chunk_id in query.relevant_chunk_ids
        if chunk_id not in available_chunk_ids
    }

    if missing_ids:
        raise ValueError(
            f"Evaluation labels reference missing chunks: {missing_ids}"
        )

    print(f"Documents loaded: {len(documents)}")
    print(f"Chunks loaded: {len(chunks)}")
    print(f"Evaluation questions: {len(EVALUATION_QUERIES)}")
    print("Embedding mode: Local feature hashing")
    print("External API calls: None")
    print(f"Retrieval strategy: {STRATEGY}")
    print(f"Retrieval depth: {TOP_K}")
    print(f"Candidate depth: {CANDIDATE_K}")

    print("\nInitializing retrieval evaluator...")

    evaluator = RetrievalEvaluator(
        chunks=chunks,
        evaluation_queries=EVALUATION_QUERIES,
        embedder=OfflineEmbedder(),
    )

    diagnostics = evaluator.diagnose(
        strategy=STRATEGY,
        k=TOP_K,
        candidate_k=CANDIDATE_K,
    )

    first_result_hits = 0
    fully_retrieved_queries = 0
    total_relevant = 0
    total_retrieved_relevant = 0
    total_missed = 0
    first_relevant_ranks = []

    print("\n" + "=" * 100)
    print("INDIVIDUAL QUERY RESULTS")
    print("=" * 100)

    for index, diagnostic in enumerate(diagnostics, start=1):
        relevant_ids = diagnostic.relevant_chunk_ids
        retrieved_ids = diagnostic.retrieved_chunk_ids
        missed_ids = diagnostic.missed_relevant_chunk_ids

        retrieved_relevant_ids = relevant_ids - missed_ids

        if diagnostic.first_result_relevant:
            first_result_hits += 1

        if not missed_ids:
            fully_retrieved_queries += 1

        total_relevant += len(relevant_ids)
        total_retrieved_relevant += len(retrieved_relevant_ids)
        total_missed += len(missed_ids)

        if diagnostic.first_relevant_rank is not None:
            first_relevant_ranks.append(
                diagnostic.first_relevant_rank
            )

        print(f"\nQUERY {index}: {diagnostic.query}")
        print("-" * 100)

        print(
            f"First result relevant: "
            f"{diagnostic.first_result_relevant}"
        )
        print(
            f"First relevant rank: "
            f"{diagnostic.first_relevant_rank}"
        )

        print("\nRETRIEVED RESULTS:")

        if retrieved_ids:
            for rank, chunk_id in enumerate(retrieved_ids, start=1):
                relevant = chunk_id in relevant_ids
                print(
                    f"  {rank}. {chunk_id} "
                    f"| Relevant: {relevant}"
                )
        else:
            print("  No results returned.")

        print("\nRELEVANT CHUNKS FOUND:")
        if retrieved_relevant_ids:
            for chunk_id in sorted(retrieved_relevant_ids):
                print(f"  FOUND: {chunk_id}")
        else:
            print("  None")

        print("\nRELEVANT CHUNKS MISSED:")
        if missed_ids:
            for chunk_id in sorted(missed_ids):
                print(f"  MISSED: {chunk_id}")
        else:
            print("  None")

    query_count = len(diagnostics)

    average_first_relevant_rank = (
        sum(first_relevant_ranks) / len(first_relevant_ranks)
        if first_relevant_ranks
        else 0.0
    )

    print("\n" + "=" * 100)
    print("OVERALL DIAGNOSTIC SUMMARY")
    print("=" * 100)

    print(f"Total queries: {query_count}")
    print(
        f"First result relevant: "
        f"{first_result_hits}/{query_count}"
    )
    print(
        f"Queries retrieving all relevant chunks: "
        f"{fully_retrieved_queries}/{query_count}"
    )
    print(f"Total relevant chunk labels: {total_relevant}")
    print(f"Relevant chunks retrieved: {total_retrieved_relevant}")
    print(f"Relevant chunks missed: {total_missed}")
    print(
        f"Average first relevant rank: "
        f"{average_first_relevant_rank:.2f}"
    )

    overall_recall = (
        total_retrieved_relevant / total_relevant
        if total_relevant
        else 0.0
    )

    print(f"Aggregate relevant-chunk recall: {overall_recall:.3f}")

    print("\nIMPORTANT:")
    print("- Results use local feature-hashing embeddings.")
    print("- No external API calls are made.")
    print("- The reranker is a lexical heuristic.")
    print("- These results are offline diagnostics, not production metrics.")

    print("\nDiagnostic completed successfully.")
    print("=" * 100)


if __name__ == "__main__":
    main()
