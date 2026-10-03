from datetime import date, time
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.enums import PaymentType
from app.schemas.trip import (
    TripCreate, TripResponse, TripSearchParams, CancelTripRequest,
    DuplicateTripRequest, PopularRoute,
)
from app.services import trip_service
from app.core.dependencies import get_current_user, get_current_driver

router = APIRouter()

# Qidiruv natijasi shu bo'laklarda beriladi; «Yana ko'rsatish» keyingisini oladi
SEARCH_PAGE_SIZE = 20
SEARCH_MAX_PAGE_SIZE = 50


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
    response: Response,
    from_region_id: int = Query(..., description="Qayerdan (viloyat ID)"),
    to_region_id: int = Query(..., description="Qayerga (viloyat ID)"),
    from_district_id: int | None = Query(None, description="Qayerdan (tuman ID) — berilmasa barcha tumanlar"),
    to_district_id: int | None = Query(None, description="Qayerga (tuman ID) — berilmasa barcha tumanlar"),
    departure_date: date = Query(..., description="Sana (YYYY-MM-DD)"),
    seats: int = Query(1, ge=1, le=4, description="O'rinlar soni"),
    payment_type: PaymentType | None = Query(None, description="To'lov turi"),
    women_only: bool | None = Query(None, description="Faqat ayollar"),
    max_price: int | None = Query(None, description="Maksimal narx (so'm)"),
    departure_from: time | None = Query(None, description="Jo'nash vaqti shundan (HH:MM)"),
    departure_to: time | None = Query(None, description="Jo'nash vaqti shugacha (HH:MM, daqiqa oxirigacha)"),
    min_rating: float | None = Query(None, ge=0, le=5, description="Haydovchi reytingi kamida"),
    large_luggage: bool | None = Query(None, description="Faqat katta yuk sig'adigan safarlar"),
    sort: str = Query("time_asc", description="Saralash: time_asc | price_asc | price_desc"),
    limit: int = Query(SEARCH_PAGE_SIZE, ge=1, le=SEARCH_MAX_PAGE_SIZE, description="Sahifadagi safarlar soni"),
    offset: int = Query(0, ge=0, description="Shuncha safar o'tkazib yuboriladi"),
    db: AsyncSession = Depends(get_db),
):
    """Javob — safarlar ro'yxati (bir sahifa). Umumiy son `X-Total-Count`
    sarlavhasida: «N ta safar» va «yana bormi» shundan bilinadi."""
    params = TripSearchParams(
        from_region_id=from_region_id,
        to_region_id=to_region_id,
        from_district_id=from_district_id,
        to_district_id=to_district_id,
        departure_date=departure_date,
        seats=seats,
        payment_type=payment_type,
        women_only=women_only,
        max_price=max_price,
        departure_from=departure_from,
        departure_to=departure_to,
        min_rating=min_rating,
        large_luggage=large_luggage,
        sort=sort,
    )
    trips = await trip_service.search_trips(db, params, limit=limit, offset=offset)
    # Birinchi sahifa to'lmagan bo'lsa — son ma'lum, qo'shimcha so'rov shart emas
    if offset == 0 and len(trips) < limit:
        total = len(trips)
    else:
        total = await trip_service.count_search(db, params)
    response.headers["X-Total-Count"] = str(total)
    return [trip_service.serialize_trip(t) for t in trips]


@router.get(
    "/nearest-dates",
    summary="Yaqin kunlardagi safarli sanalar (bo'sh natija uchun)",
)
async def nearest_dates(
    from_region_id: int = Query(..., description="Qayerdan (viloyat ID)"),
    to_region_id: int = Query(..., description="Qayerga (viloyat ID)"),
    from_district_id: int | None = Query(None, description="Qayerdan (tuman ID)"),
    to_district_id: int | None = Query(None, description="Qayerga (tuman ID)"),
    after: date = Query(..., description="Shu sanadan keyingi kunlar"),
    seats: int = Query(1, ge=1, le=4),
    db: AsyncSession = Depends(get_db),
):
    return await trip_service.nearest_dates(
        db, from_region_id, to_region_id, after, seats,
        from_district_id=from_district_id,
        to_district_id=to_district_id,
    )


@router.get(
    "/my",
    response_model=list[TripResponse],
    summary="Mening safarlarim (haydovchi)",
)
async def get_my_trips(
    past_limit: int = Query(trip_service.DEFAULT_PAST_LIMIT, ge=1, le=trip_service.MAX_PAST_LIMIT,
                            description="Tugagan safarlardan nechtasi (faollari doim to'liq)"),
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    trips = await trip_service.get_my_trips(db, current_user, past_limit)
    return [trip_service.serialize_trip(t) for t in trips]


@router.get(
    "/popular-routes",
    response_model=list[PopularRoute],
    summary="Ommabop yo'nalishlar (kelgusi safarlar bo'yicha)",
)
async def popular_routes(
    limit: int = Query(6, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
):
    return await trip_service.popular_routes(db, limit)


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
        db, current_user, trip_id, data.departure_date, data.departure_time,
        data.reverse, data.confirm_day_conflict,
    )
    return trip_service.serialize_trip(trip)


@router.post(
    "/{trip_id}/start",
    response_model=TripResponse,
    summary="Safarni boshlash — qidiruvdan olib tashlanadi, yangi bron yo'q",
)
async def start_trip(
    trip_id: str,
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    trip = await trip_service.start_trip(db, trip_id, current_user)
    return trip_service.serialize_trip(trip)
