import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.enums import TalkLevel, AdminRole


class UserResponse(BaseModel):
    id: uuid.UUID
    phone: str
    email: str | None
    full_name: str
    profile_photo: str | None
    talk_level: TalkLevel
    is_phone_verified: bool
    is_driver: bool
    is_admin: bool
    admin_role: AdminRole | None
    is_blocked: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserPublicResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    profile_photo: str | None
    talk_level: TalkLevel
    created_at: datetime

    model_config = {"from_attributes": True}
