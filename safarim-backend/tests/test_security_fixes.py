"""Audit natijasida tuzatilgan xavfsizlik kamchiliklari uchun testlar.

Har bir test aynan bitta topilmani qo'riqlaydi — keyinchalik kod
o'zgarganda kamchilik jimgina qaytib kelmasin.
"""
import base64
import uuid

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models.booking import Booking
from app.models.enums import (
    BookingPaymentStatus, BookingStatus, LuggageSize, PaymentMethod,
    PaymentType, TripStatus,
)
from app.models.location import Region
from app.models.trip import Trip
from app.models.user import User
from app.services import payment_service

from tests.conftest import auth_headers

API = "/api/v1"
PASSWORD = "Test1234!"


# ─── A3: parol o'zgarsa eski tokenlar o'ladi ─────────────────────────────────

@pytest.mark.asyncio
async def test_old_token_dies_after_password_change(client, db, user):
    old = auth_headers(user)
    assert (await client.get(f"{API}/auth/me", headers=old)).status_code == 200

    r = await client.post(f"{API}/users/me/change-password", json={
        "current_password": PASSWORD, "new_password": "YangiParol1!",
    }, headers=old)
    assert r.status_code == 200, r.text
    # Javobda yangi token keladi — shu qurilma tizimda qoladi
    assert r.json()["access_token"]

    # Eski token endi o'tmaydi
    assert (await client.get(f"{API}/auth/me", headers=old)).status_code == 401
    # Yangisi o'tadi
    new = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert (await client.get(f"{API}/auth/me", headers=new)).status_code == 200


@pytest.mark.asyncio
async def test_old_refresh_token_rejected(client, db, user):
    old_refresh = create_refresh_token(str(user.id), user.token_version)

    user.token_version += 1  # parol o'zgargandagi holat
    await db.commit()

    r = await client.post(f"{API}/auth/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 401, r.text


@pytest.mark.asyncio
async def test_blocked_user_cannot_refresh(client, db, user):
    refresh = create_refresh_token(str(user.id), user.token_version)
    user.is_blocked = True
    await db.commit()

    r = await client.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401


# ─── A5: begona band qilishning to'lovini ko'rib bo'lmaydi ───────────────────

@pytest.mark.asyncio
async def test_payment_status_is_not_readable_by_strangers(client, db, user, driver_user):
    import datetime as dt

    driver, _ = driver_user
    db.add(Region(id=91, name_uz="Test 91", name_ru="Test 91", slug="t91", order=91))
    await db.commit()
    trip = Trip(
        id=uuid.uuid4(), driver_id=driver.id,
        from_region_id=91, to_region_id=91,
        departure_date=dt.date.today(),
        departure_time=dt.time(9, 0),
        total_seats=4, available_seats=3, price_per_seat=100_000,
        payment_type=PaymentType.any, luggage_size=LuggageSize.medium,
        status=TripStatus.active,
    )
    db.add(trip)
    await db.commit()

    booking = Booking(
        id=uuid.uuid4(), trip_id=trip.id, passenger_id=user.id,
        seats_count=1, price_per_seat=100_000, total_price=100_000,
        commission_rate=0.02, commission_amount=2_000, driver_amount=98_000,
        payment_method=PaymentMethod.cash, payment_status=BookingPaymentStatus.pending,
        status=BookingStatus.pending,
    )
    db.add(booking)

    stranger = User(
        id=uuid.uuid4(), phone="+998909999999", full_name="Begona",
        password_hash=user.password_hash, is_phone_verified=True,
    )
    db.add(stranger)
    await db.commit()

    r = await client.get(f"{API}/payments/{booking.id}", headers=auth_headers(stranger))
    assert r.status_code == 403, r.text


# ─── A1: sozlanmagan to'lov provayderi callback'ni qabul qilmaydi ────────────

def test_click_signature_rejected_when_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "CLICK_SECRET_KEY", "")
    monkeypatch.setattr(settings, "CLICK_SERVICE_ID", "")
    # Imzo bo'sh kalit bilan hisoblansa ham qabul qilinmaydi
    import hashlib
    raw = "1" "1" "" "x" "100.0" "1" "t"
    sign = hashlib.md5(raw.encode()).hexdigest()
    assert payment_service.verify_click_sign(1, 1, "x", 100.0, 1, "t", sign) is False


def test_payme_auth_rejected_when_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "PAYME_KEY", "")
    monkeypatch.setattr(settings, "PAYME_ID", "")
    header = "Basic " + base64.b64encode(b"Paycom:").decode()
    assert payment_service.verify_payme_auth(header) is False


# ─── A2: rate limit uchun IP mijoz sarlavhasidan olinmaydi ──────────────────

def test_client_ip_ignores_client_supplied_forwarded_for():
    from app.core.ratelimit import _client_ip

    class _Req:
        headers = {"x-forwarded-for": "1.2.3.4, 203.0.113.9"}
        client = None

    # Oxirgi qiymat — bizning nginx qo'shgani; birinchisi mijoznikidir
    assert _client_ip(_Req()) == "203.0.113.9"


# ─── A11: hisobni o'chirish ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_account_requires_correct_password(client, user):
    r = await client.request(
        "DELETE", f"{API}/users/me",
        json={"password": "notmypassword"}, headers=auth_headers(user),
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_delete_account_anonymizes_and_logs_out(client, db, user):
    old_phone = user.phone
    r = await client.request(
        "DELETE", f"{API}/users/me",
        json={"password": PASSWORD}, headers=auth_headers(user),
    )
    assert r.status_code == 200, r.text

    refreshed = (await db.execute(select(User).where(User.id == user.id))).scalar_one()
    await db.refresh(refreshed)
    assert refreshed.phone != old_phone
    assert refreshed.full_name == "O'chirilgan foydalanuvchi"
    assert refreshed.is_blocked is True
    # Eski raqam bilan kirib bo'lmaydi, ya'ni raqam qaytadan ro'yxatga ochiq
    login = await client.post(f"{API}/auth/login", json={
        "phone": old_phone, "password": PASSWORD,
    })
    assert login.status_code == 401


@pytest.mark.asyncio
async def test_delete_account_blocked_while_booking_active(client, db, user, driver_user):
    import datetime as dt

    driver, _ = driver_user
    db.add(Region(id=92, name_uz="Test 92", name_ru="Test 92", slug="t92", order=92))
    await db.commit()
    trip = Trip(
        id=uuid.uuid4(), driver_id=driver.id,
        from_region_id=92, to_region_id=92,
        departure_date=dt.date.today() + dt.timedelta(days=1),
        departure_time=dt.time(9, 0),
        total_seats=4, available_seats=3, price_per_seat=100_000,
        payment_type=PaymentType.any, luggage_size=LuggageSize.medium,
        status=TripStatus.active,
    )
    db.add(trip)
    await db.commit()
    db.add(Booking(
        id=uuid.uuid4(), trip_id=trip.id, passenger_id=user.id,
        seats_count=1, price_per_seat=100_000, total_price=100_000,
        commission_rate=0.02, commission_amount=2_000, driver_amount=98_000,
        payment_method=PaymentMethod.cash, payment_status=BookingPaymentStatus.pending,
        status=BookingStatus.confirmed,
    ))
    await db.commit()

    r = await client.request(
        "DELETE", f"{API}/users/me",
        json={"password": PASSWORD}, headers=auth_headers(user),
    )
    assert r.status_code == 400
    assert "band qilish" in r.json()["detail"].lower()

# ─── Hisob o'chirilgach mashina raqami bo'shashi ─────────────────────────────

@pytest.mark.asyncio
async def test_deleted_account_frees_the_car_plate(client, db, user, driver_user):
    """Hisobni o'chirgan haydovchi o'z mashinasi bilan qaytib kela olsin.

    Ilgari `driver_profiles` yozuvi qolib ketardi va avtomobil raqami band
    bo'lib turaverardi: odam qaytadan ro'yxatdan o'tsa ham "bu raqam
    allaqachon ro'yxatdan o'tgan" degan boshi berk ko'chaga kirardi.
    """
    from app.models.driver import DriverProfile
    from app.schemas.driver import DriverApplyRequest
    from app.services import driver_service

    driver, profile = driver_user
    plate = profile.vehicle_plate

    r = await client.request(
        "DELETE", f"{API}/users/me",
        json={"password": PASSWORD}, headers=auth_headers(driver),
    )
    assert r.status_code == 200, r.text

    # Profil butunlay o'chdi (guvohnoma surati ham qolmaydi)
    assert await db.scalar(
        select(func.count(DriverProfile.id)).where(DriverProfile.user_id == driver.id)
    ) == 0
    refreshed = (await db.execute(select(User).where(User.id == driver.id))).scalar_one()
    await db.refresh(refreshed)
    assert refreshed.is_driver is False

    # Endi o'sha raqam bilan boshqa (yoki qaytib kelgan) odam haydovchi bo'la oladi
    again = await driver_service.apply_driver(
        db, user,
        DriverApplyRequest(
            vehicle_make="Chevrolet", vehicle_model="Cobalt", vehicle_year=2020,
            vehicle_color="Oq", vehicle_plate=plate, vehicle_seats=4,
        ),
        "documents/yangi.jpg",
    )
    assert again.vehicle_plate == plate


@pytest.mark.asyncio
async def test_cannot_delete_account_with_wallet_debt(client, db, driver_user):
    """Qarzni yig'ib, hisobni o'chirib qutulish yo'li yopiq."""
    from app.models.wallet import DriverWallet

    driver, _ = driver_user
    db.add(DriverWallet(id=uuid.uuid4(), driver_id=driver.id, balance=-45_000))
    await db.commit()

    r = await client.request(
        "DELETE", f"{API}/users/me",
        json={"password": PASSWORD}, headers=auth_headers(driver),
    )
    assert r.status_code == 400
    assert "qarz" in r.json()["detail"].lower()
