
import logging
import re
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock

import pymupdf
from fastapi import (
    FastAPI,
    File,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import Response
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging_config import configure_logging
from app.core.metrics import (
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
)
from app.generation.rag_factory import build_rag_service
from app.generation.rag_service import RAGService


configure_logging()
logger = logging.getLogger(__name__)

DOCUMENTS_DIRECTORY = Path("data/sample")
UPLOADS_DIRECTORY = Path("data/uploads")

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024

# --------------------------------------------------
# RATE LIMITING CONFIGURATION
# --------------------------------------------------

RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60

_request_history = defaultdict(deque)
_rate_limit_lock = Lock()
_document_update_lock = Lock()


def enforce_rate_limit(api_key: str) -> None:
    """Limit each API key to 10 requests per 60-second window."""

    current_time = time.monotonic()
    window_start = current_time - RATE_LIMIT_WINDOW_SECONDS

    with _rate_limit_lock:
        request_times = _request_history[api_key]

        while request_times and request_times[0] <= window_start:
            request_times.popleft()

        if len(request_times) >= RATE_LIMIT_REQUESTS:
            retry_after = max(
                1,
                int(
                    RATE_LIMIT_WINDOW_SECONDS
                    - (current_time - request_times[0])
                ) + 1,
            )

            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )

        request_times.append(current_time)


# --------------------------------------------------
# FILE HANDLING
# --------------------------------------------------

def sanitize_filename(filename: str) -> str:
    """Return a safe PDF filename."""

    normalized_name = filename.replace("\\", "/").split("/")[-1]
    original_stem = Path(normalized_name).stem

    safe_stem = re.sub(
        r"[^A-Za-z0-9._ -]",
        "_",
        original_stem,
    ).strip(" ._-")

    if not safe_stem:
        safe_stem = "uploaded_document"

    return f"{safe_stem}.pdf"


def get_unique_document_path(filename: str) -> Path:
    """Generate a filename that does not collide with existing documents."""

    candidate = UPLOADS_DIRECTORY / filename

    existing_names = {
        path.stem.lower()
        for directory in (DOCUMENTS_DIRECTORY, UPLOADS_DIRECTORY)
        if directory.exists()
        for path in directory.glob("*.pdf")
        if path.is_file()
    }

    if candidate.stem.lower() not in existing_names:
        return candidate

    counter = 2

    while True:
        candidate = UPLOADS_DIRECTORY / (
            f"{Path(filename).stem}-{counter}.pdf"
        )

        if candidate.stem.lower() not in existing_names:
            return candidate

        counter += 1


def validate_pdf_content(content: bytes) -> int:
    """Validate PDF structure and ensure searchable text exists."""

    if not content:
        raise ValueError("The uploaded file is empty.")

    if b"%PDF-" not in content[:1024]:
        raise ValueError("The uploaded file is not a valid PDF.")

    try:
        with pymupdf.open(
            stream=content,
            filetype="pdf",
        ) as document:
            if document.is_encrypted:
                raise ValueError(
                    "Password-protected PDFs are not supported."
                )

            if document.page_count == 0:
                raise ValueError("The PDF contains no pages.")

            has_searchable_text = any(
                page.get_text("text").strip()
                for page in document
            )

            if not has_searchable_text:
                raise ValueError(
                    "The PDF contains no searchable text. "
                    "Scanned PDFs require OCR."
                )

            return document.page_count

    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            "The uploaded PDF is corrupted or cannot be read."
        ) from exc


def get_document_metadata(path: Path, source: str) -> dict:
    """Return document information for the document-list endpoint."""

    try:
        with pymupdf.open(path) as document:
            page_count = document.page_count
    except Exception:
        logger.exception("Could not read document metadata: %s", path)
        page_count = 0

    return {
        "name": path.name,
        "source": source,
        "pages": page_count,
        "size_bytes": path.stat().st_size,
    }


# --------------------------------------------------
# APPLICATION LIFECYCLE
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the knowledge base when the API starts."""

    app.state.rag_service = None
    app.state.rag_startup_error = None

    UPLOADS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    if not DOCUMENTS_DIRECTORY.exists():
        app.state.rag_startup_error = (
            f"Documents directory not found: {DOCUMENTS_DIRECTORY}"
        )
        logger.error(app.state.rag_startup_error)
        yield
        return

    if not settings.openai_api_key:
        app.state.rag_startup_error = (
            "OpenAI API key is not configured."
        )
        logger.error(app.state.rag_startup_error)
        yield
        return

    try:
        uploaded_pdfs = list(UPLOADS_DIRECTORY.glob("*.pdf"))

        if uploaded_pdfs:
            app.state.rag_service = build_rag_service(
                documents_directory=DOCUMENTS_DIRECTORY,
                additional_documents_directories=[
                    UPLOADS_DIRECTORY
                ],
            )
        else:
            app.state.rag_service = build_rag_service(
                documents_directory=DOCUMENTS_DIRECTORY,
            )

        logger.info("RAG service initialized successfully.")

    except Exception:
        app.state.rag_startup_error = (
            "Failed to initialize the RAG service."
        )
        logger.exception("Failed to initialize RAG service.")

    yield


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)


# --------------------------------------------------
# REQUEST LOGGING AND METRICS
# --------------------------------------------------

@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next,
):
    """Log HTTP requests and record Prometheus metrics."""

    start_time = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code

        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        logger.info(
            "HTTP request completed",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )

        return response

    except Exception:
        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        logger.exception(
            "HTTP request failed",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )

        raise

    finally:
        duration_seconds = time.perf_counter() - start_time

        route = request.scope.get("route")
        endpoint = getattr(route, "path", "unmatched")

        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=str(status_code),
        ).inc()

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration_seconds)


# --------------------------------------------------
# REQUEST AND RESPONSE MODELS
# --------------------------------------------------

class AskRequest(BaseModel):
    """Request body for asking a question."""

    question: str = Field(
        min_length=1,
        max_length=2000,
    )


class EvidenceResponse(BaseModel):
    """A piece of evidence supporting an answer."""

    document_name: str
    page_number: int
    chunk_id: str
    text: str
    relevance_score: float


class AskResponse(BaseModel):
    """Answer and supporting evidence returned by the API."""

    question: str
    answer: str
    evidence: list[EvidenceResponse]


class DocumentResponse(BaseModel):
    """Metadata for a document in the knowledge base."""

    name: str
    source: str
    pages: int
    size_bytes: int


# --------------------------------------------------
# RAG SERVICE CONFIGURATION
# --------------------------------------------------

def set_rag_service(service: RAGService | None) -> None:
    """Configure the RAG service, including for tests."""

    app.state.rag_service = service


# --------------------------------------------------
# API KEY AUTHENTICATION
# --------------------------------------------------

def verify_api_key(api_key: str | None) -> None:
    """Verify the application API key."""

    expected_key = settings.app_api_key

    if not expected_key:
        raise HTTPException(
            status_code=503,
            detail="API authentication is not configured.",
        )

    if not api_key or not secrets.compare_digest(
        api_key,
        expected_key,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health_check() -> dict[str, str]:
    """Return the current health status of the API."""

    return {"status": "healthy"}


# --------------------------------------------------
# READINESS CHECK
# --------------------------------------------------

@app.get("/ready")
def readiness_check() -> dict[str, str]:
    """Return whether the knowledge service is configured."""

    service = getattr(app.state, "rag_service", None)

    if service is None:
        raise HTTPException(
            status_code=503,
            detail="The knowledge service is not configured.",
        )

    return {"status": "ready"}


# --------------------------------------------------
# PROMETHEUS METRICS
# --------------------------------------------------

@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """Expose Prometheus application metrics."""

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# --------------------------------------------------
# DOCUMENT LIST ENDPOINT
# --------------------------------------------------

@app.get(
    "/documents",
    response_model=list[DocumentResponse],
)
def list_documents(
    api_key: str | None = Header(
        default=None,
        alias="X-API-Key",
    ),
) -> list[DocumentResponse]:
    """List sample and uploaded documents."""

    verify_api_key(api_key)

    documents = []

    for path in sorted(DOCUMENTS_DIRECTORY.glob("*.pdf")):
        if path.is_file():
            documents.append(
                DocumentResponse(
                    **get_document_metadata(path, "sample")
                )
            )

    for path in sorted(UPLOADS_DIRECTORY.glob("*.pdf")):
        if path.is_file():
            documents.append(
                DocumentResponse(
                    **get_document_metadata(path, "uploaded")
                )
            )

    return documents


# --------------------------------------------------
# DOCUMENT UPLOAD ENDPOINT
# --------------------------------------------------

@app.post(
    "/documents/upload",
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    file: UploadFile = File(...),
    api_key: str | None = Header(
        default=None,
        alias="X-API-Key",
    ),
):
    """Validate, save, and index an uploaded PDF."""

    verify_api_key(api_key)

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A filename is required.",
        )

    if Path(file.filename.replace("\\", "/")).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=415,
            detail="Only PDF files are supported.",
        )

    service = getattr(app.state, "rag_service", None)

    if service is None:
        raise HTTPException(
            status_code=503,
            detail="The knowledge service is not configured.",
        )

    try:
        content = file.file.read(MAX_UPLOAD_SIZE_BYTES + 1)

        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail="The maximum PDF upload size is 10 MB.",
            )

        page_count = validate_pdf_content(content)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    finally:
        file.file.close()

    saved_path = None

    with _document_update_lock:
        try:
            filename = sanitize_filename(file.filename)
            saved_path = get_unique_document_path(filename)

            saved_path.write_bytes(content)

            # Rebuild the knowledge base without replacing the active
            # service until indexing has completed successfully.
            current_service = getattr(
                app.state,
                "rag_service",
                None,
            )

            if current_service is None:
                raise RuntimeError(
                    "The knowledge service is not configured."
                )

            new_service = build_rag_service(
                documents_directory=DOCUMENTS_DIRECTORY,
                additional_documents_directories=[
                    UPLOADS_DIRECTORY,
                ],
                answer_service=current_service.answer_service,
                reranker=current_service.reranker,
            )

            # Atomic reference replacement: existing requests can finish
            # using the old service while new requests use the new one.
            app.state.rag_service = new_service

            logger.info(
                "Document uploaded and indexed successfully: %s",
                saved_path.name,
            )

            return {
                "message": "Document uploaded and indexed successfully.",
                "document": {
                    "name": saved_path.name,
                    "source": "uploaded",
                    "pages": page_count,
                    "size_bytes": len(content),
                },
            }

        except ValueError as exc:
            if saved_path and saved_path.exists():
                saved_path.unlink()

            raise HTTPException(
                status_code=422,
                detail=str(exc),
            ) from exc

        except RateLimitError as exc:
            if saved_path and saved_path.exists():
                saved_path.unlink()

            logger.exception("OpenAI rate limit during document indexing.")

            raise HTTPException(
                status_code=503,
                detail="AI indexing is temporarily unavailable.",
            ) from exc

        except APITimeoutError as exc:
            if saved_path and saved_path.exists():
                saved_path.unlink()

            logger.exception("OpenAI indexing request timed out.")

            raise HTTPException(
                status_code=504,
                detail="Document indexing timed out.",
            ) from exc

        except APIConnectionError as exc:
            if saved_path and saved_path.exists():
                saved_path.unlink()

            logger.exception("OpenAI connection failed during indexing.")

            raise HTTPException(
                status_code=503,
                detail="The AI service is temporarily unreachable.",
            ) from exc

        except (AuthenticationError, APIStatusError) as exc:
            if saved_path and saved_path.exists():
                saved_path.unlink()

            logger.exception("OpenAI error during document indexing.")

            raise HTTPException(
                status_code=502,
                detail="The AI service returned an error during indexing.",
            ) from exc

        except Exception as exc:
            if saved_path and saved_path.exists():
                saved_path.unlink()

            logger.exception("Document upload or indexing failed.")

            raise HTTPException(
                status_code=500,
                detail="Document upload failed. Please try again.",
            ) from exc


# --------------------------------------------------
# ASK ENDPOINT
# --------------------------------------------------

@app.post("/ask", response_model=AskResponse)
def ask_question(
    request: AskRequest,
    api_key: str | None = Header(
        default=None,
        alias="X-API-Key",
    ),
) -> AskResponse:
    """Answer a question using retrieved document evidence."""

    # Step 1: Authenticate the client.
    verify_api_key(api_key)

    # Step 2: Enforce API rate limits.
    enforce_rate_limit(api_key)

    # Step 3: Check RAG service availability.
    service = getattr(app.state, "rag_service", None)

    if service is None:
        raise HTTPException(
            status_code=503,
            detail="The knowledge service is not configured.",
        )

    # Step 4: Generate a grounded answer.
    try:
        result = service.ask(request.question)

    except ValueError as exc:
        logger.exception("Invalid request while processing /ask.")

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except RateLimitError as exc:
        logger.exception("OpenAI rate limit or quota error.")

        raise HTTPException(
            status_code=503,
            detail=(
                "The AI service is temporarily unavailable. "
                "Please try again later."
            ),
        ) from exc

    except APITimeoutError as exc:
        logger.exception("OpenAI request timed out.")

        raise HTTPException(
            status_code=504,
            detail=(
                "The AI service request timed out. "
                "Please try again."
            ),
        ) from exc

    except APIConnectionError as exc:
        logger.exception("Could not connect to OpenAI.")

        raise HTTPException(
            status_code=503,
            detail="The AI service is temporarily unreachable.",
        ) from exc

    except AuthenticationError as exc:
        logger.exception("OpenAI authentication failed.")

        raise HTTPException(
            status_code=502,
            detail=(
                "The AI service authentication is not "
                "configured correctly."
            ),
        ) from exc

    except APIStatusError as exc:
        logger.exception("OpenAI returned an API error.")

        raise HTTPException(
            status_code=502,
            detail=(
                "The AI service returned an error. "
                "Please try again later."
            ),
        ) from exc

    # Step 5: Return answer and supporting evidence.
    return AskResponse(
        question=result.question,
        answer=result.answer,
        evidence=[
            EvidenceResponse(
                document_name=(
                    f"{item.result.chunk.document_id}.pdf"
                ),
                page_number=item.result.chunk.page_number,
                chunk_id=item.result.chunk.chunk_id,
                text=item.result.chunk.text,
                relevance_score=item.score,
            )
            for item in result.evidence
        ],
    )
