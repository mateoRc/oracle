from app.provider import OpenRouterProvider, Passage


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


def _provider(recorder: _Recorder) -> OpenRouterProvider:
    return OpenRouterProvider(
        recorder,  # type: ignore[arg-type]
        "https://example.invalid",
        "key",
        "model",
        100,
        "https://mateolabs.dev",
        "Backend Lab Oracle",
    )


def test_lore_mode_includes_the_system_prompt() -> None:
    recorder = _Recorder()

    _provider(recorder).answer("q", [Passage("/a.md", "text")], "SYSTEM")

    assert recorder.payload is not None
    roles = [message["role"] for message in recorder.payload["messages"]]
    assert roles == ["system", "user"]


def test_plain_mode_omits_the_system_prompt() -> None:
    recorder = _Recorder()

    _provider(recorder).answer("q", [Passage("/a.md", "text")], None)

    assert recorder.payload is not None
    roles = [message["role"] for message in recorder.payload["messages"]]
    assert roles == ["user"]
