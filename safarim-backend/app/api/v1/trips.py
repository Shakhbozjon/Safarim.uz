from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.enums import PaymentType
from app.schemas.trip import TripCreate, TripResponse, TripSearchParams, CancelTripRequest, DuplicateTripRequest
from app.services import trip_service
from app.core.dependencies import get_current_user, get_current_driver

router = APIRouter()


@router.post(
    "/",
    response_model=TripResponse,
    status_code=201,
    summary="Yangi safar e'lon qilish",
)
async def create_trip(
    data: TripCreate,
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    trip = await trip_service.create_trip(db, current_user, data)
    return trip_service.serialize_trip(trip)


@router.get(
    "/search",
    response_model=list[TripResponse],
    summary="Safarlarni qidirish",
)
async def search_trips(
    from_region_id: int = Query(..., description="Qayerdan (viloyat ID)"),
    to_region_id: int = Query(..., description="Qayerga (viloyat ID)"),
    departure_date: date = Query(..., description="Sana (YYYY-MM-DD)"),
    seats: int = Query(1, ge=1, le=4, description="O'rinlar soni"),
    payment_type: PaymentType | None = Query(None, description="To'lov turi"),
    women_only: bool | None = Query(None, description="Faqat ayollar"),
    max_price: int | None = Query(None, description="Maksimal narx (so'm)"),
    sort: str = Query("time_asc", description="Saralash: time_asc | price_asc | price_desc"),
    db: AsyncSession = Depends(get_db),
):
    params = TripSearchParams(
        from_region_id=from_region_id,
        to_region_id=to_region_id,
        departure_date=departure_date,
        seats=seats,
        payment_type=payment_type,
        women_only=women_only,
        max_price=max_price,
        sort=sort,
    )
    trips = await trip_service.search_trips(db, params)
    return [trip_service.serialize_trip(t) for t in trips]


@router.get(
    "/my",
    response_model=list[TripResponse],
    summary="Mening safarlarim (haydovchi)",
)
async def get_my_trips(
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    trips = await trip_service.get_my_trips(db, current_user)
    return [trip_service.serialize_trip(t) for t in trips]


@router.get(
    "/share/{token}",
    response_model=TripResponse,
    summary="Havola orqali safar ko'rish (login shart emas)",
)
async def get_trip_by_share_token(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    trip = await trip_service.get_trip_by_share_token(db, token)
    return trip_service.serialize_trip(trip)


@router.get(
    "/{trip_id}",
    response_model=TripResponse,
    summary="Safar tafsilotlari",
)
async def get_trip(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
):
    trip = await trip_service.get_trip(db, trip_id)
    return trip_service.serialize_trip(trip)


@router.delete(
    "/{trip_id}",
    response_model=TripResponse,
    summary="Safarni bekor qilish",
)
async def cancel_trip(
    trip_id: str,
    data: CancelTripRequest = CancelTripRequest(),
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    trip = await trip_service.cancel_trip(db, trip_id, current_user, data.reason)
    return trip_service.serialize_trip(trip)


@router.post(
    "/{trip_id}/duplicate",
    response_model=TripResponse,
    status_code=201,
    summary="Eski safarni yangi sana bilan qayta e'lon qilish",
)
async def duplicate_trip(
    trip_id: str,
    data: DuplicateTripRequest,
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    trip = await trip_service.duplicate_trip(
        db, current_user, trip_id, data.departure_date, data.departure_time
    )
    return trip_service.serialize_trip(trip)
