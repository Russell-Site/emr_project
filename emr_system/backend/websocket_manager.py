# ============================================================
# websocket_manager.py
# Manages active WebSocket connections for the EMR system
# ============================================================

from fastapi import WebSocket
from typing import List
import json


class ConnectionManager:
    def __init__(self):
        # Store all currently connected WebSocket clients
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

        print(
            f"🔌 WebSocket connected. "
            f"Active connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected WebSocket client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        print(
            f"🔌 WebSocket disconnected. "
            f"Active connections: {len(self.active_connections)}"
        )

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to one specific client."""
        await websocket.send_text(json.dumps(message))

    async def broadcast(self, message: dict):
        """Send a message to every connected client."""
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                # Remember connections that are no longer available
                disconnected.append(connection)

        # Remove dead connections
        for connection in disconnected:
            self.disconnect(connection)


# One shared manager for the entire FastAPI application
manager = ConnectionManager()