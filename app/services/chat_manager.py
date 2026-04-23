from typing import Dict
from fastapi import WebSocket

class ChatManager:
    def __init__(self):
        # { user_id: websocket }
        self.active: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active[user_id] = websocket

    def disconnect(self, user_id: int):
        self.active.pop(user_id, None)

    def is_online(self, user_id: int) -> bool:
        return user_id in self.active

    async def send_to_user(self, user_id: int, payload: dict):
        """Send a message to a specific user if they are connected."""
        ws = self.active.get(user_id)
        if ws:
            await ws.send_json(payload)

chat_manager = ChatManager()