import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app


def test_ask_requires_authentication() -> None:
    asyncio.run(_test_ask_requires_authentication())


async def _test_ask_requires_authentication() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://oracle",
    ) as client:
        response = await client.post("/ask", json={"question": "hello"})

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_health_and_status_are_public() -> None:
    asyncio.run(_test_health_and_status_are_public())


async def _test_health_and_status_are_public() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://oracle",
    ) as client:
        health_response = await client.get("/healthz")
        status_response = await client.get("/status")

    assert health_response.status_code == 200
    assert health_response.text == "ok"
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "ok"
