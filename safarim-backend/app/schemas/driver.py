import uuid
from datetime import datetime
from pydantic import BaseModel, field_validator
from app.models.enums import DriverStatus, LuggageSize
from app.schemas.user import UserPublicResponse
from app.core.validators import validate_uz_plate


class DriverApplyRequest(BaseModel):
    vehicle_make: str
    vehicle_model: str
    vehicle_year: int
    vehicle_color: str
    vehicle_plate: str
    vehicle_seats: int

    @field_validator("vehicle_year")
    @classmethod
    def validate_year(cls, v: int) -> int:
        if v < 1990 or v > datetime.now().year + 1:
            raise ValueError("Avtomobil yili noto'g'ri")
        return v

    @field_validator("vehicle_seats")
    @classmethod
    def validate_seats(cls, v: int) -> int:
        if v < 1 or v > 8:
            raise ValueError("O'rinlar soni 1 dan 8 gacha bo'lishi kerak")
        return v

    @field_validator("vehicle_plate")
    @classmethod
    def validate_plate(cls, v: str) -> str:
        # O'zbekiston formatiga tekshiradi va normallashtiradi (01A123BC)
        return validate_uz_plate(v)


class UpdatePreferencesRequest(BaseModel):
    smoking_allowed: bool | None = None
    pets_allowed: bool | None = None
    music_allowed: bool | None = None
    luggage_size: LuggageSize | None = None
    women_only: bool | None = None


class DriverProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    vehicle_make: str
    vehicle_model: str
    vehicle_year: int
    vehicle_color: str
    vehicle_plate: str
    vehicle_seats: int
    smoking_allowed: bool
    pets_allowed: bool
    music_allowed: bool
    luggage_size: LuggageSize
    women_only: bool
    status: DriverStatus
    rejection_reason: str | None
    rating_avg: float
    rating_count: int
    total_trips: int
    warning_count: int
    is_on_pause: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DriverPublicResponse(BaseModel):
    """Safar qidiruvda ko'rinadigan haydovchi ma'lumoti."""
    id: uuid.UUID
    user_id: uuid.UUID
    vehicle_make: str
    vehicle_model: str
    vehicle_color: str
    vehicle_seats: int
    smoking_allowed: bool
    pets_allowed: bool
    music_allowed: bool
    luggage_size: LuggageSize
    women_only: bool
    rating_avg: float
    rating_count: int
    total_trips: int
    user: UserPublicResponse

    model_config = {"from_attributes": True}


class DriverStatusResponse(BaseModel):
    status: DriverStatus
    rejection_reason: str | None
    message: str


class EarningsResponse(BaseModel):
    month: str
    total_cash_bookings: int
    total_commission: int
    is_paid: bool


class AdminDriverListResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    vehicle_plate: str
    vehicle_make: str
    vehicle_model: str
    status: DriverStatus
    created_at: datetime
    user: UserPublicResponse

    model_config = {"from_attributes": True}


class RejectDriverRequest(BaseModel):
    reason: str
