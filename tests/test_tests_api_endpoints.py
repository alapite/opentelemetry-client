from fastapi.testclient import TestClient

from primes.api.main import app
from primes.api.routers import tests as tests_router
from primes.api.test_executor import RunMetrics, RunState


def test_stop_test_endpoint_success(monkeypatch):
    async def _stop_test(_test_id: str) -> bool:
        return True

    monkeypatch.setattr(tests_router, "stop_test", _stop_test)

    with TestClient(app) as client:
        response = client.post("/api/v1/tests/stop", json={"test_id": "abc"})
        assert response.status_code == 202
        assert response.json()["status"] == "stopping"


def test_stop_test_endpoint_not_found(monkeypatch):
    async def _stop_test(_test_id: str) -> bool:
        return False

    monkeypatch.setattr(tests_router, "stop_test", _stop_test)

    with TestClient(app) as client:
        response = client.post("/api/v1/tests/stop", json={"test_id": "missing"})
        assert response.status_code == 404


def test_get_status_endpoint(monkeypatch):
    state = RunState(
        test_id="abc",
        status="running",
        metrics=RunMetrics(request_count=2, success_count=2, failure_count=0),
    )

    def _get_test_state(_test_id: str):
        return state

    monkeypatch.setattr(tests_router, "get_test_state", _get_test_state)

    with TestClient(app) as client:
        response = client.get("/api/v1/tests/status/abc")
        assert response.status_code == 200
        payload = response.json()
        assert payload["test_id"] == "abc"
        assert payload["status"] == "running"
        assert payload["metrics"]["request_count"] == 2


def test_list_tests_endpoint(monkeypatch):
    monkeypatch.setattr(tests_router, "list_active_tests", lambda: ["a", "b"])
    monkeypatch.setattr(tests_router, "list_running_tests", lambda: ["b"])

    with TestClient(app) as client:
        response = client.get("/api/v1/tests/")
        assert response.status_code == 200
        payload = response.json()
        assert payload["tests"] == ["a", "b"]
        assert payload["active"] == ["b"]
