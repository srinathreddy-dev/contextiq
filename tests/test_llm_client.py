
from unittest.mock import Mock

import pytest

from app.generation.llm_client import LLMClient


def create_mock_client(
    answer: str = "Employees receive 15 vacation days.",
) -> Mock:
    """Create a mock OpenAI client with a predictable response."""

    client = Mock()
    client.responses.create.return_value.output_text = answer

    return client


def test_generate_returns_model_answer():
    client = create_mock_client()
    llm_client = LLMClient(client=client)

    answer = llm_client.generate(
        "How many vacation days are provided?"
    )

    assert answer == "Employees receive 15 vacation days."
    client.responses.create.assert_called_once()


def test_generate_strips_whitespace():
    client = create_mock_client("  Answer with whitespace.  ")
    llm_client = LLMClient(client=client)

    answer = llm_client.generate("Provide an answer.")

    assert answer == "Answer with whitespace."


def test_generate_rejects_empty_prompt():
    llm_client = LLMClient(client=create_mock_client())

    with pytest.raises(ValueError, match="Prompt"):
        llm_client.generate("   ")


def test_generate_rejects_invalid_max_tokens():
    llm_client = LLMClient(client=create_mock_client())

    with pytest.raises(ValueError, match="max_tokens"):
        llm_client.generate(
            "Provide an answer.",
            max_tokens=0,
        )


def test_generate_rejects_empty_model_response():
    llm_client = LLMClient(client=create_mock_client("   "))

    with pytest.raises(RuntimeError, match="empty response"):
        llm_client.generate("Provide an answer.")


def test_openai_client_uses_configured_timeout_and_retries(
    monkeypatch,
):
    from types import SimpleNamespace
    import app.generation.llm_client as llm_module

    fake_settings = SimpleNamespace(
        openai_api_key="test-key",
        openai_timeout_seconds=60.0,
        openai_max_retries=2,
        openai_model="gpt-4.1-mini",
    )

    monkeypatch.setattr(
        llm_module,
        "settings",
        fake_settings,
    )

    mock_openai = Mock()
    monkeypatch.setattr(
        llm_module,
        "OpenAI",
        mock_openai,
    )

    LLMClient()

    mock_openai.assert_called_once_with(
        api_key="test-key",
        timeout=60.0,
        max_retries=2,
    )


def test_llm_client_requires_api_key(monkeypatch):
    from types import SimpleNamespace
    import app.generation.llm_client as llm_module

    fake_settings = SimpleNamespace(
        openai_api_key=None,
        openai_timeout_seconds=60.0,
        openai_max_retries=2,
    )

    monkeypatch.setattr(
        llm_module,
        "settings",
        fake_settings,
    )

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        LLMClient()

def test_generate_records_token_usage(monkeypatch):
    from types import SimpleNamespace
    import app.generation.llm_client as llm_module

    input_counter = Mock()
    output_counter = Mock()
    total_counter = Mock()

    monkeypatch.setattr(
        llm_module, "RAG_LLM_INPUT_TOKENS_TOTAL", input_counter
    )
    monkeypatch.setattr(
        llm_module, "RAG_LLM_OUTPUT_TOKENS_TOTAL", output_counter
    )
    monkeypatch.setattr(
        llm_module, "RAG_LLM_TOTAL_TOKENS_TOTAL", total_counter
    )

    response = SimpleNamespace(
        output_text="Employees receive 15 vacation days.",
        usage=SimpleNamespace(
            input_tokens=120,
            output_tokens=35,
            total_tokens=155,
        ),
    )

    client = Mock()
    client.responses.create.return_value = response

    llm_client = LLMClient(client=client)
    answer = llm_client.generate("How many vacation days?")

    assert answer == "Employees receive 15 vacation days."
    input_counter.inc.assert_called_once_with(120)
    output_counter.inc.assert_called_once_with(35)
    total_counter.inc.assert_called_once_with(155)
