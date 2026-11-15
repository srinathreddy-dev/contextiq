
from types import SimpleNamespace
from unittest.mock import Mock

import fitz
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)

from app.generation.answer_service import AnswerGenerationService
from app.generation.rag_factory import build_rag_service
from app.generation.rag_service import RAGResponse
from app.ingestion.chunker import TextChunk
from app.main import app, set_rag_service
from app.reranking.cross_encoder_reranker import RerankedResult
from app.retrieval.bm25_retriever import RetrievalResult


client = TestClient(
    app,
    headers={"X-API-Key": "test-api-key"},
)


def create_mock_openai_response(status_code: int):
    """Create a mock HTTP response for OpenAI API exceptions."""
    response = Mock()
    response.status_code = status_code
    response.headers = {}
    response.request = Mock()

    response.json.return_value = {
        "error": {"message": "Mock OpenAI API error"}
    }

    return response


def create_upload_pdf_bytes() -> bytes:
    """Create a valid one-page PDF for upload tests."""
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Employee handbook upload test document.",
    )
    content = document.tobytes()
    document.close()
    return content


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


# --------------------------------------------------
# API AUTHENTICATION
# --------------------------------------------------


def test_ask_endpoint_rejects_missing_api_key():
    unauthenticated_client = TestClient(app)

    response = unauthenticated_client.post(
        "/ask",
        json={"question": "What is the vacation policy?"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key."


def test_ask_endpoint_rejects_invalid_api_key():
    response = client.post(
        "/ask",
        json={"question": "What is the vacation policy?"},
        headers={"X-API-Key": "incorrect-api-key"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key."


def test_ask_endpoint_returns_503_when_api_key_not_configured(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.main.settings",
        SimpleNamespace(app_api_key=None),
    )

    response = client.post(
        "/ask",
        json={"question": "What is the vacation policy?"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "API authentication is not configured."
    )


# --------------------------------------------------
# QUESTION ANSWERING
# --------------------------------------------------


def test_ask_endpoint_returns_answer_and_evidence():
    chunk = TextChunk(
        text="Employees receive 15 days of paid vacation per year.",
        page_number=1,
        chunk_index=0,
        document_id="employee_handbook",
    )

    evidence = [
        RerankedResult(
            result=RetrievalResult(chunk=chunk, score=0.9),
            score=8.5,
        )
    ]

    mock_service = Mock()

    mock_service.ask.return_value = RAGResponse(
        question="How many vacation days do employees receive?",
        answer=(
            "Employees receive 15 days of paid vacation per year. "
            "[Page 1]"
        ),
        evidence=evidence,
    )

    set_rag_service(mock_service)

    try:
        response = client.post(
            "/ask",
            json={
                "question": "How many vacation days do employees receive?"
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["question"] == (
            "How many vacation days do employees receive?"
        )

        assert data["answer"] == (
            "Employees receive 15 days of paid vacation per year. "
            "[Page 1]"
        )

        assert len(data["evidence"]) == 1

        assert data["evidence"][0]["chunk_id"] == (
            "employee_handbook-page-1-chunk-0"
        )

        assert data["evidence"][0]["document_name"] == (
            "employee_handbook.pdf"
        )

    finally:
        set_rag_service(None)


def test_ask_endpoint_returns_503_when_service_is_not_configured():
    set_rag_service(None)

    response = client.post(
        "/ask",
        json={"question": "What is the vacation policy?"},
    )

    assert response.status_code == 503


def test_ask_endpoint_rejects_empty_question():
    response = client.post(
        "/ask",
        json={"question": ""},
    )

    assert response.status_code == 422


def test_ask_endpoint_handles_missing_evidence():
    mock_service = Mock()

    mock_service.ask.return_value = RAGResponse(
        question="What is the vacation policy?",
        answer="I could not find relevant information.",
        evidence=[],
    )

    set_rag_service(mock_service)

    try:
        response = client.post(
            "/ask",
            json={"question": "What is the vacation policy?"},
        )

        assert response.status_code == 200
        assert response.json()["evidence"] == []

    finally:
        set_rag_service(None)


def test_ask_endpoint_with_real_pdf_and_fake_answer_service():
    answer_service = Mock(spec=AnswerGenerationService)

    answer_service.generate_answer.return_value = (
        "Employees receive 15 days of paid vacation per year. "
        "[Page 1]"
    )

    service = build_rag_service(
        pdf_path="data/sample/employee_handbook.pdf",
        answer_service=answer_service,
    )

    set_rag_service(service)

    try:
        response = client.post(
            "/ask",
            json={
                "question": "How many vacation days do employees receive?"
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert "15 days" in data["answer"]
        assert data["evidence"]

        assert data["evidence"][0]["chunk_id"] == (
            "employee_handbook-page-1-chunk-0"
        )

        assert data["evidence"][0]["document_name"] == (
            "employee_handbook.pdf"
        )

        answer_service.generate_answer.assert_called_once()

    finally:
        set_rag_service(None)


def test_ask_endpoint_searches_multiple_pdfs():
    answer_service = Mock(spec=AnswerGenerationService)

    answer_service.generate_answer.return_value = (
        "Multi-factor authentication is required. [Page 1]"
    )

    service = build_rag_service(
        documents_directory="data/sample",
        answer_service=answer_service,
    )

    set_rag_service(service)

    try:
        response = client.post(
            "/ask",
            json={
                "question": "Is multi-factor authentication required?"
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["answer"] == (
            "Multi-factor authentication is required. [Page 1]"
        )

        assert data["evidence"]

        document_names = {
            item["document_name"]
            for item in data["evidence"]
        }

        assert "it_security_policy.pdf" in document_names

        for item in data["evidence"]:
            assert item["document_name"].endswith(".pdf")
            assert item["page_number"] >= 1
            assert item["chunk_id"]

        answer_service.generate_answer.assert_called_once()

    finally:
        set_rag_service(None)


# --------------------------------------------------
# READINESS CHECK
# --------------------------------------------------


def test_ready_endpoint_returns_ready_when_service_is_configured():
    mock_service = Mock()

    set_rag_service(mock_service)

    try:
        response = client.get("/ready")

        assert response.status_code == 200
        assert response.json() == {"status": "ready"}

    finally:
        set_rag_service(None)


def test_ready_endpoint_returns_503_when_service_is_not_configured():
    set_rag_service(None)

    response = client.get("/ready")

    assert response.status_code == 503

    assert response.json() == {
        "detail": "The knowledge service is not configured."
    }


# --------------------------------------------------
# OPENAI ERROR HANDLING
# --------------------------------------------------


def test_ask_endpoint_handles_openai_rate_limit():
    mock_service = Mock()

    error = RateLimitError(
        message="Rate limit or quota exceeded",
        response=create_mock_openai_response(429),
        body={"error": {"message": "Quota exceeded"}},
    )

    mock_service.ask.side_effect = error

    set_rag_service(mock_service)

    try:
        response = client.post(
            "/ask",
            json={
                "question": "How many vacation days do employees receive?"
            },
        )

        assert response.status_code == 503

        assert response.json()["detail"] == (
            "The AI service is temporarily unavailable. "
            "Please try again later."
        )

    finally:
        set_rag_service(None)


def test_ask_endpoint_handles_openai_timeout():
    mock_service = Mock()

    error = APITimeoutError(request=Mock())
    mock_service.ask.side_effect = error

    set_rag_service(mock_service)

    try:
        response = client.post(
            "/ask",
            json={
                "question": "How many vacation days do employees receive?"
            },
        )

        assert response.status_code == 504

        assert response.json()["detail"] == (
            "The AI service request timed out. Please try again."
        )

    finally:
        set_rag_service(None)


def test_ask_endpoint_handles_openai_connection_error():
    mock_service = Mock()

    error = APIConnectionError(request=Mock())
    mock_service.ask.side_effect = error

    set_rag_service(mock_service)

    try:
        response = client.post(
            "/ask",
            json={
                "question": "How many vacation days do employees receive?"
            },
        )

        assert response.status_code == 503

        assert response.json()["detail"] == (
            "The AI service is temporarily unreachable."
        )

    finally:
        set_rag_service(None)


def test_ask_endpoint_handles_openai_authentication_error():
    mock_service = Mock()

    error = AuthenticationError(
        message="Invalid API key",
        response=create_mock_openai_response(401),
        body={"error": {"message": "Invalid API key"}},
    )

    mock_service.ask.side_effect = error

    set_rag_service(mock_service)

    try:
        response = client.post(
            "/ask",
            json={
                "question": "How many vacation days do employees receive?"
            },
        )

        assert response.status_code == 502

        assert response.json()["detail"] == (
            "The AI service authentication is not configured correctly."
        )

    finally:
        set_rag_service(None)

def test_ask_endpoint_handles_openai_api_status_error():
    mock_service = Mock()

    error = APIStatusError(
        message="Internal server error",
        response=create_mock_openai_response(500),
        body={"error": {"message": "Internal server error"}},
    )

    mock_service.ask.side_effect = error

    set_rag_service(mock_service)

    try:
        response = client.post(
            "/ask",
            json={
                "question": "How many vacation days do employees receive?"
            },
        )

        assert response.status_code == 502

        assert response.json()["detail"] == (
            "The AI service returned an error. "
            "Please try again later."
        )

    finally:
        set_rag_service(None)


# --------------------------------------------------
# RATE LIMITING
# --------------------------------------------------


def test_rate_limit_allows_first_10_requests():
    from app.main import _request_history, enforce_rate_limit

    api_key = "rate-limit-test-key"
    _request_history.pop(api_key, None)

    for _ in range(10):
        enforce_rate_limit(api_key)


def test_rate_limit_rejects_11th_request():
    from app.main import _request_history, enforce_rate_limit

    api_key = "rate-limit-reject-test-key"
    _request_history.pop(api_key, None)

    for _ in range(10):
        enforce_rate_limit(api_key)

    with pytest.raises(HTTPException) as exc_info:
        enforce_rate_limit(api_key)

    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


def test_rate_limit_tracks_different_api_keys_separately():
    from app.main import _request_history, enforce_rate_limit

    key_one = "rate-limit-user-one"
    key_two = "rate-limit-user-two"

    _request_history.pop(key_one, None)
    _request_history.pop(key_two, None)

    for _ in range(10):
        enforce_rate_limit(key_one)

    # A different API key should have its own allowance.
    enforce_rate_limit(key_two)


# --------------------------------------------------
# DOCUMENT UPLOAD RELIABILITY
# --------------------------------------------------


def test_upload_endpoint_accepts_valid_pdf(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()

    monkeypatch.setattr("app.main.UPLOADS_DIRECTORY", uploads_dir)
    monkeypatch.setattr(
        "app.main.DOCUMENTS_DIRECTORY",
        tmp_path / "sample",
    )

    current_service = Mock()
    new_service = Mock()

    set_rag_service(current_service)

    monkeypatch.setattr(
        "app.main.build_rag_service",
        Mock(return_value=new_service),
    )

    try:
        response = client.post(
            "/documents/upload",
            files={
                "file": (
                    "employee_test.pdf",
                    create_upload_pdf_bytes(),
                    "application/pdf",
                )
            },
        )

        assert response.status_code == 201

        data = response.json()

        assert data["document"]["name"] == "employee_test.pdf"
        assert data["document"]["source"] == "uploaded"
        assert data["document"]["pages"] == 1
        assert data["document"]["size_bytes"] > 0

        assert (uploads_dir / "employee_test.pdf").exists()
        assert app.state.rag_service is new_service

    finally:
        set_rag_service(None)


def test_upload_endpoint_rejects_non_pdf_file():
    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "notes.txt",
                b"This is not a PDF.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 415


def test_upload_endpoint_rejects_oversized_file(
    tmp_path,
    monkeypatch,
):
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()

    monkeypatch.setattr("app.main.UPLOADS_DIRECTORY", uploads_dir)
    monkeypatch.setattr("app.main.MAX_UPLOAD_SIZE_BYTES", 10)

    set_rag_service(Mock())

    try:
        response = client.post(
            "/documents/upload",
            files={
                "file": (
                    "large.pdf",
                    b"x" * 11,
                    "application/pdf",
                )
            },
        )

        assert response.status_code == 413
        assert not list(uploads_dir.iterdir())

    finally:
        set_rag_service(None)


def test_upload_endpoint_rejects_invalid_pdf(
    tmp_path,
    monkeypatch,
):
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()

    monkeypatch.setattr("app.main.UPLOADS_DIRECTORY", uploads_dir)

    set_rag_service(Mock())

    try:
        response = client.post(
            "/documents/upload",
            files={
                "file": (
                    "invalid.pdf",
                    b"not a valid PDF document",
                    "application/pdf",
                )
            },
        )

        assert response.status_code == 422
        assert not list(uploads_dir.iterdir())

    finally:
        set_rag_service(None)


def test_upload_endpoint_removes_file_when_indexing_fails(
    tmp_path,
    monkeypatch,
):
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()

    monkeypatch.setattr("app.main.UPLOADS_DIRECTORY", uploads_dir)

    current_service = Mock()
    set_rag_service(current_service)

    monkeypatch.setattr(
        "app.main.build_rag_service",
        Mock(side_effect=RuntimeError("Indexing failed")),
    )

    try:
        response = client.post(
            "/documents/upload",
            files={
                "file": (
                    "failed_upload.pdf",
                    create_upload_pdf_bytes(),
                    "application/pdf",
                )
            },
        )

        assert response.status_code == 500
        assert not (uploads_dir / "failed_upload.pdf").exists()

    finally:
        set_rag_service(None)


def test_upload_endpoint_preserves_existing_service_when_indexing_fails(
    tmp_path,
    monkeypatch,
):
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()

    monkeypatch.setattr("app.main.UPLOADS_DIRECTORY", uploads_dir)

    current_service = Mock()
    set_rag_service(current_service)

    monkeypatch.setattr(
        "app.main.build_rag_service",
        Mock(side_effect=RuntimeError("Indexing failed")),
    )

    try:
        response = client.post(
            "/documents/upload",
            files={
                "file": (
                    "failed_upload.pdf",
                    create_upload_pdf_bytes(),
                    "application/pdf",
                )
            },
        )

        assert response.status_code == 500
        assert app.state.rag_service is current_service

    finally:
        set_rag_service(None)
