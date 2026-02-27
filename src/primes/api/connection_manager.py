import logging
from collections import defaultdict
from typing import Any, Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, test_id: str) -> None:
        self.active_connections[test_id].add(websocket)
        logger.info(
            f"WebSocket connected for test_id={test_id}, total connections for test: {len(self.active_connections[test_id])}"
        )

    def disconnect(self, websocket: WebSocket, test_id: str) -> None:
        if test_id in self.active_connections:
            self.active_connections[test_id].discard(websocket)
            if not self.active_connections[test_id]:
                del self.active_connections[test_id]
        logger.info(f"WebSocket disconnected for test_id={test_id}")

    async def broadcast(self, test_id: str, message: dict[str, Any]) -> None:
        if test_id in self.active_connections:
            disconnected: Set[WebSocket] = set()
            for connection in self.active_connections[test_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send message to client: {e}")
                    disconnected.add(connection)
            for connection in disconnected:
                self.disconnect(connection, test_id)

    async def broadcast_all(self, message: dict[str, Any]) -> None:
        test_ids = list(self.active_connections.keys())
        for test_id in test_ids:
            await self.broadcast(test_id, message)


manager = WebSocketConnectionManager()
