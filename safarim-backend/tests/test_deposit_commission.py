"""
Hozirgi JONLI biznes modeli testi — NAQD-only + haydovchi depozit.

Model:
  - Online to'lov YO'Q. Yo'lovchi haydovchiga naqd to'laydi (tizim ushlamaydi).
  - Haydovchi hamyoniga oldindan DEPOZIT qo'yadi (jonli: admin qo'lda to'ldiradi).
  - Safar YAKUNLANGANDA platforma komissiyasini depozitdan yechib oladi.
  - Depozit -50,000 dan past tushsa haydovchi bloklanadi → yangi naqd bron
    qabul qila olmaydi. Qayta to'ldirilsa avtomatik ochiladi.
"""
import uuid
from datetime import date, time, timedelta

import pytest
from sqlalchemy import select

from app.models.location import Region
from app.models.trip import Trip
from app.models.booking import Booking
from app.models.enums import (
    TripStatus, PaymentType, LuggageSize, PaymentMethod,
    BookingStatus, BookingPaymentStatus,
)
from app.core.config import settings
from app.services import wallet_service, booking_service
from tests.conftest import auth_headers


API = "/api/v1"


async def _region(db, rid=1):
    if not await db.get(Region, rid):
        db.add(Region(id=rid, name_uz="T", name_ru="T", slug=f"r{rid}", order=rid))
        await db.commit()


async def _trip(db, driver, *, price=100_000, seats_left=4, future=True):
    dep = date.today() + timedelta(days=2) if future else date.today() - timedelta(days=1)
    trip = Trip(
        driver_id=driver.id, from_region_id=1, to_region_id=1,
        departure_date=dep, departure_time=time(9, 0),
        total_seats=4, available_seats=seats_left, price_per_seat=price,
        payment_type=PaymentType.cash, luggage_size=LuggageSize.medium,
        status=TripStatus.active,
    )
    db.add(trip)
    await db.commit()
    await db.refresh(trip)
    return trip


# ─── 1. Admin depozit to'ldiradi (jonli depozit yo'li) ───────────────────────

@pytest.mark.asyncio
async def test_admin_deposit_credits_and_unblocks(client, db, driver_user, admin_user):
    driver, _ = driver_user

    # Haydovchi naqd komissiyalardan manfiyga tushib bloklangan
    await wallet_service.deduct_commission(db, driver.id, 60_000)
    await db.commit()
    w = await wallet_service.get_or_create(db, driver.id)
    assert w.is_blocked is True and w.balance == -60_000

    # Admin depozit qo'shadi
    r = await client.post(f"{API}/admin/users/{driver.id}/wallet/topup",
                          json={"amount": 100_000, "note": "naqd olindi"},
                          headers=auth_headers(admin_user))
    assert r.status_code == 200, r.text
    assert r.json()["new_balance"] == 40_000       # -60,000 + 100,000
    assert r.json()["is_blocked"] is False          # avtomatik ochildi


# ─── 2. Safar yakunlanganda komissiya depozitdan yechiladi ───────────────────

@pytest.mark.asyncio
async def test_cash_completion_deducts_commission_from_deposit(client, db, user, driver_user):
    driver, _ = driver_user
    await _region(db)

    # Haydovchi depoziti bor (100,000)
    await wallet_service.topup(db, driver.id, 100_000, check_min=False)
    await db.commit()

    trip = await _trip(db, driver, price=100_000)

    # Yo'lovchi naqd bron qiladi
    r = await client.post(f"{API}/bookings/", json={
        "trip_id": str(trip.id), "seats_count": 1, "payment_method": "cash",
    }, headers=auth_headers(user))
    assert r.status_code == 201, r.text
    booking_id = r.json()["id"]
    assert r.json()["commission_amount"] == 2_000   # 100k → 2%

    # Bron paytida depozit HALI o'zgarmagan (komissiya faqat yakunda)
    w = await wallet_service.get_or_create(db, driver.id)
    assert w.balance == 100_000

    # Jo'nashni o'tkazamiz → haydovchi "bo'ldi" deydi → yakun
    trip.departure_date = date.today() - timedelta(days=1)
    await db.commit()
    result = await booking_service.confirm_booking(db, booking_id, driver, confirmed=True)
    assert result.status == BookingStatus.completed

    # Komissiya depozitdan yechildi: 100,000 - 2,000 = 98,000
    w = await wallet_service.get_or_create(db, driver.id)
    await db.refresh(w)
    assert w.balance == 98_000


# ─── 3. Depozit tugagan (bloklangan) haydovchi yangi bron ololmaydi ──────────

@pytest.mark.asyncio
async def test_blocked_driver_cannot_receive_cash_booking(client, db, user, driver_user):
    driver, _ = driver_user
    await _region(db)

    # Depozit -50,000 dan past → bloklangan
    await wallet_service.deduct_commission(db, driver.id, 60_000)
    await db.commit()
    assert (await wallet_service.get_or_create(db, driver.id)).is_blocked is True

    trip = await _trip(db, driver)

    # Yo'lovchi naqd bron urinadi → rad etiladi
    r = await client.post(f"{API}/bookings/", json={
        "trip_id": str(trip.id), "seats_count": 1, "payment_method": "cash",
    }, headers=auth_headers(user))
    assert r.status_code == 400, r.text
    assert "hamyon" in r.json()["detail"].lower()


# ─── 4. Qayta depozit → ochiladi → bron yana ishlaydi ────────────────────────

@pytest.mark.asyncio
async def test_redeposit_unblocks_and_allows_booking(client, db, user, driver_user, admin_user):
    driver, _ = driver_user
    await _region(db)

    # Bloklangan holat (rad etilishini test 3 allaqachon isbotladi)
    await wallet_service.deduct_commission(db, driver.id, 60_000)
    await db.commit()
    trip = await _trip(db, driver)

    # Admin qayta depozit qo'shadi → avtomatik ochiladi
    r = await client.post(f"{API}/admin/users/{driver.id}/wallet/topup",
                          json={"amount": 100_000, "note": ""},
                          headers=auth_headers(admin_user))
    assert r.status_code == 200
    assert r.json()["is_blocked"] is False

    # Endi naqd bron o'tadi
    r = await client.post(f"{API}/bookings/", json={
        "trip_id": str(trip.id), "seats_count": 1, "payment_method": "cash",
    }, headers=auth_headers(user))
    assert r.status_code == 201, r.text


# ─── 5. Katta narx → 5% komissiya (chegara: 200,000) ─────────────────────────

@pytest.mark.asyncio
async def test_high_price_uses_5_percent_commission(client, db, user, driver_user):
    driver, _ = driver_user
    await _region(db)
    await wallet_service.topup(db, driver.id, 100_000, check_min=False)
    await db.commit()

    trip = await _trip(db, driver, price=300_000)   # > 200,000 → 5%

    r = await client.post(f"{API}/bookings/", json={
        "trip_id": str(trip.id), "seats_count": 1, "payment_method": "cash",
    }, headers=auth_headers(user))
    assert r.status_code == 201, r.text
    assert r.json()["commission_amount"] == 15_000   # 300k → 5%

    booking_id = r.json()["id"]
    trip.departure_date = date.today() - timedelta(days=1)
    await db.commit()
    await booking_service.confirm_booking(db, booking_id, driver, confirmed=True)

    w = await wallet_service.get_or_create(db, driver.id)
    await db.refresh(w)
    assert w.balance == 100_000 - 15_000   # 85,000


# ─── Bepul davr (COMMISSION_FREE_MODE) ───────────────────────────────────────

@pytest.mark.asyncio
async def test_free_mode_charges_no_commission(client, db, user, driver_user, monkeypatch):
    """Bepul davrda komissiya 0 va depozitga umuman tegilmaydi."""
    monkeypatch.setattr(settings, "COMMISSION_FREE_MODE", True)
    driver, _ = driver_user
    await _region(db)
    # Depozit yo'q (0) — bepul davrda kerak emas
    trip = await _trip(db, driver, price=100_000)

    r = await client.post(f"{API}/bookings/", json={
        "trip_id": str(trip.id), "seats_count": 1, "payment_method": "cash",
    }, headers=auth_headers(user))
    assert r.status_code == 201, r.text
    assert r.json()["commission_amount"] == 0
    assert r.json()["driver_amount"] == 100_000   # haydovchi to'liq oladi

    booking_id = r.json()["id"]
    trip.departure_date = date.today() - timedelta(days=1)
    await db.commit()
    await booking_service.confirm_booking(db, booking_id, driver, confirmed=True)

    w = await wallet_service.get_or_create(db, driver.id)
    await db.refresh(w)
    assert w.balance == 0   # hech narsa yechilmadi


@pytest.mark.asyncio
async def test_free_mode_never_blocks_driver(client, db, user, driver_user, monkeypatch):
    """Bepul davrda balans manfiy bo'lsa ham naqd bron qabul qilinadi."""
    monkeypatch.setattr(settings, "COMMISSION_FREE_MODE", True)
    driver, _ = driver_user
    await _region(db)
    await wallet_service.deduct_commission(db, driver.id, 60_000)  # bloklangan holat
    await db.commit()
    trip = await _trip(db, driver)

    r = await client.post(f"{API}/bookings/", json={
        "trip_id": str(trip.id), "seats_count": 1, "payment_method": "cash",
    }, headers=auth_headers(user))
    assert r.status_code == 201, r.text   # bepul davr: rad etilmaydi
