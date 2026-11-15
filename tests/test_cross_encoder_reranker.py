
import pytest

from app.ingestion.chunker import TextChunk
from app.retrieval.bm25_retriever import RetrievalResult
from app.reranking.cross_encoder_reranker import CrossEncoderReranker


def create_results():
    chunks = [
        TextChunk(
            text="Employees receive annual vacation benefits.",
            page_number=1,
            chunk_index=0,
            document_id="employee_handbook",
        ),
        TextChunk(
            text="Employees enroll in health insurance during open enrollment.",
            page_number=2,
            chunk_index=1,
            document_id="employee_handbook",
        ),
        TextChunk(
            text="Employees can request remote work arrangements.",
            page_number=3,
            chunk_index=2,
            document_id="employee_handbook",
        ),
    ]

    return [
        RetrievalResult(chunk=chunk, score=score)
        for chunk, score in zip(chunks, [0.2, 0.5, 0.3])
    ]


def test_reranker_sorts_results_by_relevance():
    reranker = CrossEncoderReranker()

    results = reranker.rerank(
        query="employees health insurance enrollment",
        results=create_results(),
        top_k=3,
    )

    assert len(results) == 3
    assert results[0].result.chunk.page_number == 2


def test_reranker_returns_requested_top_k():
    reranker = CrossEncoderReranker()

    results = reranker.rerank(
        query="employee benefits",
        results=create_results(),
        top_k=2,
    )

    assert len(results) == 2


def test_reranker_returns_empty_for_empty_query():
    reranker = CrossEncoderReranker()

    assert reranker.rerank(
        query="   ",
        results=create_results(),
    ) == []


def test_reranker_returns_empty_for_no_results():
    reranker = CrossEncoderReranker()

    assert reranker.rerank(
        query="employee benefits",
        results=[],
    ) == []


def test_reranker_rejects_invalid_top_k():
    reranker = CrossEncoderReranker()

    with pytest.raises(ValueError, match="top_k"):
        reranker.rerank(
            query="employee benefits",
            results=create_results(),
            top_k=0,
        )


def test_reranker_preserves_original_chunks():
    reranker = CrossEncoderReranker()
    original = create_results()

    results = reranker.rerank(
        query="employee benefits",
        results=original,
        top_k=3,
    )

    assert {
        item.result.chunk.chunk_id for item in results
    } == {
        item.chunk.chunk_id for item in original
    }

def test_reranker_ignores_common_stopwords():
    reranker = CrossEncoderReranker()

    chunk = TextChunk(
        text="The office is open on weekdays.",
        page_number=1,
        chunk_index=0,
        document_id="office_policy",
    )

    results = [
        RetrievalResult(chunk=chunk, score=0.0)
    ]

    reranked = reranker.rerank(
        query="What is the maternity leave policy?",
        results=results,
        top_k=1,
    )

    assert reranked[0].score == pytest.approx(0.0)

def test_tokenizer_removes_possessive_fragments():
    reranker = CrossEncoderReranker()

    tokens = reranker._tokenize(
        "What are the company's attendance expectations?"
    )

    assert tokens == {"attendance", "expectations"}


def test_reranker_matches_attendance_concepts():
    reranker = CrossEncoderReranker()

    attendance_chunk = TextChunk(
        text=(
            "Repeated tardiness may result in corrective action. "
            "Employees should notify their manager if they expect "
            "to arrive late."
        ),
        page_number=1,
        chunk_index=0,
        document_id="attendance_policy",
    )

    unrelated_chunk = TextChunk(
        text=(
            "Employees can enroll in the retirement savings plan "
            "and receive employer contributions."
        ),
        page_number=1,
        chunk_index=0,
        document_id="retirement_policy",
    )

    results = [
        RetrievalResult(chunk=unrelated_chunk, score=0.5),
        RetrievalResult(chunk=attendance_chunk, score=0.5),
    ]

    ranked = reranker.rerank(
        query="What are the company's attendance expectations?",
        results=results,
        top_k=2,
    )

    assert ranked[0].result.chunk.chunk_id == attendance_chunk.chunk_id

def test_vacation_query_does_not_boost_leave_of_absence():

    reranker = CrossEncoderReranker()

    vacation_chunk = TextChunk(
        text=(
            "Full-time employees receive 15 days of paid vacation "
            "per calendar year."
        ),
        page_number=1,
        chunk_index=0,
        document_id="employee_handbook",
    )

    pto_chunk = TextChunk(
        text=(
            "Eligible full-time employees receive 15 days of paid "
            "time off (PTO) annually. PTO may be used for vacation."
        ),
        page_number=1,
        chunk_index=1,
        document_id="leave_attendance_policy",
    )

    absence_chunk = TextChunk(
        text=(
            "Repeated unexcused absences or tardiness may result "
            "in corrective action. Employees should notify their "
            "manager if they expect to arrive late. Employees "
            "requiring an extended leave of absence should contact HR."
        ),
        page_number=1,
        chunk_index=2,
        document_id="leave_attendance_policy",
    )

    results = [
        RetrievalResult(chunk=vacation_chunk, score=0.5),
        RetrievalResult(chunk=pto_chunk, score=0.5),
        RetrievalResult(chunk=absence_chunk, score=0.5),
    ]

    ranked = reranker.rerank(
        query="How many vacation days do employees receive?",
        results=results,
        top_k=3,
    )

    scores = {
        item.result.chunk.chunk_id: item.score
        for item in ranked
    }

    assert scores[vacation_chunk.chunk_id] > scores[absence_chunk.chunk_id]

    assert scores[pto_chunk.chunk_id] > scores[absence_chunk.chunk_id]

def test_reranker_matches_sick_leave_concepts():

    reranker = CrossEncoderReranker()

    sick_leave_chunk = TextChunk(
        text=(
            "Employees who are ill should notify their manager. "
            "Sick leave may be used when employees are unable to work "
            "because of illness."
        ),
        page_number=1,
        chunk_index=0,
        document_id="leave_attendance_policy",
    )

    vacation_chunk = TextChunk(
        text=(
            "Full-time employees receive 15 days of paid vacation "
            "per calendar year."
        ),
        page_number=1,
        chunk_index=1,
        document_id="employee_handbook",
    )

    results = [
        RetrievalResult(chunk=vacation_chunk, score=0.5),
        RetrievalResult(chunk=sick_leave_chunk, score=0.5),
    ]

    ranked = reranker.rerank(
        query="What is the sick leave policy?",
        results=results,
        top_k=2,
    )

    assert ranked[0].result.chunk.chunk_id == sick_leave_chunk.chunk_id


def test_reranker_prefers_specific_password_policy_chunk():
    reranker = CrossEncoderReranker()

    password_chunk = TextChunk(
        text=(
            "Passwords must contain at least 12 characters. "
            "Employees must use strong, unique passwords."
        ),
        page_number=1,
        chunk_index=0,
        document_id="security_policy",
    )

    mfa_chunk = TextChunk(
        text=(
            "Multi-factor authentication is required for "
            "company email, cloud applications, and remote systems."
        ),
        page_number=1,
        chunk_index=1,
        document_id="security_policy",
    )

    results = [
        RetrievalResult(chunk=mfa_chunk, score=0.5),
        RetrievalResult(chunk=password_chunk, score=0.5),
    ]

    ranked = reranker.rerank(
        query="What is the minimum password length?",
        results=results,
        top_k=2,
    )

    assert ranked[0].result.chunk.chunk_id == password_chunk.chunk_id


def test_reranker_prefers_exact_vacation_phrase():
    reranker = CrossEncoderReranker()

    vacation_chunk = TextChunk(
        text=(
            "Full-time employees receive 15 days of paid vacation "
            "per calendar year."
        ),
        page_number=1,
        chunk_index=0,
        document_id="employee_handbook",
    )

    attendance_chunk = TextChunk(
        text=(
            "Employees are expected to maintain attendance "
            "and punctuality."
        ),
        page_number=1,
        chunk_index=1,
        document_id="attendance_policy",
    )

    ranked = reranker.rerank(
        query="How many vacation days do employees receive?",
        results=[
            RetrievalResult(chunk=attendance_chunk, score=0.5),
            RetrievalResult(chunk=vacation_chunk, score=0.5),
        ],
        top_k=2,
    )

    assert ranked[0].result.chunk.chunk_id == vacation_chunk.chunk_id


def test_reranker_prefers_specific_mfa_chunk():
    reranker = CrossEncoderReranker()

    mfa_chunk = TextChunk(
        text=(
            "Multi-factor authentication (MFA) is required "
            "for company email, cloud applications, and remote systems."
        ),
        page_number=1,
        chunk_index=0,
        document_id="security_policy",
    )

    password_chunk = TextChunk(
        text=(
            "Employees must use strong passwords containing "
            "at least 12 characters."
        ),
        page_number=1,
        chunk_index=1,
        document_id="security_policy",
    )

    ranked = reranker.rerank(
        query="Which systems require multi-factor authentication?",
        results=[
            RetrievalResult(chunk=password_chunk, score=0.5),
            RetrievalResult(chunk=mfa_chunk, score=0.5),
        ],
        top_k=2,
    )

    assert ranked[0].result.chunk.chunk_id == mfa_chunk.chunk_id


def test_reranker_prefers_access_request_chunk_for_who_question():
    reranker = CrossEncoderReranker()

    mfa_chunk = TextChunk(
        text=(
            "Multi-factor authentication is required for access "
            "to company email, cloud applications, and remote systems. "
            "Employees must register an approved authentication method."
        ),
        page_number=1,
        chunk_index=0,
        document_id="security_policy",
    )

    access_request_chunk = TextChunk(
        text=(
            "Managers must request access for new employees "
            "through the approved IT access request process. "
            "Access permissions must be reviewed periodically."
        ),
        page_number=1,
        chunk_index=1,
        document_id="security_policy",
    )

    ranked = reranker.rerank(
        query="Who is responsible for requesting system access for new employees?",
        results=[
            RetrievalResult(chunk=mfa_chunk, score=0.5),
            RetrievalResult(chunk=access_request_chunk, score=0.5),
        ],
        top_k=2,
    )

    assert ranked[0].result.chunk.chunk_id == access_request_chunk.chunk_id
