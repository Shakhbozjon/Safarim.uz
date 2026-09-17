"""«Safarni boshlash» safarni qidiruvdan olib tashlaydi.

Aynan user aytgan stsenariy: haydovchi e'lon beradi → bitta yo'lovchi band
qiladi → haydovchi «Safarni boshlash» ni bosadi. Shundan keyin safar bo'sh
o'rni qolgan bo'lsa ham qidiruvda chiqmasligi kerak — mashina yo'lga chiqqan,
yangi yo'lovchi uni band qilib kutib qolmasin.
"""
import uuid
from datetime import date, time, timedelta

import pytest

from app.models.enums import (
    BookingStatus, LuggageSize, PaymentMethod, PaymentType, TripStatus,
)
from app.models.location import Region
from app.models.trip import Trip
from app.schemas.booking import BookingCreate
from app.schemas.trip import TripSearchParams
from app.services import booking_service, trip_service

FARGONA, TOSHKENT = 501, 502
TOMORROW = date.today() + timedelta(days=1)


async def _regions(db) -> None:
    db.add_all([
        Region(id=FARGONA, name_uz="Farg'ona viloyati", name_ru="Фергана", slug="fargona-s", order=1),
        Region(id=TOSHKENT, name_uz="Toshkent shahri", name_ru="Ташкент", slug="toshkent-s", order=2),
    ])
    await db.commit()


async def _trip(db, driver) -> Trip:
    trip = Trip(
        id=uuid.uuid4(),
        driver_id=driver.id,
        from_region_id=FARGONA,
        to_region_id=TOSHKENT,
        departure_date=TOMORROW,
        departure_time=time(8, 0),
        total_seats=4,
        available_seats=4,
        price_per_seat=120000,
        payment_type=PaymentType.cash,
        luggage_size=LuggageSize.medium,
        status=TripStatus.active,
    )
    db.add(trip)
    await db.commit()
    return trip


def _search() -> TripSearchParams:
    return TripSearchParams(
        from_region_id=FARGONA,
        to_region_id=TOSHKENT,
        departure_date=TOMORROW,
        seats=1,
    )


@pytest.mark.asyncio
async def test_boshlangan_safar_qidiruvdan_yoqoladi(db, user, driver_user):
    driver, _dp = driver_user
    await _regions(db)
    trip = await _trip(db, driver)

    # 1) E'londan keyin — qidiruvda bor
    found = await trip_service.search_trips(db, _search())
    assert [t.id for t in found] == [trip.id]

    # 2) Bitta yo'lovchi band qildi — o'rin kamaydi, lekin safar hali qidiruvda
    booking = await booking_service.create_booking(db, user, BookingCreate(
        trip_id=trip.id,
        seats_count=1,
        payment_method=PaymentMethod.cash,
        pickup_address="Buvayda markazi",
    ))
    assert booking.status == BookingStatus.confirmed   # carpooling'da avto-tasdiq

    await db.refresh(trip)
    assert trip.available_seats == 3
    found = await trip_service.search_trips(db, _search())
    assert [t.id for t in found] == [trip.id], "band qilingan, lekin o'rin bor — chiqishi kerak"

    # 3) Haydovchi safarni boshladi
    await trip_service.start_trip(db, str(trip.id), driver)

    await db.refresh(trip)
    assert trip.status == TripStatus.started
    assert trip.available_seats == 3, "bo'sh o'rin baribir qoldi"

    # 4) Endi qidiruvda YO'Q — mashina yo'lga chiqqan
    found = await trip_service.search_trips(db, _search())
    assert found == [], "boshlangan safar qidiruvda ko'rinmasligi kerak"


@pytest.mark.asyncio
async def test_yolovchisiz_safarni_boshlab_bolmaydi(db, driver_user):
    """Bo'sh safar «started» bo'lib qolsa — u qidiruvdan ham yo'qoladi,
    yangi bron ham qabul qilmaydi, ya'ni o'lik qoladi."""
    from fastapi import HTTPException

    driver, _dp = driver_user
    await _regions(db)
    trip = await _trip(db, driver)

    with pytest.raises(HTTPException) as err:
        await trip_service.start_trip(db, str(trip.id), driver)

    assert err.value.status_code == 400
    await db.refresh(trip)
    assert trip.status == TripStatus.active


@pytest.mark.asyncio
async def test_boshlangan_safarga_yangi_bron_qabul_qilinmaydi(db, user, driver_user):
    """Qidiruvda ko'rinmasa ham, havola orqali kirib band qilib bo'lmasin."""
    from fastapi import HTTPException

    driver, _dp = driver_user
    await _regions(db)
    trip = await _trip(db, driver)

    await booking_service.create_booking(db, user, BookingCreate(
        trip_id=trip.id, seats_count=1,
        payment_method=PaymentMethod.cash, pickup_address="Buvayda markazi",
    ))
    await trip_service.start_trip(db, str(trip.id), driver)

    with pytest.raises(HTTPException):
        await booking_service.create_booking(db, user, BookingCreate(
            trip_id=trip.id, seats_count=1,
            payment_method=PaymentMethod.cash, pickup_address="Buvayda markazi",
        ))
