"""Safar yakunlangach qidiruvda qolib ketmasin.

User jonli saytda ko'rgan holat (2026-09-17): safarni band qilgan, safar
bo'lgani haqida xabar kelgan, Telegram botdan «bo'ldi» deb tasdiqlagan —
lekin keyin qidirganda o'sha safar yana ro'yxatda turgan.

Ikki alohida sabab bor edi, ikkalasi ham shu yerda qamrab olinadi:

  1. Safar HECH QACHON `completed` bo'lmasdi. `expire_due_trips` real broni
     bor safarga ataylab tegmaydi («tasdiq oqimi yakunlaydi»), tasdiq oqimi
     esa faqat BRONni yopib, safarni `active` holida qoldirardi.

  2. Qidiruv faqat SANAni solishtirardi. Soat 10:55 da jo'nab ketgan mashina
     o'sha kuni yarim tungacha ro'yxatda turaverar va uni band qilish ham
     mumkin edi.
"""
import uuid
from datetime import date, datetime, time, timedelta

import pytest
from fastapi import HTTPException

from app.core.timeutils import now_tashkent_naive
from app.models.enums import (
    BookingStatus, CONFIRM_YES, LuggageSize, PaymentMethod, PaymentType, TripStatus,
)
from app.models.location import Region
from app.models.trip import Trip
from app.schemas.booking import BookingCreate
from app.schemas.trip import TripSearchParams
from app.services import booking_service, trip_service

FARGONA, TOSHKENT = 601, 602


async def _regions(db) -> None:
    db.add_all([
        Region(id=FARGONA, name_uz="Farg'ona viloyati", name_ru="Фергана", slug="fargona-c", order=1),
        Region(id=TOSHKENT, name_uz="Toshkent shahri", name_ru="Ташкент", slug="toshkent-c", order=2),
    ])
    await db.commit()


async def _trip(db, driver, *, when: datetime) -> Trip:
    trip = Trip(
        id=uuid.uuid4(),
        driver_id=driver.id,
        from_region_id=FARGONA,
        to_region_id=TOSHKENT,
        departure_date=when.date(),
        departure_time=when.time(),
        total_seats=4,
        available_seats=4,
        price_per_seat=140000,
        payment_type=PaymentType.cash,
        luggage_size=LuggageSize.medium,
        status=TripStatus.active,
    )
    db.add(trip)
    await db.commit()
    return trip


def _search(when: date) -> TripSearchParams:
    return TripSearchParams(
        from_region_id=FARGONA, to_region_id=TOSHKENT,
        departure_date=when, seats=1,
    )


# ─── 1. Tasdiqlangach safar yopiladi ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_safar_tasdiqlangach_qidiruvda_qolmaydi(db, user, driver_user):
    driver, _dp = driver_user
    await _regions(db)
    # Ertaga jo'naydi — qidiruvdan vaqt sababli tushib qolmasin
    tomorrow = now_tashkent_naive() + timedelta(days=1)
    trip = await _trip(db, driver, when=tomorrow.replace(hour=10, minute=55))

    booking = await booking_service.create_booking(db, user, BookingCreate(
        trip_id=trip.id, seats_count=1,
        payment_method=PaymentMethod.cash, pickup_address="Buvayda markazi",
    ))
    assert await trip_service.search_trips(db, _search(trip.departure_date))

    # Ikki tomon ham «bo'ldi» dedi → bron yakunlanadi
    booking.driver_confirmed = CONFIRM_YES
    await booking_service._apply_completion(db, booking, driver.id)
    await db.commit()

    assert booking.status == BookingStatus.completed
    await db.refresh(trip)
    assert trip.status == TripStatus.completed, "safar ham yopilishi kerak"
    assert await trip_service.search_trips(db, _search(trip.departure_date)) == []


@pytest.mark.asyncio
async def test_bitta_bron_qolsa_safar_yopilmaydi(db, user, admin_user, driver_user):
    """Ikki yo'lovchidan biri tasdiqlamagan bo'lsa safar ochiq qoladi."""
    driver, _dp = driver_user
    await _regions(db)
    tomorrow = now_tashkent_naive() + timedelta(days=1)
    trip = await _trip(db, driver, when=tomorrow.replace(hour=10, minute=55))

    first = await booking_service.create_booking(db, user, BookingCreate(
        trip_id=trip.id, seats_count=1,
        payment_method=PaymentMethod.cash, pickup_address="Buvayda",
    ))
    await booking_service.create_booking(db, admin_user, BookingCreate(
        trip_id=trip.id, seats_count=1,
        payment_method=PaymentMethod.cash, pickup_address="Qo'qon",
    ))

    first.driver_confirmed = CONFIRM_YES
    await booking_service._apply_completion(db, first, driver.id)
    await db.commit()

    await db.refresh(trip)
    assert trip.status == TripStatus.active, "ikkinchi yo'lovchi hali tasdiqlamadi"


# ─── 2. Jo'nab ketgan safar ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_jonab_ketgan_safar_qidiruvda_chiqmaydi(db, driver_user):
    """Bugun ertalab ketgan mashina kechqurungi qidiruvda turmasin."""
    driver, _dp = driver_user
    await _regions(db)
    now = now_tashkent_naive()
    if now.hour < 2:
        pytest.skip("yarim tundan keyin — bugungi o'tgan vaqt yo'q")

    gone = await _trip(db, driver, when=now.replace(hour=0, minute=30))
    soon = await _trip(db, driver, when=now.replace(hour=23, minute=55))

    found = [t.id for t in await trip_service.search_trips(db, _search(now.date()))]

    assert gone.id not in found, "jo'nab ketgan safar chiqmasligi kerak"
    assert soon.id in found, "hali jo'namagan safar chiqishi kerak"


@pytest.mark.asyncio
async def test_jonab_ketgan_safarni_band_qilib_bolmaydi(db, user, driver_user):
    """Havola orqali kirib ham band qilib bo'lmasin — safar hali `active`."""
    driver, _dp = driver_user
    await _regions(db)
    now = now_tashkent_naive()
    if now.hour < 2:
        pytest.skip("yarim tundan keyin — bugungi o'tgan vaqt yo'q")

    trip = await _trip(db, driver, when=now.replace(hour=0, minute=30))
    assert trip.status == TripStatus.active

    with pytest.raises(HTTPException) as err:
        await booking_service.create_booking(db, user, BookingCreate(
            trip_id=trip.id, seats_count=1,
            payment_method=PaymentMethod.cash, pickup_address="Buvayda",
        ))

    assert err.value.status_code == 400
    assert "jo'nab ketgan" in str(err.value.detail)
