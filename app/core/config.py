
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    app_name: str = os.getenv(
        "APP_NAME",
        "Enterprise AI Knowledge Platform",
    )

    environment: str = os.getenv(
        "ENVIRONMENT",
        "development",
    )

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")

    app_api_key: str | None = os.getenv("APP_API_KEY")

    openai_model: str = os.getenv(
        "OPENAI_MODEL",
        "gpt-4.1-mini",
    )

    openai_timeout_seconds: float = float(
        os.getenv("OPENAI_TIMEOUT_SECONDS", "60")
    )

    openai_max_retries: int = int(
        os.getenv("OPENAI_MAX_RETRIES", "2")
    )


settings = Settings()
