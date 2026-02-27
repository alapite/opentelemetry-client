import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from primes.api.connection_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()


async def _handle_subscribe(
    websocket: WebSocket,
    message: dict[str, object],
    current_test_id: str | None,
) -> str | None:
    test_id_raw = message.get("test_id")
    if not isinstance(test_id_raw, str):
        await websocket.send_json({"type": "error", "message": "test_id is required"})
        return current_test_id

    if current_test_id:
        manager.disconnect(websocket, current_test_id)
    await manager.connect(websocket, test_id_raw)
    await websocket.send_json({"type": "subscribed", "test_id": test_id_raw})
    logger.info(f"Client subscribed to test_id={test_id_raw}")
    return test_id_raw


async def _handle_unsubscribe(
    websocket: WebSocket, current_test_id: str | None
) -> str | None:
    if current_test_id:
        manager.disconnect(websocket, current_test_id)
        await websocket.send_json({"type": "unsubscribed", "test_id": current_test_id})
        logger.info(f"Client unsubscribed from test_id={current_test_id}")
    return None


async def _handle_message(
    websocket: WebSocket,
    message: dict[str, object],
    current_test_id: str | None,
) -> str | None:
    msg_type = message.get("type")
    if msg_type == "subscribe":
        return await _handle_subscribe(websocket, message, current_test_id)
    if msg_type == "unsubscribe":
        return await _handle_unsubscribe(websocket, current_test_id)
    if msg_type == "ping":
        await websocket.send_json({"type": "pong"})
        return current_test_id

    await websocket.send_json(
        {"type": "error", "message": f"Unknown message type: {msg_type}"}
    )
    return current_test_id


@router.websocket("/ws/results")
async def websocket_results(websocket: WebSocket):
    current_test_id = None
    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)
                if not isinstance(message, dict):
                    await websocket.send_json(
                        {"type": "error", "message": "Message must be an object"}
                    )
                    continue
                current_test_id = await _handle_message(
                    websocket, message, current_test_id
                )

            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        logger.info("WebSocket connection disconnected")
    finally:
        if current_test_id:
            manager.disconnect(websocket, current_test_id)
