from app.config import Config


def test_groq_defaults(monkeypatch) -> None:
    monkeypatch.setenv("ORACLE_PROVIDER", "groq")
    monkeypatch.delenv("ORACLE_MODEL", raising=False)
    monkeypatch.delenv("ORACLE_MODELS", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")

    config = Config.from_environment()

    assert config.provider == "groq"
    assert config.models == ("openai/gpt-oss-20b",)
    assert config.base_url == "https://api.groq.com/openai/v1"
    assert config.api_key == "groq-key"


def test_groq_ignores_the_openrouter_rotation_list(monkeypatch) -> None:
    monkeypatch.setenv("ORACLE_PROVIDER", "groq")
    monkeypatch.setenv("ORACLE_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setenv("ORACLE_MODELS", "first:free,second:free")

    config = Config.from_environment()

    assert config.models == ("openai/gpt-oss-20b",)


def test_openrouter_keeps_the_rotation_list(monkeypatch) -> None:
    monkeypatch.setenv("ORACLE_PROVIDER", "openrouter")
    monkeypatch.setenv("ORACLE_MODELS", "first:free,second:free")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")

    config = Config.from_environment()

    assert config.models == ("first:free", "second:free")
    assert config.base_url == "https://openrouter.ai/api/v1"
    assert config.api_key == "openrouter-key"


def test_oracle_api_key_is_used_as_a_fallback(monkeypatch) -> None:
    monkeypatch.setenv("ORACLE_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("ORACLE_API_KEY", "shared-key")

    config = Config.from_environment()

    assert config.api_key == "shared-key"
