"""WebSocket connection manager for real-time updates."""
import asyncio
import json
import time
import uuid
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect


class WebSocketManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.connections: dict[str, WebSocket] = {}
        self.subscriptions: dict[str, set[str]] = {
            "services": set(),
            "workers": set(),
            "memory": set(),
            "all": set(),
        }

    async def connect(self, websocket: WebSocket) -> str:
        """Accept a new WebSocket connection and return its ID."""
        await websocket.accept()
        connection_id = str(uuid.uuid4())[:8]
        self.connections[connection_id] = websocket
        # Auto-subscribe to 'all' by default
        self.subscriptions["all"].add(connection_id)
        return connection_id

    async def disconnect(self, connection_id: str):
        """Remove a WebSocket connection."""
        if connection_id in self.connections:
            del self.connections[connection_id]

        # Remove from all subscriptions
        for channel_subs in self.subscriptions.values():
            channel_subs.discard(connection_id)

    def subscribe(self, connection_id: str, channel: str):
        """Subscribe a connection to a channel."""
        if channel in self.subscriptions:
            self.subscriptions[channel].add(connection_id)
        elif channel == "all":
            for ch in self.subscriptions:
                self.subscriptions[ch].add(connection_id)

    def unsubscribe(self, connection_id: str, channel: str):
        """Unsubscribe a connection from a channel."""
        if channel in self.subscriptions:
            self.subscriptions[channel].discard(connection_id)

    async def send_to(self, connection_id: str, message: dict[str, Any]):
        """Send a message to a specific connection."""
        if connection_id in self.connections:
            websocket = self.connections[connection_id]
            try:
                await websocket.send_json(message)
            except Exception:
                await self.disconnect(connection_id)

    async def broadcast(self, channel: str, data: dict[str, Any]):
        """Broadcast a message to all subscribers of a channel."""
        message = {
            "type": f"{channel}_update",
            "timestamp": time.time(),
            "data": data,
        }

        # Get subscribers for this channel and 'all'
        subscribers = self.subscriptions.get(channel, set()) | self.subscriptions.get(
            "all", set()
        )

        disconnected = []
        for connection_id in subscribers:
            if connection_id in self.connections:
                try:
                    await self.connections[connection_id].send_json(message)
                except Exception:
                    disconnected.append(connection_id)

        # Clean up disconnected clients
        for connection_id in disconnected:
            await self.disconnect(connection_id)

    async def broadcast_all(self, message_type: str, data: dict[str, Any]):
        """Broadcast to all connected clients regardless of subscription."""
        message = {
            "type": message_type,
            "timestamp": time.time(),
            "data": data,
        }

        disconnected = []
        for connection_id, websocket in list(self.connections.items()):
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(connection_id)

        for connection_id in disconnected:
            await self.disconnect(connection_id)

    async def handle_message(self, connection_id: str, message: dict[str, Any]):
        """Handle incoming WebSocket messages."""
        msg_type = message.get("type")

        if msg_type == "subscribe":
            channel = message.get("channel", "all")
            self.subscribe(connection_id, channel)
            await self.send_to(
                connection_id,
                {"type": "subscribed", "channel": channel, "timestamp": time.time()},
            )

        elif msg_type == "unsubscribe":
            channel = message.get("channel", "all")
            self.unsubscribe(connection_id, channel)
            await self.send_to(
                connection_id,
                {"type": "unsubscribed", "channel": channel, "timestamp": time.time()},
            )

        elif msg_type == "ping":
            await self.send_to(
                connection_id, {"type": "pong", "timestamp": time.time()}
            )

    @property
    def connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.connections)


# Global WebSocket manager instance
ws_manager = WebSocketManager()
