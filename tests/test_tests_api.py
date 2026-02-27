import pytest
from fastapi.testclient import TestClient

from primes.api.main import app
from primes.distributions.loader import load_plugins


@pytest.fixture(scope="module")
def client():
    load_plugins()
    with TestClient(app) as c:
        yield c


async def _noop_execute_test(*_args, **_kwargs):
    return None


def test_start_test_accepts_sequence_distribution(client, monkeypatch):
    monkeypatch.setattr("primes.api.routers.tests.execute_test", _noop_execute_test)
    response = client.post(
        "/api/v1/tests/start",
        json={
            "test_type": "distribution",
            "duration_seconds": 5,
            "target_rps": 20,
            "distribution": {
                "name": "sequence",
                "config": {
                    "post_behavior": "hold_last",
                    "stages": [
                        {
                            "duration_seconds": 2,
                            "distribution": {"name": "constant", "config": {"rps": 10}},
                        }
                    ],
                },
            },
        },
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "starting"
    assert "test_id" in payload


def test_start_test_accepts_mix_distribution(client, monkeypatch):
    monkeypatch.setattr("primes.api.routers.tests.execute_test", _noop_execute_test)
    response = client.post(
        "/api/v1/tests/start",
        json={
            "test_type": "distribution",
            "num_requests": 5,
            "target_rps": 30,
            "distribution": {
                "name": "mix",
                "config": {
                    "components": [
                        {
                            "weight": 1.0,
                            "distribution": {"name": "constant", "config": {"rps": 30}},
                        }
                    ]
                },
            },
        },
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "starting"
    assert "test_id" in payload


def test_start_test_requires_target_rps_for_distribution(client, monkeypatch):
    monkeypatch.setattr("primes.api.routers.tests.execute_test", _noop_execute_test)
    response = client.post(
        "/api/v1/tests/start",
        json={
            "test_type": "distribution",
            "num_requests": 5,
            "distribution": {
                "name": "mix",
                "config": {
                    "components": [
                        {
                            "weight": 1.0,
                            "distribution": {"name": "constant", "config": {"rps": 30}},
                        }
                    ]
                },
            },
        },
    )
    assert response.status_code == 400


def test_start_test_requires_duration_or_num_requests_for_distribution(client, monkeypatch):
    monkeypatch.setattr("primes.api.routers.tests.execute_test", _noop_execute_test)
    response = client.post(
        "/api/v1/tests/start",
        json={
            "test_type": "distribution",
            "target_rps": 20,
            "distribution": {
                "name": "sequence",
                "config": {
                    "stages": [
                        {
                            "duration_seconds": 2,
                            "distribution": {"name": "constant", "config": {"rps": 10}},
                        }
                    ]
                },
            },
        },
    )
    assert response.status_code == 400
