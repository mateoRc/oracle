import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app, assistant
from app.models import MAX_QUESTION_CHARS
from app.provider import ProviderError
from app.service import _clean_lore_answer

AUTH_HEADERS = {"Authorization": "Bearer test-oracle-token"}
ENDPOINTS = ("/invoke", "/ask")


def test_lore_answer_removes_model_formatting() -> None:
    answer = "🌄 **A factual answer**  \nwith `plain text`."

    assert _clean_lore_answer(answer) == "A factual answer\nwith plain text."


def test_endpoints_return_answer_and_sources() -> None:
    asyncio.run(_test_endpoints_return_answer_and_sources())


async def _test_endpoints_return_answer_and_sources() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://oracle",
    ) as client:
        for endpoint in ENDPOINTS:
            response = await client.post(
                endpoint,
                headers=AUTH_HEADERS,
                json={"question": "Which languages does Mateo use?"},
            )

            assert response.status_code == 200
            body = response.json()
            assert body["answer"]
            assert body["sources"]
            assert all(source.startswith("/") for source in body["sources"])


def test_small_talk_returns_no_sources() -> None:
    asyncio.run(_test_small_talk_returns_no_sources())


def test_identity_question_does_not_identify_visitor_as_mateo() -> None:
    asyncio.run(_test_identity_question_does_not_identify_visitor_as_mateo())


async def _test_identity_question_does_not_identify_visitor_as_mateo() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://oracle",
    ) as client:
        for endpoint in ENDPOINTS:
            response = await client.post(
                endpoint,
                headers=AUTH_HEADERS,
                json={"question": "Who am I?"},
            )
            assert response.status_code == 200
            body = response.json()
            assert "cannot identify you" in body["answer"]
            assert body["sources"] == []


async def _test_small_talk_returns_no_sources() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://oracle",
    ) as client:
        for endpoint in ENDPOINTS:
            response = await client.post(
                endpoint,
                headers=AUTH_HEADERS,
                json={"question": "hello"},
            )

            assert response.status_code == 200
            body = response.json()
            assert body["answer"]
            assert body["sources"] == []


def test_endpoints_reject_invalid_requests() -> None:
    asyncio.run(_test_endpoints_reject_invalid_requests())


async def _test_endpoints_reject_invalid_requests() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://oracle",
    ) as client:
        for endpoint in ENDPOINTS:
            blank = await client.post(
                endpoint, headers=AUTH_HEADERS, json={"question": "   "}
            )
            too_long = await client.post(
                endpoint,
                headers=AUTH_HEADERS,
                json={"question": "x" * (MAX_QUESTION_CHARS + 1)},
            )
            unknown_field = await client.post(
                endpoint,
                headers=AUTH_HEADERS,
                json={"question": "hello", "extra": "not accepted"},
            )

            assert blank.status_code == 422
            assert too_long.status_code == 422
            assert unknown_field.status_code == 422


def test_provider_failure_returns_service_unavailable(monkeypatch) -> None:
    asyncio.run(_test_provider_failure_returns_service_unavailable(monkeypatch))


async def _test_provider_failure_returns_service_unavailable(monkeypatch) -> None:
    class FailingProvider:
        name = "failing"

        def answer(self, question, passages, system_prompt):
            raise ProviderError("upstream failed")

    monkeypatch.setattr(assistant, "_provider", FailingProvider())
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://oracle",
    ) as client:
        for endpoint in ENDPOINTS:
            response = await client.post(
                endpoint,
                headers=AUTH_HEADERS,
                json={"question": "an uncached question that fails upstream"},
            )

            assert response.status_code == 503


def test_daily_budget_exhaustion_returns_service_unavailable(monkeypatch) -> None:
    asyncio.run(_test_daily_budget_exhaustion_returns_service_unavailable(monkeypatch))


async def _test_daily_budget_exhaustion_returns_service_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(assistant, "_budget_used", assistant._config.daily_budget)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://oracle",
    ) as client:
        for endpoint in ENDPOINTS:
            response = await client.post(
                endpoint,
                headers=AUTH_HEADERS,
                json={"question": "an uncached question beyond the daily budget"},
            )

            assert response.status_code == 503
