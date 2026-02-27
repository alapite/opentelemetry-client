from fastapi.testclient import TestClient

from primes.api.connection_manager import manager
from primes.api.main import app


def test_websocket_subscribe_unsubscribe_and_ping():
    manager.active_connections.clear()

    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/ws/results") as ws:
            ws.send_json({"type": "subscribe", "test_id": "test-1"})
            assert ws.receive_json() == {"type": "subscribed", "test_id": "test-1"}

            ws.send_json({"type": "ping"})
            assert ws.receive_json() == {"type": "pong"}

            ws.send_json({"type": "unsubscribe"})
            assert ws.receive_json() == {"type": "unsubscribed", "test_id": "test-1"}

            ws.send_json({"type": "unknown"})
            response = ws.receive_json()
            assert response["type"] == "error"

    assert manager.active_connections == {}
