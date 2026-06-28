import uuid
from datetime import datetime
from pydantic import BaseModel


class MessageSenderInfo(BaseModel):
    id: uuid.UUID
    full_name: str
    profile_photo: str | None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    sender: MessageSenderInfo
    content: str
    is_read: bool
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    booking_id: uuid.UUID
    unread_count: int


class WsIncoming(BaseModel):
    """WebSocket orqali keluvchi xabar formati."""
    content: str


class WsOutgoing(BaseModel):
    """WebSocket orqali ketuvchi xabar formati."""
    type: str          # "message" | "read" | "error" | "online_status"
    data: dict
