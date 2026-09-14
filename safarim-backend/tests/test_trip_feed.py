"""Telegram guruhidagi safar lentasi.

Guruhga e'lon tashlanadi va holat o'zgarganda O'SHA post tahrirlanadi.
Eng muhim tekshiruv — postda haydovchining telefon raqami yo'qligi: bo'lsa,
yo'lovchi to'g'ridan-to'g'ri qo'ng'iroq qilib platformani chetlab o'tadi.

Tarmoqqa chiqilmaydi: `_call` monkeypatch qilinadi.
"""
import uuid
from datetime import date, time, timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.enums import LuggageSize, PaymentType, TripStatus
from app.models.location import District, Region
from app.models.trip import Trip
from app.services import telegram_service, trip_service
from tests.conftest import TestingSession

FARGONA, TOSHKENT = 301, 302
BUVAYDA = 3011
TOMORROW = date.today() + timedelta(days=1)
CHAT = "-1001234567890"


@pytest.fixture
def sent(monkeypatch) -> list[dict]:
    """Telegramga ketgan chaqiruvlar; bot sozlangan deb hisoblanadi."""
    calls: list[dict] = []
    counter = {"n": 0}

    async def _fake_call(method: str, payload: dict):
        calls.append({"method": method, **payload})
        counter["n"] += 1
        return {"ok": True, "result": {"message_id": 5000 + counter["n"]}}

    monkeypatch.setattr(telegram_service, "_call", _fake_call)
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TELEGRAM_TRIPS_CHAT_ID", CHAT)
    monkeypatch.setattr(settings, "PUBLIC_SITE_URL", "https://uzsafar.uz")
    return calls


async def _locations(db):
    db.add_all([
        Region(id=FARGONA, name_uz="Farg'ona viloyati", name_ru="Фергана", slug="fargona-f", order=1),
        Region(id=TOSHKENT, name_uz="Toshkent shahri", name_ru="Ташкент", slug="toshkent-f", order=2),
    ])
    await db.flush()
    db.add(District(id=BUVAYDA, region_id=FARGONA, name_uz="Buvayda", name_ru="Бувайда", slug="buvayda-f"))
    await db.commit()


async def _trip(db, driver_user, **kw) -> Trip:
    user, dp = driver_user
    dp.rating_avg, dp.rating_count = 4.8, 12
    trip = Trip(
        id=uuid.uuid4(),
        driver_id=user.id,
        from_region_id=FARGONA,
        from_district_id=BUVAYDA,
        to_region_id=TOSHKENT,
        departure_date=TOMORROW,
        departure_time=time(8, 0),
        total_seats=4,
        available_seats=kw.get("available_seats", 3),
        price_per_seat=120000,
        payment_type=PaymentType.cash,
        luggage_size=LuggageSize.medium,
        status=kw.get("status", TripStatus.active),
        telegram_message_id=kw.get("telegram_message_id"),
    )
    db.add(trip)
    await db.commit()
    return (await db.execute(
        select(Trip).options(*trip_service._load_options()).where(Trip.id == trip.id)
    )).scalar_one()


# ─── Matn ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_postda_telefon_raqam_yoq(db, driver_user, sent):
    """Eng muhim qoida: guruh posti haydovchiga to'g'ridan-to'g'ri yo'l ochmasin."""
    await _locations(db)
    user, _ = driver_user
    trip = await _trip(db, driver_user)

    text = telegram_service._trip_text(trip)

    assert user.phone not in text
    assert user.phone.lstrip("+") not in text
    # Raqamning oxirgi bo'lagi ham tushib qolmasin
    assert user.phone[-7:] not in text


@pytest.mark.asyncio
async def test_post_matni_kerakli_malumotni_beradi(db, driver_user, sent):
    await _locations(db)
    trip = await _trip(db, driver_user)

    text = telegram_service._trip_text(trip)

    assert "Buvayda" in text                 # viloyat emas, tuman ko'rsatiladi
    assert "Toshkent shahri" in text
    assert "120 000 so'm" in text
    assert "3 ta o'rin bor" in text
    assert "Nexia 3" in text
    assert "4.8" in text
    assert f"/trips/{trip.id}" in text       # band qilish saytda


@pytest.mark.asyncio
async def test_familiya_toliq_yozilmaydi(db, driver_user, sent):
    """Guruh ochiq — familiya to'liq chiqmasin."""
    await _locations(db)
    trip = await _trip(db, driver_user)

    text = telegram_service._trip_text(trip)

    assert "Test H." in text
    assert "Test Haydovchi" not in text


@pytest.mark.asyncio
async def test_holat_yorligi_qoshiladi(db, driver_user, sent):
    await _locations(db)
    trip = await _trip(db, driver_user, status=TripStatus.cancelled)

    assert "Bekor qilindi" in telegram_service._trip_text(trip)

    trip.status = TripStatus.full
    trip.available_seats = 0
    text = telegram_service._trip_text(trip)
    assert "O'rinlar tugadi" in text
    assert "o'rin qolmadi" in text


# ─── Yuborish va tahrirlash ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_yangi_elon_ovozsiz_yuboriladi(db, driver_user, sent):
    await _locations(db)
    trip = await _trip(db, driver_user)

    message_id = await telegram_service.send_trip_post(trip)

    assert message_id == 5001
    assert len(sent) == 1
    assert sent[0]["method"] == "sendMessage"
    assert sent[0]["chat_id"] == CHAT
    # Kuniga o'nlab e'lon chiqadi — har biri telefonni jiringlatmasin
    assert sent[0]["disable_notification"] is True


@pytest.mark.asyncio
async def test_holat_ozgarsa_yangi_post_emas_tahrir(db, driver_user, sent, monkeypatch):
    monkeypatch.setattr("app.db.session.AsyncSessionLocal", TestingSession)
    await _locations(db)
    trip = await _trip(db, driver_user, telegram_message_id=777)

    trip.status = TripStatus.cancelled
    await db.commit()

    await telegram_service._sync_trip_now(trip.id)

    assert len(sent) == 1
    assert sent[0]["method"] == "editMessageText"
    assert sent[0]["message_id"] == 777
    assert "Bekor qilindi" in sent[0]["text"]


@pytest.mark.asyncio
async def test_post_id_saqlanadi(db, driver_user, sent, monkeypatch):
    monkeypatch.setattr("app.db.session.AsyncSessionLocal", TestingSession)
    await _locations(db)
    trip = await _trip(db, driver_user)

    await telegram_service._post_trip_now(trip.id)

    await db.refresh(trip)
    assert trip.telegram_message_id == 5001


@pytest.mark.asyncio
async def test_ikki_marta_tashlanmaydi(db, driver_user, sent, monkeypatch):
    """Vazifa qayta ishga tushsa ham guruhda dublikat e'lon paydo bo'lmasin."""
    monkeypatch.setattr("app.db.session.AsyncSessionLocal", TestingSession)
    await _locations(db)
    trip = await _trip(db, driver_user, telegram_message_id=777)

    await telegram_service._post_trip_now(trip.id)

    assert sent == []


@pytest.mark.asyncio
async def test_bekor_qilingan_safar_tashlanmaydi(db, driver_user, sent, monkeypatch):
    monkeypatch.setattr("app.db.session.AsyncSessionLocal", TestingSession)
    await _locations(db)
    trip = await _trip(db, driver_user, status=TripStatus.cancelled)

    await telegram_service._post_trip_now(trip.id)

    assert sent == []


# ─── O'chiq holat ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_guruh_sozlanmagan_bolsa_jim_turadi(db, driver_user, monkeypatch):
    """`TELEGRAM_TRIPS_CHAT_ID` bo'sh — sayt oddiy ishlayveradi, xato bermaydi."""
    calls: list = []

    async def _fake_call(method: str, payload: dict):
        calls.append(method)
        return {"ok": True}

    monkeypatch.setattr(telegram_service, "_call", _fake_call)
    monkeypatch.setattr(settings, "TELEGRAM_TRIPS_CHAT_ID", "")
    await _locations(db)
    trip = await _trip(db, driver_user)

    assert telegram_service.trips_chat_configured() is False
    assert await telegram_service.send_trip_post(trip) is None
    telegram_service.queue_trip_post(trip.id)     # navbatga ham qo'yilmasin
    telegram_service.queue_trip_sync(trip.id)
    assert calls == []
