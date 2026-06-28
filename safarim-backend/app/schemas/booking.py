import uuid
from datetime import datetime
from pydantic import BaseModel, field_validator
from app.models.enums import BookingStatus, BookingPaymentStatus, PaymentMethod, CancelledBy
from app.schemas.trip import TripResponse


class BookingCreate(BaseModel):
    trip_id: uuid.UUID
    seats_count: int = 1
    payment_method: PaymentMethod
    from_waypoint_id: uuid.UUID | None = None
    to_waypoint_id: uuid.UUID | None = None

    @field_validator("seats_count")
    @classmethod
    def validate_seats(cls, v: int) -> int:
        if v < 1 or v > 4:
            raise ValueError("O'rinlar soni 1 dan 4 tagacha bo'lishi kerak")
        return v


class BookingPassengerInfo(BaseModel):
    id: uuid.UUID
    full_name: str
    phone: str | None  # faqat booking tasdiqlanganidan keyin
    profile_photo: str | None

    model_config = {"from_attributes": True}


class BookingResponse(BaseModel):
    id: uuid.UUID
    trip_id: uuid.UUID
    passenger: BookingPassengerInfo
    seats_count: int
    price_per_seat: int
    total_price: int
    commission_rate: float
    commission_amount: int
    driver_amount: int
    payment_method: PaymentMethod
    payment_status: BookingPaymentStatus
    status: BookingStatus
    cancelled_by: CancelledBy | None
    cancellation_reason: str | None
    cancelled_at: datetime | None
    refund_amount: int | None
    no_show_reported_at: datetime | None
    completed_at: datetime | None

    # Ikki tomonlama safar tasdiqi ('yes' / 'no' / None=jim)
    driver_confirmed: str | None = None
    passenger_confirmed: str | None = None
    confirmation_requested_at: datetime | None = None
    needs_my_confirmation: bool = False

    created_at: datetime

    # Telefon faqat confirmed/completed da ko'rinadi
    driver_phone: str | None = None

    model_config = {"from_attributes": True}


class BookingDetailResponse(BookingResponse):
    trip: TripResponse


class CancelBookingRequest(BaseModel):
    reason: str | None = None


class ConfirmBookingRequest(BaseModel):
    confirmed: bool   # True = safar bo'ldi, False = bo'lmadi
