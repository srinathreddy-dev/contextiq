
import numpy as np

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.ingestion.chunker import TextChunk
from app.retrieval.semantic_retriever import SemanticEmbedder


class MockEmbedding:
    def __init__(self, embedding):
        self.embedding = embedding


class MockEmbeddingsResponse:
    def __init__(self, vectors):
        self.data = [MockEmbedding(v) for v in vectors]


class MockEmbeddingsAPI:
    def create(self, model, input):
        if isinstance(input, str):
            texts = [input]
        else:
            texts = input

        vectors = [
            [1.0, 0.0, 0.0] if "health" in text.lower()
            else [0.0, 1.0, 0.0]
            for text in texts
        ]

        return MockEmbeddingsResponse(vectors)


class MockOpenAI:
    def __init__(self):
        self.embeddings = MockEmbeddingsAPI()


def create_chunks():
    return [
        TextChunk(
            text="Employees can enroll in health insurance.",
            page_number=1,
            chunk_index=0,
        ),
        TextChunk(
            text="Employees receive paid vacation days.",
            page_number=2,
            chunk_index=1,
        ),
    ]


def test_embed_chunks_returns_one_vector_per_chunk():
    embedder = SemanticEmbedder(client=MockOpenAI())

    embeddings = embedder.embed_chunks(create_chunks())

    assert embeddings.shape == (2, 3)


def test_embed_query_returns_vector():
    embedder = SemanticEmbedder(client=MockOpenAI())

    embedding = embedder.embed_query("health insurance")

    assert embedding.shape == (3,)


def test_embeddings_are_normalized():
    embedder = SemanticEmbedder(client=MockOpenAI())

    embedding = embedder.embed_query("health insurance")

    assert np.isclose(
        np.linalg.norm(embedding),
        1.0,
        atol=1e-5,
    )


def test_empty_chunks_return_empty_matrix():
    embedder = SemanticEmbedder(client=MockOpenAI())

    embeddings = embedder.embed_chunks([])

    assert embeddings.shape == (0, 1536)


def test_openai_embedding_client_uses_configured_timeout_and_retries(
    monkeypatch,
):
    import app.retrieval.semantic_retriever as semantic_module

    fake_settings = SimpleNamespace(
        openai_api_key="test-key",
        openai_timeout_seconds=60.0,
        openai_max_retries=2,
    )

    monkeypatch.setattr(
        semantic_module,
        "settings",
        fake_settings,
    )

    mock_openai = Mock()

    monkeypatch.setattr(
        semantic_module,
        "OpenAI",
        mock_openai,
    )

    SemanticEmbedder()

    mock_openai.assert_called_once_with(
        api_key="test-key",
        timeout=60.0,
        max_retries=2,
    )


def test_semantic_embedder_requires_api_key(monkeypatch):
    import app.retrieval.semantic_retriever as semantic_module

    fake_settings = SimpleNamespace(
        openai_api_key=None,
        openai_timeout_seconds=60.0,
        openai_max_retries=2,
    )

    monkeypatch.setattr(
        semantic_module,
        "settings",
        fake_settings,
    )

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        SemanticEmbedder()
