import json
from typing import Set, Dict, Any
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self) -> None:
        self.state_connections: Set[WebSocket] = set()
        self.telemetry_connections: Set[WebSocket] = set()

    async def connect_state(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.state_connections.add(websocket)

    def disconnect_state(self, websocket: WebSocket) -> None:
        self.state_connections.discard(websocket)

    async def connect_telemetry(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.telemetry_connections.add(websocket)

    def disconnect_telemetry(self, websocket: WebSocket) -> None:
        self.telemetry_connections.discard(websocket)

    async def broadcast_state(self, data: Dict[str, Any]) -> None:
        message = json.dumps(data)
        disconnected = set()
        for conn in self.state_connections:
            try:
                await conn.send_text(message)
            except Exception:
                disconnected.add(conn)
        for conn in disconnected:
            self.state_connections.discard(conn)

    async def broadcast_telemetry(self, data: Dict[str, Any]) -> None:
        message = json.dumps(data)
        disconnected = set()
        for conn in self.telemetry_connections:
            try:
                await conn.send_text(message)
            except Exception:
                disconnected.add(conn)
        for conn in disconnected:
            self.telemetry_connections.discard(conn)

ws_manager = WebSocketManager()
