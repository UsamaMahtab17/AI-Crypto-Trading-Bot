from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi import WebSocketException
import asyncio
from typing import Dict

class ConnectionManager:
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}

    async def connect(self, strategy_id: str, websocket: WebSocket):
        if strategy_id in self.connections:
            raise WebSocketException(detail="Conversation ID already in use")
        await websocket.accept() 
        self.connections[strategy_id] = websocket

    async def disconnect(self, strategy_id: str):
        connection = self.connections.pop(strategy_id, None)
        if connection:
            await connection.close() 

    async def send_message(self, strategy_id: str, message: str):
        connection = self.connections.get(strategy_id)
        print ("connections : ",connection)
        if connection:
            await connection.send_text(message) 

    async def send_json(self, strategy_id: str, data: dict):
        """Send a JSON message to a specific connection."""
        connection = self.connections.get(strategy_id)
        if not connection:
            raise WebSocketException(detail="No active connection for this strategy_id")
        try:
            await connection.send_json(data)
        except Exception as e:
            print(f"Error sending JSON: {e}")

    async def broadcast_message(self, message: str):
        """Send a text message to all active WebSocket connections."""
        for strategy_id, connection in list(self.connections.items()):
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error broadcasting message to {strategy_id}: {e}")

    async def close_all_connections(self):
        """ close all active connections."""
        for strategy_id, connection in list(self.connections.items()):
            try:
                await connection.close()
            except Exception as e:
                print(f"Error closing connection {strategy_id}: {e}")
        self.connections.clear()

    def get_active_connections(self) -> List[str]:
        """Return a list of active connection IDs."""
        return list(self.connections.keys())

    def is_connected(self, strategy_id: str) -> bool:
        """Check if a given strategy ID is connected."""
        return strategy_id in self.connections

ws_manager = ConnectionManager()