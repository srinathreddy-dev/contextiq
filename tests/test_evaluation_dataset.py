
from app.evaluation.dataset import EVALUATION_QUERIES


def test_evaluation_dataset_contains_thirty_queries():
    assert len(EVALUATION_QUERIES) == 30


def test_evaluation_dataset_has_no_duplicate_queries():
    query_texts = [
        query.query
        for query in EVALUATION_QUERIES
    ]

    assert len(query_texts) == len(set(query_texts))


def test_evaluation_dataset_queries_have_relevant_chunks():
    for query in EVALUATION_QUERIES:
        assert query.query.strip()
        assert query.relevant_chunk_ids


def test_system_access_query_only_marks_access_request_chunk_as_relevant():

    query = next(
        item
        for item in EVALUATION_QUERIES
        if item.query == "Who is responsible for requesting system access for new employees?"
    )

    assert query.relevant_chunk_ids == {
        "it_security_policy-page-1-chunk-2",
    }

def test_sick_leave_query_only_marks_sick_leave_chunk_as_relevant():
    query = next(
        item
        for item in EVALUATION_QUERIES
        if item.query == "Can employees take sick leave when they are unable to work because of illness?"
    )

    assert query.relevant_chunk_ids == {
        "leave_attendance_policy-page-1-chunk-0",
        "leave_attendance_policy-page-1-chunk-1",
    }
