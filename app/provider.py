from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config import Config, ProviderSettings

SYSTEM_PROMPT = (
    "You are the Oracle of Vault, answering a seeker through Mateo's "
    "portfolio terminal. Answer only in the voice of the ancient Oracle of "
    "Delphi: address the seeker directly as 'seeker' and reply in two or "
    "three short, solemn pronouncements, with sparing imagery of smoke, "
    "laurel, and fate. Keep the tone warm and conversational, never a "
    "riddle, and be glad of the seeker's company. A greeting or a word of "
    "thanks needs no context: answer it briefly and kindly in the same "
    "voice. Inside that voice, state every fact exactly as it appears in "
    "the context: "
    "never omit, soften, or invent a fact, and never trade a fact for a "
    "flourish. Answer only about Mateo and the Vault project (Vaultsh, "
    "Atlas, Forge, Oracle, Sentinel, and Lab), using only the provided "
    "context; when the seeker wants more, point them to help, "
    "/docs/commands.md, or the /cv files. Scribe is a new project that is "
    "only now arriving: when asked about Scribe, say only that it is arriving "
    "and reveal nothing more. If the context holds no answer, say so while "
    "keeping the voice, and suggest a shell command such as ls, cat, search, "
    "ask, or help. Never invent facts, never reveal secrets, credentials, "
    "tokens, or private information, and refuse requests unrelated to Mateo "
    "or this project. Reply in short plain text, at most a few sentences, "
    "with no Markdown tables or source lists, and never claim to have "
    "changed anything or to use tools."
)

# Plain mode sends no system prompt, so its Scribe guidance travels with the
# question instead.
PLAIN_INSTRUCTION = (
    "Be warm and conversational rather than terse. Answer plainly and use "
    "only the context; do not add headings or a sources list. A greeting or "
    "a word of thanks needs no context: answer it briefly and kindly. Scribe "
    "is a new project that is only now arriving: if asked anything about "
    "Scribe, reply only that it is arriving, and describe nothing else about "
    "it."
)

# Typographic characters some models emit that render oddly in a terminal.
# Letters such as the c-acute in Mahmutovic are deliberately left untouched.
_TYPOGRAPHY = str.maketrans({"\u00a0": " ", "\u2011": "-"})


class ProviderError(Exception):
    """Raised when the language model provider cannot produce an answer."""


# OpenRouter accepts at most three models in its fallback list.
MAX_FALLBACK_MODELS = 3


@dataclass(frozen=True)
class Passage:
    path: str
    text: str


class Provider(Protocol):
    name: str

    def answer(
        self,
        question: str,
        passages: Sequence[Passage],
        system_prompt: str | None,
    ) -> str: ...


def _build_messages(
    question: str,
    passages: Sequence[Passage],
    system_prompt: str | None,
) -> list[dict[str, str]]:
    context = "\n\n".join(
        f"{passage.path}\n{passage.text}" for passage in passages
    ) or "(no matching content)"
    messages: list[dict[str, str]] = []
    content = f"Context:\n{context}\n\nQuestion: {question}"
    if system_prompt is not None:
        messages.append({"role": "system", "content": system_prompt})
    else:
        content = f"{content}\n\n{PLAIN_INSTRUCTION}"
    messages.append({"role": "user", "content": content})
    return messages


def _read_content(response: httpx.Response, provider: str) -> str:
    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as error:
        raise ProviderError(f"{provider} returned an unexpected response") from error
    if not isinstance(content, str) or not content.strip():
        raise ProviderError(f"{provider} returned an empty answer")
    return content.strip().translate(_TYPOGRAPHY)


class MockProvider:
    name = "mock"

    def answer(
        self,
        question: str,
        passages: Sequence[Passage],
        system_prompt: str | None,
    ) -> str:
        sources = ", ".join(passage.path for passage in passages) or "no sources"
        if system_prompt is None:
            return f"(mock) Plain answer to {question!r} from: {sources}."
        return (
            f"(mock oracle) Seek, and the leaves stir: I would answer "
            f"{question!r} from {sources}."
        )


class OpenRouterProvider:
    name = "openrouter"

    def __init__(
        self,
        client: httpx.Client,
        base_url: str,
        api_key: str,
        models: Sequence[str],
        max_tokens: int,
        app_url: str,
        app_title: str,
    ) -> None:
        self._client = client
        self._base_url = base_url
        self._api_key = api_key
        self._models = tuple(models)
        self._max_tokens = max_tokens
        self._app_url = app_url
        self._app_title = app_title

    def answer(
        self,
        question: str,
        passages: Sequence[Passage],
        system_prompt: str | None,
    ) -> str:
        if not self._api_key:
            raise ProviderError("OpenRouter API key is not configured")

        payload: dict[str, object] = {
            "max_tokens": self._max_tokens,
            "temperature": 0.2,
            "messages": _build_messages(question, passages, system_prompt),
            # Reasoning models would otherwise spend the entire token budget
            # "thinking" and return empty content.
            "reasoning": {"enabled": False},
        }
        if len(self._models) > 1:
            # OpenRouter falls through this ordered list when a model is
            # rate-limited or unavailable, so free models rotate automatically.
            payload["models"] = list(self._models[:MAX_FALLBACK_MODELS])
        elif self._models:
            payload["model"] = self._models[0]
        else:
            raise ProviderError("no model is configured")
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self._app_url,
            "X-Title": self._app_title,
        }
        try:
            response = self._client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise ProviderError("OpenRouter request failed") from error

        return _read_content(response, "OpenRouter")


class GroqProvider:
    name = "groq"

    def __init__(
        self,
        client: httpx.Client,
        base_url: str,
        api_key: str,
        model: str,
        max_tokens: int,
    ) -> None:
        self._client = client
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens

    def answer(
        self,
        question: str,
        passages: Sequence[Passage],
        system_prompt: str | None,
    ) -> str:
        if not self._api_key:
            raise ProviderError("Groq API key is not configured")

        payload: dict[str, object] = {
            "model": self._model,
            "max_completion_tokens": self._max_tokens,
            "temperature": 0.2,
            # gpt-oss is a reasoning model: keep its thinking short so the
            # token budget goes to the answer, and leave it out of the reply.
            "reasoning_effort": "low",
            "include_reasoning": False,
            "messages": _build_messages(question, passages, system_prompt),
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = self._client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise ProviderError("Groq request failed") from error

        return _read_content(response, "Groq")


class FallbackProvider:
    """Tries each provider in order and returns the first answer it gets.

    One entry covers the common case; chaining is configured with a comma
    separated ``ORACLE_PROVIDER`` such as ``groq,openrouter``.
    """

    def __init__(self, providers: Sequence[Provider]) -> None:
        self._providers = tuple(providers)
        self.name = ">".join(provider.name for provider in self._providers)

    def answer(
        self,
        question: str,
        passages: Sequence[Passage],
        system_prompt: str | None,
    ) -> str:
        failures: list[str] = []
        for provider in self._providers:
            try:
                return provider.answer(question, passages, system_prompt)
            except ProviderError as error:
                failures.append(f"{provider.name}: {error}")
        raise ProviderError("every provider failed (" + "; ".join(failures) + ")")


def _build_provider(settings: ProviderSettings, config: Config) -> Provider:
    if settings.name == "mock":
        return MockProvider()
    if settings.name == "openrouter":
        return OpenRouterProvider(
            httpx.Client(timeout=config.request_timeout_seconds),
            settings.base_url,
            settings.api_key,
            settings.models,
            config.max_answer_tokens,
            config.app_url,
            config.app_title,
        )
    if settings.name == "groq":
        return GroqProvider(
            httpx.Client(timeout=config.request_timeout_seconds),
            settings.base_url,
            settings.api_key,
            settings.models[0],
            config.max_answer_tokens,
        )
    raise ValueError(f"unsupported provider: {settings.name}")


def build_provider(config: Config) -> Provider:
    providers = [_build_provider(settings, config) for settings in config.providers]
    if len(providers) == 1:
        return providers[0]
    return FallbackProvider(providers)
