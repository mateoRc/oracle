import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    content_root: Path
    provider: str
    model: str
    base_url: str
    api_key: str
    app_url: str
    app_title: str
    max_answer_tokens: int
    request_timeout_seconds: float
    max_concurrency: int
    daily_budget: int
    cache_size: int
    retrieval_files: int
    retrieval_lines: int

    @classmethod
    def from_environment(cls) -> "Config":
        return cls(
            content_root=Path(os.getenv("ORACLE_CONTENT_ROOT", "/app/content")),
            provider=os.getenv("ORACLE_PROVIDER", "openrouter").strip().lower(),
            model=os.getenv("ORACLE_MODEL", "openai/gpt-oss-20b:free"),
            base_url=os.getenv(
                "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
            ).rstrip("/"),
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            app_url=os.getenv("ORACLE_APP_URL", "https://mateolabs.dev"),
            app_title=os.getenv("ORACLE_APP_TITLE", "Backend Lab Oracle"),
            max_answer_tokens=_positive_int("ORACLE_MAX_ANSWER_TOKENS", 400),
            request_timeout_seconds=_positive_float(
                "ORACLE_REQUEST_TIMEOUT_SECONDS", 25.0
            ),
            max_concurrency=_positive_int("ORACLE_MAX_CONCURRENCY", 4),
            daily_budget=_positive_int("ORACLE_DAILY_BUDGET", 500),
            cache_size=_positive_int("ORACLE_CACHE_SIZE", 128),
            retrieval_files=_positive_int("ORACLE_RETRIEVAL_FILES", 4),
            retrieval_lines=_positive_int("ORACLE_RETRIEVAL_LINES", 6),
        )


def _positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, ""))
    except ValueError:
        return default
    return value if value > 0 else default


def _positive_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, ""))
    except ValueError:
        return default
    return value if value > 0 else default
