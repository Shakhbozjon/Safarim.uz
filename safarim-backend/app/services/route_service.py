"""Haydovchining doimiy yo'nalishi — shablon va undan safar e'lon qilish.

Yo'nalish tarixdan taxmin qilinmaydi: haydovchi safar e'lon qilishda
"bu mening doimiy yo'nalishim" deb belgilaydi, keyin panelda bir bosishda
(narxni tasdiqlab) qayta e'lon qiladi.
"""
from datetime import date, time, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.route import DriverRoute
from app.models.trip import Trip
from app.models.user import User
from app.schemas.route import DriverRouteResponse, DriverRouteUpdate, RoutePublishRequest
from app.schemas.trip import LocationBrief, TripCreate, WaypointCreate


def _load_options():
    return [
        selectinload(DriverRoute.from_region),
        selectinload(DriverRoute.from_district),
        selectinload(DriverRoute.to_region),
        selectinload(DriverRoute.to_district),
    ]


def _brief(loc) -> LocationBrief | None:
    if loc is None:
        return None
    return LocationBrief(id=loc.id, name_uz=loc.name_uz, name_ru=loc.name_ru)


def serialize(route: DriverRoute) -> DriverRouteResponse:
    return DriverRouteResponse(
        id=route.id,
        from_region=_brief(route.from_region),
        from_district=_brief(route.from_district),
        from_address=route.from_address,
        to_region=_brief(route.to_region),
        to_district=_brief(route.to_district),
        to_address=route.to_address,
        total_seats=route.total_seats,
        price_per_seat=route.price_per_seat,
        payment_type=route.payment_type,
        smoking_allowed=route.smoking_allowed,
        pets_allowed=route.pets_allowed,
        women_only=route.women_only,
        luggage_size=route.luggage_size,
        description=route.description,
    )


async def get_route(db: AsyncSession, user: User) -> DriverRoute | None:
    result = await db.execute(
        select(DriverRoute).options(*_load_options()).where(DriverRoute.driver_id == user.id)
    )
    return result.scalar_one_or_none()


async def _reload(db: AsyncSession, route_id) -> DriverRoute:
    result = await db.execute(
        select(DriverRoute).options(*_load_options()).where(DriverRoute.id == route_id)
    )
    return result.scalar_one()


async def upsert_from_trip(db: AsyncSession, user: User, trip: Trip) -> DriverRoute:
    """Yangi e'lon qilingan safarni doimiy yo'nalish shabloniga aylantiradi.

    Haydovchida bitta yo'nalish — mavjudi bo'lsa ustiga yoziladi (oxirgi
    e'lon eng dolzarb: narx ham, vaqt ham).
    """
    waypoints = [
        {
            "region_id": wp.region_id,
            "district_id": wp.district_id,
            "address": wp.address,
            "order_index": wp.order_index,
            "price_from_start": wp.price_from_start,
            "arrival_time": wp.arrival_time.isoformat() if wp.arrival_time else None,
        }
        for wp in sorted(trip.waypoints, key=lambda w: w.order_index)
    ] or None

    route = await get_route(db, user)
    if route is None:
        route = DriverRoute(driver_id=user.id)
        db.add(route)

    route.from_region_id = trip.from_region_id
    route.from_district_id = trip.from_district_id
    route.from_address = trip.from_address
    route.to_region_id = trip.to_region_id
    route.to_district_id = trip.to_district_id
    route.to_address = trip.to_address
    # Vaqt saqlanmaydi — har e'londa haydovchi o'zi kiritadi
    route.departure_time = None
    route.return_time = None
    route.total_seats = trip.total_seats
    route.price_per_seat = trip.price_per_seat
    route.payment_type = trip.payment_type
    route.smoking_allowed = trip.smoking_allowed
    route.pets_allowed = trip.pets_allowed
    route.women_only = trip.women_only
    route.luggage_size = trip.luggage_size
    route.description = trip.description
    route.waypoints = waypoints

    await db.commit()
    return await _reload(db, route.id)


async def update_route(db: AsyncSession, user: User, data: DriverRouteUpdate) -> DriverRoute:
    route = await get_route(db, user)
    if not route:
        raise HTTPException(status_code=404, detail="Doimiy yo'nalish belgilanmagan")

    fields = data.model_dump(exclude_unset=True)

    # Yo'nalish o'zgarsa oraliq to'xtashlar eskirib qoladi
    if any(k in fields for k in ("from_region_id", "to_region_id")):
        route.waypoints = None

    for key, value in fields.items():
        setattr(route, key, value)

    if route.from_region_id == route.to_region_id:
        raise HTTPException(status_code=400, detail="Qayerdan va qayerga bir xil bo'lishi mumkin emas")

    await db.commit()
    return await _reload(db, route.id)


async def delete_route(db: AsyncSession, user: User) -> None:
    route = await get_route(db, user)
    if not route:
        raise HTTPException(status_code=404, detail="Doimiy yo'nalish belgilanmagan")
    await db.delete(route)
    await db.commit()


def _waypoints_for_trip(route: DriverRoute) -> list[WaypointCreate] | None:
    if not route.waypoints:
        return None
    return [
        WaypointCreate(
            region_id=wp["region_id"],
            district_id=wp.get("district_id"),
            address=wp.get("address"),
            order_index=wp["order_index"],
            price_from_start=wp.get("price_from_start", 0),
            arrival_time=wp.get("arrival_time"),
        )
        for wp in sorted(route.waypoints, key=lambda w: w["order_index"])
    ]


def _default_return_date(dep_date: date, dep_time: time, ret_time: time) -> date:
    """Qaytish vaqti borish vaqtidan kichik bo'lsa — ertasi kuni (17:00 → 06:00)."""
    return dep_date + timedelta(days=1) if ret_time <= dep_time else dep_date


async def publish(
    db: AsyncSession, user: User, data: RoutePublishRequest
) -> tuple[list[Trip], str | None]:
    """Shablondan 1 yoki 2 ta safar e'lon qiladi (borish + ixtiyoriy qaytish).

    Barcha tekshiruvlar (tasdiqlangan haydovchi, pauza, o'rin soni, shu kunda
    takroriy safar) `trip_service.create_trip` ichida — shu sababli aynan
    o'sha yo'ldan yuriladi.
    """
    from app.services import trip_service  # aylanma importni oldini olish

    route = await get_route(db, user)
    if not route:
        raise HTTPException(status_code=404, detail="Doimiy yo'nalish belgilanmagan")

    dep_time = time.fromisoformat(data.departure_time)
    seats = data.total_seats or route.total_seats
    price = data.price_per_seat or route.price_per_seat

    trips: list[Trip] = []

    trips.append(await trip_service.create_trip(db, user, TripCreate(
        from_region_id=route.from_region_id,
        from_district_id=route.from_district_id,
        from_address=route.from_address,
        to_region_id=route.to_region_id,
        to_district_id=route.to_district_id,
        to_address=route.to_address,
        departure_date=data.departure_date,
        departure_time=dep_time.strftime("%H:%M"),
        total_seats=seats,
        price_per_seat=price,
        payment_type=route.payment_type,
        smoking_allowed=route.smoking_allowed,
        pets_allowed=route.pets_allowed,
        women_only=route.women_only,
        luggage_size=route.luggage_size,
        description=route.description,
        waypoints=_waypoints_for_trip(route),
    )))

    if not data.include_return:
        return trips, None

    if not data.return_time:
        raise HTTPException(status_code=400, detail="Qaytish vaqtini kiriting")
    ret_time = time.fromisoformat(data.return_time)

    ret_date = data.return_date or _default_return_date(data.departure_date, dep_time, ret_time)

    # Borish safari allaqachon yaratilgan — qaytish rad etilsa butun amalni
    # xatoga chiqarmaymiz, sababini ogohlantirish sifatida qaytaramiz.
    try:
        # Qaytish — teskari yo'nalish. Oraliq to'xtashlar ko'chirilmaydi:
        # qaytishda narxlar boshqacha bo'ladi, haydovchi o'zi qo'shadi.
        trips.append(await trip_service.create_trip(db, user, TripCreate(
            from_region_id=route.to_region_id,
            from_district_id=route.to_district_id,
            from_address=route.to_address,
            to_region_id=route.from_region_id,
            to_district_id=route.from_district_id,
            to_address=route.from_address,
            departure_date=ret_date,
            departure_time=ret_time.strftime("%H:%M"),
            total_seats=seats,
            price_per_seat=data.return_price or price,
            payment_type=route.payment_type,
            smoking_allowed=route.smoking_allowed,
            pets_allowed=route.pets_allowed,
            women_only=route.women_only,
            luggage_size=route.luggage_size,
            description=route.description,
        )))
    except HTTPException as err:
        return trips, f"Qaytish safari e'lon qilinmadi: {err.detail}"

    return trips, None
