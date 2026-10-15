import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    content_root: Path
    provider: str
    models: tuple[str, ...]
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
        provider = os.getenv("ORACLE_PROVIDER", "openrouter").strip().lower()
        return cls(
            content_root=Path(os.getenv("ORACLE_CONTENT_ROOT", "/app/content")),
            provider=provider,
            models=_models(provider),
            base_url=_base_url(provider),
            api_key=_api_key(provider),
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


# The model a provider falls back to when ORACLE_MODEL is not set.
DEFAULT_MODELS = {
    "openrouter": "google/gemma-4-26b-a4b-it:free",
    "groq": "openai/gpt-oss-20b",
}

# Where each provider lives when no base URL is configured.
DEFAULT_BASE_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
}

# The environment variable holding each provider's API key.
API_KEY_VARIABLES = {
    "openrouter": "OPENROUTER_API_KEY",
    "groq": "GROQ_API_KEY",
}

# The environment variable overriding each provider's base URL.
BASE_URL_VARIABLES = {
    "openrouter": "OPENROUTER_BASE_URL",
    "groq": "GROQ_BASE_URL",
}


def _models(provider: str) -> tuple[str, ...]:
    # ORACLE_MODELS is the ordered rotation list OpenRouter walks as free
    # models are rate-limited; other providers answer with a single model.
    if provider == "openrouter":
        configured = os.getenv("ORACLE_MODELS", "").strip()
        if configured:
            models = tuple(
                name.strip() for name in configured.split(",") if name.strip()
            )
            if models:
                return models
    default = DEFAULT_MODELS.get(provider, DEFAULT_MODELS["openrouter"])
    return (os.getenv("ORACLE_MODEL") or default,)


def _base_url(provider: str) -> str:
    variable = BASE_URL_VARIABLES.get(provider)
    configured = (os.getenv(variable) if variable else None) or os.getenv(
        "ORACLE_BASE_URL"
    )
    default = DEFAULT_BASE_URLS.get(provider, DEFAULT_BASE_URLS["openrouter"])
    return (configured or default).rstrip("/")


def _api_key(provider: str) -> str:
    variable = API_KEY_VARIABLES.get(provider)
    return (
        (os.getenv(variable) if variable else None)
        or os.getenv("ORACLE_API_KEY")
        or ""
    )


def _positive_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, ""))
    except ValueError:
        return default
    return value if value > 0 else default
