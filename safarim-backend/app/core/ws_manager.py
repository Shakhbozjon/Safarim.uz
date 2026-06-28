import json
from fastapi import WebSocket


class ConnectionManager:
    """
    WebSocket ulanishlarni boshqarish.
    Har bir booking uchun alohida xona (room).
    """

    def __init__(self):
        # { booking_id: { user_id: WebSocket } }
        self.rooms: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, booking_id: str, user_id: str) -> None:
        await websocket.accept()
        if booking_id not in self.rooms:
            self.rooms[booking_id] = {}
        self.rooms[booking_id][user_id] = websocket

    def disconnect(self, booking_id: str, user_id: str) -> None:
        if booking_id in self.rooms:
            self.rooms[booking_id].pop(user_id, None)
            if not self.rooms[booking_id]:
                del self.rooms[booking_id]

    def is_online(self, booking_id: str, user_id: str) -> bool:
        return user_id in self.rooms.get(booking_id, {})

    async def send_to_room(
        self,
        booking_id: str,
        data: dict,
        exclude_user_id: str | None = None,
    ) -> None:
        """Booking xonasidagi barcha online foydalanuvchilarga xabar yuborish."""
        room = self.rooms.get(booking_id, {})
        dead = []
        for uid, ws in room.items():
            if uid == exclude_user_id:
                continue
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.disconnect(booking_id, uid)

    async def send_to_user(self, booking_id: str, user_id: str, data: dict) -> None:
        """Bitta foydalanuvchiga xabar yuborish."""
        ws = self.rooms.get(booking_id, {}).get(user_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(booking_id, user_id)


# Global instance — butun app boyicha bitta
ws_manager = ConnectionManager()
