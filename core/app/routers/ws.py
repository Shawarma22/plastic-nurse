from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.ws_manager import ws_manager
from app.logger import logger

router = APIRouter(tags=["websocket"])

@router.websocket("/ws/state")
async def websocket_state_endpoint(websocket: WebSocket) -> None:
    await ws_manager.connect_state(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect_state(websocket)
    except Exception as e:
        logger.error(f"WebSocket state error: {e}")
        ws_manager.disconnect_state(websocket)

@router.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket) -> None:
    await ws_manager.connect_telemetry(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect_telemetry(websocket)
    except Exception as e:
        logger.error(f"WebSocket telemetry error: {e}")
        ws_manager.disconnect_telemetry(websocket)
