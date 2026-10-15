import pytest

from app.config import Config
from app.provider import (
    FallbackProvider,
    GroqProvider,
    OpenRouterProvider,
    Passage,
    ProviderError,
    build_provider,
)


class _Response:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _Recorder:
    """Stand-in for httpx.Client that captures the request payload."""

    def __init__(self) -> None:
        self.payload: dict | None = None

    def post(self, url: str, headers: dict, json: dict) -> _Response:
        self.payload = json
        return _Response({"choices": [{"message": {"content": "an answer"}}]})


def _provider(recorder: _Recorder, models: list[str]) -> OpenRouterProvider:
    return OpenRouterProvider(
        recorder,  # type: ignore[arg-type]
        "https://example.invalid",
        "key",
        models,
        100,
        "https://mateolabs.dev",
        "Backend Lab Oracle",
    )


def test_lore_mode_includes_the_system_prompt() -> None:
    recorder = _Recorder()

    _provider(recorder, ["model"]).answer("q", [Passage("/a.md", "text")], "SYSTEM")

    assert recorder.payload is not None
    roles = [message["role"] for message in recorder.payload["messages"]]
    assert roles == ["system", "user"]


def test_plain_mode_omits_the_system_prompt() -> None:
    recorder = _Recorder()

    _provider(recorder, ["model"]).answer("q", [Passage("/a.md", "text")], None)

    assert recorder.payload is not None
    roles = [message["role"] for message in recorder.payload["messages"]]
    assert roles == ["user"]


def test_a_single_model_uses_the_model_field() -> None:
    recorder = _Recorder()

    _provider(recorder, ["only/model"]).answer("q", [], None)

    assert recorder.payload is not None
    assert recorder.payload["model"] == "only/model"
    assert "models" not in recorder.payload


def test_several_models_use_the_fallback_list() -> None:
    recorder = _Recorder()

    _provider(recorder, ["first/model", "second/model", "third/model"]).answer("q", [], None)

    assert recorder.payload is not None
    assert recorder.payload["models"] == ["first/model", "second/model", "third/model"]
    assert "model" not in recorder.payload


def test_the_fallback_list_is_capped_at_three() -> None:
    recorder = _Recorder()

    _provider(recorder, ["a", "b", "c", "d", "e"]).answer("q", [], None)

    assert recorder.payload is not None
    assert recorder.payload["models"] == ["a", "b", "c"]


def test_reasoning_is_disabled() -> None:
    recorder = _Recorder()

    _provider(recorder, ["model"]).answer("q", [], None)

    assert recorder.payload is not None
    assert recorder.payload["reasoning"] == {"enabled": False}


def _groq(recorder: _Recorder, model: str = "openai/gpt-oss-20b") -> GroqProvider:
    return GroqProvider(
        recorder,  # type: ignore[arg-type]
        "https://api.groq.com/openai/v1",
        "key",
        model,
        100,
    )


def test_groq_uses_a_single_model_and_completion_tokens() -> None:
    recorder = _Recorder()

    _groq(recorder).answer("q", [], None)

    assert recorder.payload is not None
    assert recorder.payload["model"] == "openai/gpt-oss-20b"
    assert recorder.payload["max_completion_tokens"] == 100
    assert "models" not in recorder.payload


def test_groq_keeps_reasoning_short_and_out_of_the_reply() -> None:
    recorder = _Recorder()

    _groq(recorder).answer("q", [], None)

    assert recorder.payload is not None
    assert recorder.payload["reasoning_effort"] == "low"
    assert recorder.payload["include_reasoning"] is False


def test_groq_lore_mode_includes_the_system_prompt() -> None:
    recorder = _Recorder()

    _groq(recorder).answer("q", [Passage("/a.md", "text")], "SYSTEM")

    assert recorder.payload is not None
    roles = [message["role"] for message in recorder.payload["messages"]]
    assert roles == ["system", "user"]


def test_groq_plain_mode_omits_the_system_prompt() -> None:
    recorder = _Recorder()

    _groq(recorder).answer("q", [Passage("/a.md", "text")], None)

    assert recorder.payload is not None
    roles = [message["role"] for message in recorder.payload["messages"]]
    assert roles == ["user"]


class _StubProvider:
    """Provider stand-in that records calls and returns a fixed outcome."""

    def __init__(
        self,
        name: str,
        answer: str | None = None,
        error: Exception | None = None,
    ) -> None:
        self.name = name
        self._answer = answer
        self._error = error
        self.calls = 0

    def answer(self, question, passages, system_prompt):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._answer


def test_fallback_provider_returns_the_first_answer() -> None:
    first = _StubProvider("first", answer="from first")
    second = _StubProvider("second", answer="from second")

    provider = FallbackProvider([first, second])

    assert provider.answer("q", [], "SYSTEM") == "from first"
    assert second.calls == 0
    assert provider.name == "first>second"


def test_fallback_provider_falls_through_on_provider_error() -> None:
    first = _StubProvider("first", error=ProviderError("down"))
    second = _StubProvider("second", answer="from second")

    assert FallbackProvider([first, second]).answer("q", [], None) == "from second"
    assert first.calls == 1


def test_fallback_provider_raises_when_every_provider_fails() -> None:
    first = _StubProvider("first", error=ProviderError("down"))
    second = _StubProvider("second", error=ProviderError("nope"))

    with pytest.raises(ProviderError):
        FallbackProvider([first, second]).answer("q", [], None)


def test_build_provider_chains_configured_providers(monkeypatch) -> None:
    monkeypatch.setenv("ORACLE_PROVIDER", "groq,openrouter")
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")

    provider = build_provider(Config.from_environment())

    assert isinstance(provider, FallbackProvider)
    assert provider.name == "groq>openrouter"


def test_build_provider_returns_a_single_provider(monkeypatch) -> None:
    monkeypatch.setenv("ORACLE_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")

    provider = build_provider(Config.from_environment())

    assert isinstance(provider, GroqProvider)
