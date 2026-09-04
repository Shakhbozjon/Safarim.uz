import uuid
from datetime import date, time
from pydantic import BaseModel, field_validator

from app.models.enums import PaymentType, LuggageSize
from app.schemas.trip import LocationBrief, TripResponse


def _valid_time(v: str | None) -> str | None:
    if v is None:
        return None
    try:
        time.fromisoformat(v)
    except ValueError:
        raise ValueError("Vaqt HH:MM formatida bo'lishi kerak")
    return v


class DriverRouteResponse(BaseModel):
    """Haydovchining doimiy yo'nalishi — panel kartasi shundan chiziladi."""
    id: uuid.UUID
    from_region: LocationBrief
    from_district: LocationBrief | None
    from_address: str | None
    to_region: LocationBrief
    to_district: LocationBrief | None
    to_address: str | None
    departure_time: time
    return_time: time | None
    total_seats: int
    price_per_seat: int
    payment_type: PaymentType
    smoking_allowed: bool
    pets_allowed: bool
    women_only: bool
    luggage_size: LuggageSize
    description: str | None


class DriverRouteUpdate(BaseModel):
    """Panel kartasidagi ✎ — faqat berilgan maydonlar o'zgaradi."""
    from_region_id: int | None = None
    from_district_id: int | None = None
    from_address: str | None = None
    to_region_id: int | None = None
    to_district_id: int | None = None
    to_address: str | None = None
    departure_time: str | None = None
    return_time: str | None = None
    total_seats: int | None = None
    price_per_seat: int | None = None

    @field_validator("departure_time", "return_time")
    @classmethod
    def validate_times(cls, v: str | None) -> str | None:
        return _valid_time(v)

    @field_validator("total_seats")
    @classmethod
    def validate_seats(cls, v: int | None) -> int | None:
        if v is not None and (v < 1 or v > 8):
            raise ValueError("O'rinlar soni 1–8 oralig'ida bo'lishi kerak")
        return v

    @field_validator("price_per_seat")
    @classmethod
    def validate_price(cls, v: int | None) -> int | None:
        if v is not None and v < 1_000:
            raise ValueError("Narx kamida 1,000 so'm bo'lishi kerak")
        return v


class RoutePublishRequest(BaseModel):
    """Doimiy yo'nalishni bir sanaga e'lon qilish.

    Narx tez-tez o'zgargani uchun u har safar tasdiqlanadi — berilmasa
    shablondagi oxirgi narx ishlatiladi.
    """
    departure_date: date
    departure_time: str | None = None
    price_per_seat: int | None = None
    total_seats: int | None = None

    # Qaytish safari — sana berilmasa o'zi hisoblanadi (qaytish vaqti borish
    # vaqtidan kichik bo'lsa ertasi kuni)
    include_return: bool = False
    return_date: date | None = None
    return_time: str | None = None
    return_price: int | None = None

    @field_validator("departure_time", "return_time")
    @classmethod
    def validate_times(cls, v: str | None) -> str | None:
        return _valid_time(v)

    @field_validator("departure_date")
    @classmethod
    def validate_date(cls, v: date) -> date:
        from datetime import date as d
        if v < d.today():
            raise ValueError("Safar sanasi o'tib ketgan")
        return v


class RoutePublishResponse(BaseModel):
    """E'lon qilingan safarlar. Borish chiqib, qaytish chiqmasa (masalan o'sha
    kunga allaqachon safar bor) — `warning` da sababi qaytadi."""
    trips: list[TripResponse]
    warning: str | None = None
