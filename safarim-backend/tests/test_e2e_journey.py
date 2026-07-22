"""
Uchidan-uchiga (E2E) to'liq sayohat testi — HTTP API orqali, haqiqiy oqim:

  ro'yxatdan o'tish (OTP) → haydovchi ariza → admin tasdiq → safar e'lon →
  bron (online + naqd) → to'lov (Click + Payme callback simulyatsiyasi) →
  jo'nashdan keyin tasdiq → safar yakuni → hamyon/komissiya/daromad tekshiruvi.

To'lov provayderlari (Click/Payme) haqiqiy pul talab qiladi va pilotda
sozlanmagan — shuning uchun ularning webhook (callback) chaqiruvi
simulyatsiya qilinadi (aynan provayder yuboradigan so'rov ko'rinishida).
Fayl saqlash (MinIO) test doirasidan tashqarida — mock qilinadi.
"""
import base64
import hashlib
import io
import uuid
from datetime import date, time, timedelta

import pytest
from PIL import Image
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.models.otp import OtpCode
from app.models.user import User
from app.models.location import Region
from app.models.trip import Trip
from app.models.booking import Booking
from app.models.enums import (
    OtpPurpose, BookingStatus, BookingPaymentStatus, PaymentType, LuggageSize, TripStatus,
)
from app.services import wallet_service, booking_service
from app.services.storage_service import storage_service
from tests.conftest import auth_headers


API = "/api/v1"


# ─── Yordamchilar ────────────────────────────────────────────────────────────

def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _jpeg_bytes() -> bytes:
    """Struktura tekshiruvidan o'tadigan haqiqiy shovqinli JPEG (bo'sh emas)."""
    img = Image.effect_noise((600, 380), 60).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _click_sign(click_trans_id, service_id, merchant_trans_id, amount, action, sign_time) -> str:
    """Click imzosi — verify_click_sign bilan bir xil formula."""
    raw = (
        f"{click_trans_id}{service_id}{settings.CLICK_SECRET_KEY}"
        f"{merchant_trans_id}{amount}{action}{sign_time}"
    )
    return hashlib.md5(raw.encode()).hexdigest()


def _payme_auth() -> dict:
    cred = base64.b64encode(f"Paycom:{settings.PAYME_KEY}".encode()).decode()
    return {"Authorization": f"Basic {cred}"}


async def _register(client, db, phone, name, password="Test1234!") -> str:
    """Haqiqiy ro'yxatdan o'tish: send-otp → OTP'ni bazadan o'qish → register."""
    r = await client.post(f"{API}/auth/send-otp", json={"phone": phone, "purpose": "register"})
    assert r.status_code == 200, r.text
    otp = (await db.execute(
        select(OtpCode).where(
            OtpCode.phone == phone,
            OtpCode.purpose == OtpPurpose.register,
            OtpCode.is_used == False,  # noqa: E712
        ).order_by(OtpCode.created_at.desc())
    )).scalars().first()
    assert otp is not None, "OTP yaratilmadi"

    r = await client.post(f"{API}/auth/register", json={
        "phone": phone, "otp_code": otp.code, "full_name": name, "password": password,
    })
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


async def _two_regions(db):
    for rid, nm in ((1, "Toshkent"), (2, "Samarqand")):
        if not await db.get(Region, rid):
            db.add(Region(id=rid, name_uz=nm, name_ru=nm, slug=f"r{rid}", order=rid))
    await db.commit()


# ─── To'liq sayohat: ro'yxatdan o'tishdan safar yakunigacha ──────────────────

@pytest.mark.asyncio
async def test_full_journey_registration_to_completion(client, db, admin_user, monkeypatch):
    # MinIO'siz: fayl yuklashni mock qilamiz
    async def _fake_upload(file, bucket, folder=""):
        await file.read()
        await file.seek(0)
        return f"{folder}/e2e-license.jpg"
    monkeypatch.setattr(storage_service, "upload", _fake_upload)

    await _two_regions(db)

    # ── 1. Ro'yxatdan o'tish: 2 yo'lovchi + 1 haydovchi ──────────────────────
    token_a = await _register(client, db, "+998901000001", "Yo'lovchi A")
    token_b = await _register(client, db, "+998901000002", "Yo'lovchi B")
    token_d = await _register(client, db, "+998901000003", "Haydovchi D")

    driver = (await db.execute(select(User).where(User.phone == "+998901000003"))).scalar_one()
    assert driver.is_driver is False  # hali oddiy foydalanuvchi

    # ── 2. Haydovchi ariza (mashina + guvohnoma rasmi) ───────────────────────
    r = await client.post(
        f"{API}/drivers/apply",
        data={
            "vehicle_make": "Chevrolet", "vehicle_model": "Cobalt", "vehicle_year": "2022",
            "vehicle_color": "Oq", "vehicle_plate": "01A123BC", "vehicle_seats": "4",
        },
        files={"license_image": ("license.jpg", _jpeg_bytes(), "image/jpeg")},
        headers=_auth(token_d),
    )
    assert r.status_code == 200, r.text
    profile_id = r.json()["id"]
    assert r.json()["status"] == "pending"

    # ── 3. Admin tasdiqlaydi ─────────────────────────────────────────────────
    r = await client.post(f"{API}/admin/drivers/{profile_id}/approve", headers=auth_headers(admin_user))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"

    # ── 4. Haydovchi safar e'lon qiladi (ertaga) ─────────────────────────────
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    r = await client.post(f"{API}/trips/", json={
        "from_region_id": 1, "to_region_id": 2,
        "departure_date": tomorrow, "departure_time": "08:00",
        "total_seats": 4, "price_per_seat": 100_000, "payment_type": "any",
    }, headers=_auth(token_d))
    assert r.status_code == 201, r.text
    trip_id = r.json()["id"]

    # ── 5a. Yo'lovchi A — ONLINE bron (Click) ────────────────────────────────
    r = await client.post(f"{API}/bookings/", json={
        "trip_id": trip_id, "seats_count": 1, "payment_method": "click",
    }, headers=_auth(token_a))
    assert r.status_code == 201, r.text
    booking_a = r.json()["id"]
    assert r.json()["commission_amount"] == 2_000   # 100k ning 2%
    assert r.json()["driver_amount"] == 98_000

    # To'lovni boshlash (payment_url oladi)
    r = await client.post(f"{API}/payments/initiate", json={
        "booking_id": booking_a, "method": "click",
    }, headers=_auth(token_a))
    assert r.status_code == 200, r.text
    assert "my.click.uz" in r.json()["payment_url"]

    # Click callback: PREPARE (0) → COMPLETE (1)
    amt = float(100_000)
    for action in (0, 1):
        cti, st = 5551234, "2026-07-22 08:30:00"
        sign = _click_sign(cti, 1, booking_a, amt, action, st)
        r = await client.post(f"{API}/payments/click/callback", json={
            "click_trans_id": cti, "service_id": 1, "click_paydoc_id": 99,
            "merchant_trans_id": booking_a, "amount": amt, "action": action,
            "error": 0, "error_note": "", "sign_time": st, "sign_string": sign,
        })
        assert r.status_code == 200, r.text
        assert r.json()["error"] == 0, r.json()

    bk_a = (await db.execute(select(Booking).where(Booking.id == uuid.UUID(booking_a)))).scalar_one()
    await db.refresh(bk_a)
    assert bk_a.payment_status == BookingPaymentStatus.paid   # ✅ online to'landi

    # Noto'g'ri imzo rad etilishi kerak (xavfsizlik)
    bad = await client.post(f"{API}/payments/click/callback", json={
        "click_trans_id": 1, "service_id": 1, "click_paydoc_id": 1,
        "merchant_trans_id": booking_a, "amount": amt, "action": 1,
        "error": 0, "error_note": "", "sign_time": "x", "sign_string": "DEADBEEF",
    })
    assert bad.json()["error"] == -1   # SIGN CHECK FAILED

    # ── 5b. Yo'lovchi B — NAQD bron ──────────────────────────────────────────
    r = await client.post(f"{API}/bookings/", json={
        "trip_id": trip_id, "seats_count": 1, "payment_method": "cash",
    }, headers=_auth(token_b))
    assert r.status_code == 201, r.text
    booking_b = r.json()["id"]

    # 2 ta bron → 2 o'rin band, 2 qoldi
    r = await client.get(f"{API}/trips/{trip_id}")
    assert r.json()["available_seats"] == 2

    # ── 6. Vaqtni oldinga surish: jo'nash o'tdi (tasdiq mumkin bo'lsin) ───────
    trip = (await db.execute(select(Trip).where(Trip.id == uuid.UUID(trip_id)))).scalar_one()
    trip.departure_date = date.today() - timedelta(days=1)
    await db.commit()

    # ── 7. Haydovchi ikkala safarni "bo'ldi" deb yakunlaydi ──────────────────
    for bid in (booking_a, booking_b):
        r = await client.post(f"{API}/bookings/{bid}/complete", headers=_auth(token_d))
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "completed", r.json()

    # ── 8. Hamyon tekshiruvi ─────────────────────────────────────────────────
    #   Online (A): daromad  +98,000
    #   Naqd  (B): komissiya  -2,000
    #   Yakuniy balans = 96,000
    wallet = await wallet_service.get_or_create(db, driver.id)
    await db.refresh(wallet)
    assert wallet.balance == 98_000 - 2_000, f"kutilgan 96000, bor: {wallet.balance}"

    # Naqd bron: pul olinmagan → completion'da paid deb belgilanadi (komissiya asosida)
    bk_b = (await db.execute(select(Booking).where(Booking.id == uuid.UUID(booking_b)))).scalar_one()
    await db.refresh(bk_b)
    assert bk_b.status == BookingStatus.completed


# ─── Payme to'lov oqimi (alohida, fixture'lar bilan qisqa) ───────────────────

@pytest.mark.asyncio
async def test_payme_online_payment_marks_paid(client, db, user, driver_user):
    """Payme CreateTransaction + PerformTransaction → bron to'landi + daromad."""
    driver, _ = driver_user
    if not await db.get(Region, 1):
        db.add(Region(id=1, name_uz="T", name_ru="T", slug="t1", order=1))
        await db.commit()

    # Safar (ertaga) — to'g'ridan-to'g'ri bazaga
    trip = Trip(
        driver_id=driver.id, from_region_id=1, to_region_id=1,
        departure_date=date.today() + timedelta(days=1), departure_time=time(9, 0),
        total_seats=4, available_seats=4, price_per_seat=100_000,
        payment_type=PaymentType.any, luggage_size=LuggageSize.medium, status=TripStatus.active,
    )
    db.add(trip)
    await db.commit()
    await db.refresh(trip)

    # Yo'lovchi online bron qiladi
    r = await client.post(f"{API}/bookings/", json={
        "trip_id": str(trip.id), "seats_count": 1, "payment_method": "payme",
    }, headers=auth_headers(user))
    assert r.status_code == 201, r.text
    booking_id = r.json()["id"]

    # Payme CreateTransaction (amount tiyinda = so'm * 100)
    r = await client.post(f"{API}/payments/payme/callback", headers=_payme_auth(), json={
        "jsonrpc": "2.0", "id": 1, "method": "CreateTransaction",
        "params": {"id": "payme_tx_e2e", "time": 1_700_000_000_000,
                   "amount": 100_000 * 100, "account": {"booking_id": booking_id}},
    })
    assert r.status_code == 200, r.text
    assert r.json()["result"]["state"] == 1, r.json()

    # Noto'g'ri summa rad etilishi kerak (xavfsizlik — C3 fix)
    bad = await client.post(f"{API}/payments/payme/callback", headers=_payme_auth(), json={
        "jsonrpc": "2.0", "id": 9, "method": "CreateTransaction",
        "params": {"id": "payme_tx_bad", "time": 1_700_000_000_000,
                   "amount": 50 * 100, "account": {"booking_id": booking_id}},
    })
    assert "error" in bad.json(), bad.json()

    # PerformTransaction → to'landi
    r = await client.post(f"{API}/payments/payme/callback", headers=_payme_auth(), json={
        "jsonrpc": "2.0", "id": 2, "method": "PerformTransaction",
        "params": {"id": "payme_tx_e2e"},
    })
    assert r.status_code == 200, r.text
    assert r.json()["result"]["state"] == 2, r.json()

    bk = (await db.execute(select(Booking).where(Booking.id == uuid.UUID(booking_id)))).scalar_one()
    await db.refresh(bk)
    assert bk.payment_status == BookingPaymentStatus.paid

    # Jo'nashni o'tkazib, yakunlash → haydovchiga daromad
    trip.departure_date = date.today() - timedelta(days=1)
    await db.commit()
    result = await booking_service.confirm_booking(db, booking_id, driver, confirmed=True)
    assert result.status == BookingStatus.completed
    wallet = await wallet_service.get_or_create(db, driver.id)
    await db.refresh(wallet)
    assert wallet.balance == 98_000   # online daromad


# ─── To'langan online bronni bekor qilish → refund belgilanadi ───────────────

@pytest.mark.asyncio
async def test_paid_online_cancel_flags_refund(client, db, user, driver_user, monkeypatch):
    """Online to'langan bron bekor qilinsa payment_status=refunded + refund_amount."""
    # Admin xabari (Telegram) — tashqi chaqiruvni bloklaymiz
    async def _noop(*a, **k):
        return True
    monkeypatch.setattr("app.services.sms_service.sms_service.notify_admin", _noop)

    driver, _ = driver_user
    if not await db.get(Region, 1):
        db.add(Region(id=1, name_uz="T", name_ru="T", slug="t1", order=1))
        await db.commit()

    trip = Trip(
        driver_id=driver.id, from_region_id=1, to_region_id=1,
        departure_date=date.today() + timedelta(days=3), departure_time=time(9, 0),
        total_seats=4, available_seats=4, price_per_seat=100_000,
        payment_type=PaymentType.any, luggage_size=LuggageSize.medium, status=TripStatus.active,
    )
    db.add(trip)
    await db.commit()
    await db.refresh(trip)

    r = await client.post(f"{API}/bookings/", json={
        "trip_id": str(trip.id), "seats_count": 1, "payment_method": "click",
    }, headers=auth_headers(user))
    booking_id = r.json()["id"]

    # To'langan holatga keltiramiz (Payment + booking paid)
    bk = (await db.execute(select(Booking).where(Booking.id == uuid.UUID(booking_id)))).scalar_one()
    bk.payment_status = BookingPaymentStatus.paid
    await db.commit()

    # Yo'lovchi bekor qiladi (3 kun oldin → 100% refund)
    r = await client.post(f"{API}/bookings/{booking_id}/cancel", json={"reason": "reja o'zgardi"},
                          headers=auth_headers(user))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "cancelled"
    assert data["refund_amount"] == 100_000       # to'liq qaytariladi
    assert data["payment_status"] == "refunded"   # refund navbatga belgilandi
