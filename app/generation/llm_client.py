
from openai import OpenAI

from app.core.config import settings
from app.core.metrics import (
    RAG_LLM_INPUT_TOKENS_TOTAL,
    RAG_LLM_OUTPUT_TOKENS_TOTAL,
    RAG_LLM_TOTAL_TOKENS_TOTAL,
)


class LLMClient:
    """Generate answers using the configured OpenAI model."""

    def __init__(self, client: OpenAI | None = None) -> None:
        if client is None:
            if not settings.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY must be configured to use the LLM."
                )

            client = OpenAI(
                api_key=settings.openai_api_key,
                timeout=settings.openai_timeout_seconds,
                max_retries=settings.openai_max_retries,
            )

        self.client = client

    def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
    ) -> str:
        """Generate a response and record available token usage."""

        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        if max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero")

        response = self.client.responses.create(
            model=settings.openai_model,
            input=prompt,
            max_output_tokens=max_tokens,
        )

        usage = getattr(response, "usage", None)

        if usage is not None:
            input_tokens = getattr(usage, "input_tokens", None)
            output_tokens = getattr(usage, "output_tokens", None)
            total_tokens = getattr(usage, "total_tokens", None)

            token_values = (input_tokens, output_tokens, total_tokens)

            if all(
                isinstance(value, int) and not isinstance(value, bool)
                for value in token_values
            ):
                RAG_LLM_INPUT_TOKENS_TOTAL.inc(input_tokens)
                RAG_LLM_OUTPUT_TOKENS_TOTAL.inc(output_tokens)
                RAG_LLM_TOTAL_TOKENS_TOTAL.inc(total_tokens)

        answer = response.output_text.strip()

        if not answer:
            raise RuntimeError("The model returned an empty response.")

        return answer
