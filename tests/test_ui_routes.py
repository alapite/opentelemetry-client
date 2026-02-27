from fastapi.testclient import TestClient

from primes.api.main import app


def test_ui_index_served() -> None:
    client = TestClient(app)
    resp = client.get("/ui")
    assert resp.status_code == 200
