import uuid
from datetime import date, time, datetime
from pydantic import BaseModel, field_validator
from app.models.enums import PaymentType, TripStatus, LuggageSize, TalkLevel


class LocationBrief(BaseModel):
    id: int
    name_uz: str
    name_ru: str
    model_config = {"from_attributes": True}


class WaypointCreate(BaseModel):
    region_id: int
    district_id: int | None = None
    address: str | None = None
    order_index: int
    price_from_start: int  # boshlanishdan shu nuqtagacha narx (so'm)
    arrival_time: str | None = None  # "HH:MM"


class WaypointResponse(BaseModel):
    id: uuid.UUID
    region: LocationBrief
    district: LocationBrief | None
    address: str | None
    order_index: int
    price_from_start: int
    arrival_time: time | None
    model_config = {"from_attributes": True}


class TripDriverInfo(BaseModel):
    id: uuid.UUID
    full_name: str
    profile_photo: str | None
    talk_level: TalkLevel
    rating_avg: float
    rating_count: int
    total_trips: int


class TripCreate(BaseModel):
    from_region_id: int
    from_district_id: int | None = None
    from_address: str | None = None
    to_region_id: int
    to_district_id: int | None = None
    to_address: str | None = None
    departure_date: date
    departure_time: str  # "HH:MM"
    total_seats: int
    price_per_seat: int
    payment_type: PaymentType = PaymentType.any
    smoking_allowed: bool = False
    pets_allowed: bool = False
    women_only: bool = False
    luggage_size: LuggageSize = LuggageSize.medium
    description: str | None = None
    waypoints: list[WaypointCreate] | None = None

    @field_validator("departure_date")
    @classmethod
    def validate_date(cls, v: date) -> date:
        from datetime import date as d
        if v < d.today():
            raise ValueError("Safar sanasi o'tib ketgan")
        return v

    @field_validator("price_per_seat")
    @classmethod
    def validate_price(cls, v: int) -> int:
        if v < 1_000:
            raise ValueError("Narx kamida 1,000 so'm bo'lishi kerak")
        return v

    @field_validator("total_seats")
    @classmethod
    def validate_seats(cls, v: int) -> int:
        if v < 1 or v > 8:
            raise ValueError("O'rinlar soni 1–8 oralig'ida bo'lishi kerak")
        return v

    @field_validator("departure_time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            time.fromisoformat(v)
        except ValueError:
            raise ValueError("Vaqt HH:MM formatida bo'lishi kerak")
        return v

    @field_validator("from_region_id", "to_region_id")
    @classmethod
    def validate_regions_different(cls, v: int) -> int:
        return v


class TripResponse(BaseModel):
    id: uuid.UUID
    driver: TripDriverInfo
    from_region: LocationBrief
    from_district: LocationBrief | None
    from_address: str | None
    to_region: LocationBrief
    to_district: LocationBrief | None
    to_address: str | None
    departure_date: date
    departure_time: time
    total_seats: int
    available_seats: int
    price_per_seat: int
    payment_type: PaymentType
    smoking_allowed: bool
    pets_allowed: bool
    women_only: bool
    luggage_size: LuggageSize
    description: str | None
    has_waypoints: bool
    waypoints: list[WaypointResponse]
    status: TripStatus
    share_token: str
    created_at: datetime


class TripSearchParams(BaseModel):
    from_region_id: int
    to_region_id: int
    departure_date: date
    seats: int = 1
    payment_type: PaymentType | None = None
    women_only: bool | None = None
    max_price: int | None = None
    sort: str = "time_asc"  # time_asc | price_asc | price_desc | rating_desc


class CancelTripRequest(BaseModel):
    reason: str | None = None


class DuplicateTripRequest(BaseModel):
    """Eski safarni yangi sana bilan qayta e'lon qilish."""
    departure_date: date
    departure_time: str | None = None  # "HH:MM" — berilmasa eski vaqt ishlatiladi

    @field_validator("departure_date")
    @classmethod
    def date_not_past(cls, v: date) -> date:
        from datetime import date as _date
        if v < _date.today():
            raise ValueError("Sana o'tmishda bo'lishi mumkin emas")
        return v
