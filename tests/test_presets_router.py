import importlib
from pathlib import Path

from fastapi.testclient import TestClient


def test_presets_crud(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PRESETS_FILE", str(tmp_path / "presets.json"))
    from primes.api import config as api_config
    from primes.api import main as api_main

    importlib.reload(api_config)
    importlib.reload(api_main)

    client = TestClient(api_main.app)

    resp = client.get("/api/v1/presets")
    assert resp.status_code == 200
    assert resp.json() == []

    create = client.post(
        "/api/v1/presets",
        json={
            "name": "smoke",
            "config": {
                "test_type": "linear",
                "duration_seconds": 10,
                "spawn_rate": 1.0,
                "user_count": 1,
            },
        },
    )
    assert create.status_code == 201
    preset = create.json()
    assert preset["name"] == "smoke"

    update = client.put(
        f"/api/v1/presets/{preset['id']}",
        json={
            "name": "smoke-2",
            "config": {
                "test_type": "linear",
                "duration_seconds": 20,
                "spawn_rate": 2.0,
                "user_count": 2,
            },
        },
    )
    assert update.status_code == 200

    delete = client.delete(f"/api/v1/presets/{preset['id']}")
    assert delete.status_code == 204
