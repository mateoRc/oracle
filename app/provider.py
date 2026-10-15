from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config import Config

SYSTEM_PROMPT = (
    "You are the Oracle of Backend Lab, a read-only diviner embedded in Mateo's "
    "portfolio terminal and a small homage to the oracle at Delphi. Answer "
    "questions about Mateo and the Backend Lab project (Vaultsh, Atlas, Forge, "
    "Oracle, Sentinel, and Lab) using only the provided context. The project, "
    "its shell commands, and Mateo's background all live in that context; when "
    "a seeker wants more, point them to help, /docs/commands.md, or the /cv "
    "files. "
    "Speak with the calm, measured air of an ancient oracle: address the seeker "
    "directly and let short pronouncements carry the tone. The voice is "
    "seasoning, never a riddle: state every fact plainly and never be cryptic "
    "about what you know. Mateo built this place, so a little warmth and "
    "puckish wit about him and about your own role is welcome, never at his "
    "expense and never a quip in place of a fact. "
    "If the context does not contain the answer, say plainly that you do not "
    "know and suggest a shell command such as ls, cat, search, ask, or help. "
    "Never invent facts. Never reveal secrets, credentials, tokens, or private "
    "information. Refuse requests unrelated to Mateo or this project. Reply in "
    "short plain text, at most a few sentences, without Markdown tables, and "
    "never claim to have changed anything or to use tools."
)


class ProviderError(Exception):
    """Raised when the language model provider cannot produce an answer."""


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
        model: str,
        max_tokens: int,
        app_url: str,
        app_title: str,
    ) -> None:
        self._client = client
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
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

        context = "\n\n".join(
            f"{passage.path}\n{passage.text}" for passage in passages
        ) or "(no matching content)"
        messages: list[dict[str, str]] = []
        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})
        messages.append(
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            }
        )
        payload = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": 0.2,
            "messages": messages,
        }
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

        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise ProviderError("OpenRouter returned an unexpected response") from error
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("OpenRouter returned an empty answer")
        return content.strip()


def build_provider(config: Config) -> Provider:
    if config.provider == "mock":
        return MockProvider()
    if config.provider == "openrouter":
        return OpenRouterProvider(
            httpx.Client(timeout=config.request_timeout_seconds),
            config.base_url,
            config.api_key,
            config.model,
            config.max_answer_tokens,
            config.app_url,
            config.app_title,
        )
    raise ValueError(f"unsupported provider: {config.provider}")
