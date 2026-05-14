import json
from collections import defaultdict

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    def __init__(self):
        # user_id -> list of WebSocket connections
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        self._connections[user_id].append(websocket)
        logger.info("ws_connected", user_id=user_id)

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        self._connections[user_id] = [
            ws for ws in self._connections[user_id] if ws is not websocket
        ]
        logger.info("ws_disconnected", user_id=user_id)

    async def send_to_user(self, user_id: str, event: str, data: dict) -> None:
        message = json.dumps({"event": event, "data": data})
        dead: list[WebSocket] = []
        for ws in self._connections.get(user_id, []):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[user_id].remove(ws)

    async def broadcast(self, event: str, data: dict) -> None:
        """Send to ALL connected users — used for approval_required events."""
        message = json.dumps({"event": event, "data": data})
        dead: list[tuple[str, WebSocket]] = []
        for user_id, connections in self._connections.items():
            for ws in connections:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append((user_id, ws))
        for user_id, ws in dead:
            if ws in self._connections.get(user_id, []):
                self._connections[user_id].remove(ws)

    @property
    def active_connections(self) -> int:
        return sum(len(v) for v in self._connections.values())


ws_manager = WebSocketManager()
