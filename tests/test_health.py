from app.main import health, service_status


def test_health_returns_ok() -> None:
    assert health() == "ok"


def test_status_returns_uptime() -> None:
    status = service_status()

    assert status["status"] == "ok"
    assert isinstance(status["uptime_seconds"], int)
    assert status["uptime_seconds"] >= 0
