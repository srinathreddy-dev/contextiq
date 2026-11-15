
from pathlib import Path

from app.generation.answer_service import AnswerGenerationService
from app.generation.llm_client import LLMClient
from app.generation.rag_service import RAGService
from app.ingestion.pipeline import DocumentIngestionPipeline
from app.reranking.cross_encoder_reranker import CrossEncoderReranker
from app.retrieval.hybrid_retriever import HybridRetriever


def build_rag_service(
    pdf_path: str | Path | None = None,
    answer_service: AnswerGenerationService | None = None,
    *,
    documents_directory: str | Path | None = None,
    additional_documents_directories: list[str | Path] | None = None,
    reranker: CrossEncoderReranker | None = None,
) -> RAGService:
    """Build a RAG service from a PDF or one or more PDF directories."""

    additional_directories = additional_documents_directories or []

    if pdf_path is not None and (
        documents_directory is not None or additional_directories
    ):
        raise ValueError(
            "Provide either pdf_path or document directories, not both."
        )

    if pdf_path is None and documents_directory is None and not additional_directories:
        raise ValueError(
            "A PDF path or at least one documents directory must be provided."
        )

    pipeline = DocumentIngestionPipeline()

    if pdf_path is not None:
        source_path = Path(pdf_path)

        if source_path.is_dir():
            ingested_documents = pipeline.process_directory(source_path)
        else:
            ingested_documents = [pipeline.process(source_path)]

    else:
        directories = []

        if documents_directory is not None:
            directories.append(Path(documents_directory))

        directories.extend(Path(path) for path in additional_directories)

        # Avoid processing the same directory more than once.
        unique_directories = list(
            dict.fromkeys(path.resolve() for path in directories)
        )

        ingested_documents = []

        for directory in unique_directories:
            ingested_documents.extend(
                pipeline.process_directory(directory)
            )

    all_chunks = [
        chunk
        for ingested_document in ingested_documents
        for chunk in ingested_document.chunks
    ]

    if not all_chunks:
        raise ValueError(
            "The PDF documents did not contain any searchable text."
        )

    chunk_ids = [chunk.chunk_id for chunk in all_chunks]

    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError(
            "Duplicate chunk IDs found across the document directories."
        )

    hybrid_retriever = HybridRetriever(all_chunks)
    active_reranker = reranker or CrossEncoderReranker()

    if answer_service is None:
        answer_service = AnswerGenerationService(
            llm_client=LLMClient(),
        )

    return RAGService(
        chunks=all_chunks,
        hybrid_retriever=hybrid_retriever,
        reranker=active_reranker,
        answer_service=answer_service,
    )

