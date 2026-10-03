"""«Mening safarlarim» va bron ro'yxatlari butun tarixni birdan bermaydi.

Ilgari `/trips/my`, `/bookings/driver` va `/bookings/my` cheklovsiz edi: har
kuni qatnaydigan haydovchida bir yilda ~700 safar to'planadi va panel har
ochilganda hammasi yuklanardi. Endi faol yozuvlar to'liq, tugaganlardan esa
oxirgi `past_limit` tasi keladi. Statistika ro'yxatdan emas, alohida
`summary` endpointlaridan — aks holda «jami safarlar» 30 da to'xtab qolardi.
"""
import uuid
from datetime import datetime, timedelta

from app.core.timeutils import now_tashkent_naive
from app.models.booking import Booking
from app.models.enums import (
    BookingStatus, LuggageSize, PaymentMethod, PaymentType, TripStatus,
)
from app.models.location import Region
from app.models.trip import Trip
from tests.conftest import auth_headers

FARGONA, TOSHKENT, SAMARQAND = 701, 702, 703


async def _regions(db) -> None:
    db.add_all([
        Region(id=FARGONA, name_uz="Farg'ona viloyati", name_ru="Фергана", slug="fargona-p", order=1),
        Region(id=TOSHKENT, name_uz="Toshkent shahri", name_ru="Ташкент", slug="toshkent-p", order=2),
        Region(id=SAMARQAND, name_uz="Samarqand viloyati", name_ru="Самарканд", slug="samarqand-p", order=3),
    ])
    await db.commit()


def _trip(driver, days: int, status: TripStatus, to=TOSHKENT) -> Trip:
    when = now_tashkent_naive() + timedelta(days=days)
    return Trip(
        id=uuid.uuid4(),
        driver_id=driver.id,
        from_region_id=FARGONA,
        to_region_id=to,
        departure_date=when.date(),
        departure_time=when.replace(hour=9, minute=0, second=0, microsecond=0).time(),
        total_seats=4,
        available_seats=3,
        price_per_seat=100_000,
        payment_type=PaymentType.cash,
        luggage_size=LuggageSize.medium,
        status=status,
    )


def _booking(trip, passenger, status: BookingStatus, *, created: datetime,
             completed: datetime | None = None, price=100_000) -> Booking:
    return Booking(
        id=uuid.uuid4(),
        trip_id=trip.id,
        passenger_id=passenger.id,
        seats_count=1,
        price_per_seat=price,
        total_price=price,
        commission_rate=0,
        commission_amount=0,
        driver_amount=price - 10_000,
        payment_method=PaymentMethod.cash,
        status=status,
        created_at=created,
        completed_at=completed,
    )


async def _history(db, driver, passenger, n_past: int):
    """`n_past` ta tugagan safar (har biri yakunlangan bron bilan) + 2 ta faol."""
    now = datetime.utcnow()
    past = []
    for i in range(n_past):
        t = _trip(driver, -(i + 2), TripStatus.completed)
        past.append(t)
        db.add(t)
        await db.flush()
        db.add(_booking(t, passenger, BookingStatus.completed,
                        created=now - timedelta(days=i + 3), completed=now - timedelta(days=i + 2)))
    live = [_trip(driver, 1, TripStatus.active), _trip(driver, 2, TripStatus.full)]
    for t in live:
        db.add(t)
        await db.flush()
        db.add(_booking(t, passenger, BookingStatus.confirmed, created=now))
    await db.commit()
    return past, live


# ─── Haydovchi ───────────────────────────────────────────────────────────────

async def test_haydovchi_faollari_toliq_tugaganlari_cheklangan(client, db, user, driver_user):
    driver, _ = driver_user
    await _regions(db)
    past, live = await _history(db, driver, user, 8)

    r = await client.get("/api/v1/trips/my?past_limit=5", headers=auth_headers(driver))
    assert r.status_code == 200
    ids = {t["id"] for t in r.json()}
    assert {str(t.id) for t in live} <= ids
    # Eng yangi 5 ta tugagani (sanasi bo'yicha) — eskilari keyingi sahifada
    assert {str(t.id) for t in past[:5]} <= ids
    assert not ({str(t.id) for t in past[5:]} & ids)
    assert len(ids) == 7


async def test_haydovchi_bronlari_safarlar_bilan_mos(client, db, user, driver_user):
    """Panel safar ostida uning yo'lovchilarini chizadi — ikkala ro'yxat bir xil kesilishi kerak."""
    driver, _ = driver_user
    await _regions(db)
    past, live = await _history(db, driver, user, 8)

    h = auth_headers(driver)
    trips = (await client.get("/api/v1/trips/my?past_limit=5", headers=h)).json()
    bookings = (await client.get("/api/v1/bookings/driver?past_limit=5", headers=h)).json()
    assert {b["trip_id"] for b in bookings} == {t["id"] for t in trips}


async def test_eski_safardagi_ochiq_bron_tushib_qolmaydi(client, db, user, driver_user):
    """Tasdiq kutayotgan bron — haydovchidan javob kutilmoqda, safar qanchalik eski bo'lmasin."""
    driver, _ = driver_user
    await _regions(db)
    past, _ = await _history(db, driver, user, 6)
    old = _trip(driver, -60, TripStatus.completed)
    db.add(old)
    await db.flush()
    waiting = _booking(old, user, BookingStatus.awaiting_confirmation,
                       created=datetime.utcnow() - timedelta(days=61))
    db.add(waiting)
    await db.commit()

    r = await client.get("/api/v1/bookings/driver?past_limit=3", headers=auth_headers(driver))
    assert str(waiting.id) in {b["id"] for b in r.json()}


async def test_sukut_boyicha_ham_cheklangan(client, db, user, driver_user):
    """Parametrsiz so'rov (xabarlar sahifasi, eski brauzer keshidagi kod) ham butun tarixni olmaydi."""
    driver, _ = driver_user
    await _regions(db)
    await _history(db, driver, user, 33)

    r = await client.get("/api/v1/trips/my", headers=auth_headers(driver))
    assert len(r.json()) == 30 + 2


async def test_past_limit_chegaradan_oshmaydi(client, db, driver_user):
    driver, _ = driver_user
    r = await client.get("/api/v1/trips/my?past_limit=100000", headers=auth_headers(driver))
    assert r.status_code == 422


async def test_haydovchi_statistikasi_butun_tarix(client, db, user, driver_user):
    driver, _ = driver_user
    await _regions(db)
    await _history(db, driver, user, 8)

    r = await client.get("/api/v1/bookings/driver/summary", headers=auth_headers(driver))
    assert r.status_code == 200
    data = r.json()
    # 8 ta yakunlangan bron × (100 000 − 10 000) — ro'yxat 5 ta bilan cheklansa ham
    assert data["total_earnings"] == 8 * 90_000
    assert 0 <= data["completed_this_month"] <= 8


async def test_haydovchi_statistikasi_yolovchiga_yopiq(client, user):
    r = await client.get("/api/v1/bookings/driver/summary", headers=auth_headers(user))
    assert r.status_code == 403


# ─── Yo'lovchi ───────────────────────────────────────────────────────────────

async def test_yolovchi_ochiq_bronlari_toliq_yopilganlari_cheklangan(client, db, user, driver_user):
    driver, _ = driver_user
    await _regions(db)
    past, live = await _history(db, driver, user, 8)

    r = await client.get("/api/v1/bookings/my?past_limit=4", headers=auth_headers(user))
    data = r.json()
    assert sum(b["status"] == "confirmed" for b in data) == 2
    assert sum(b["status"] == "completed" for b in data) == 4


async def test_yolovchi_statistikasi_butun_tarix(client, db, user, driver_user):
    driver, _ = driver_user
    await _regions(db)
    await _history(db, driver, user, 8)
    # Bitta Samarqand safari — sevimli yo'nalish baribir Toshkent bo'lib qolsin
    t = _trip(driver, -40, TripStatus.completed, to=SAMARQAND)
    db.add(t)
    await db.flush()
    db.add(_booking(t, user, BookingStatus.cancelled, created=datetime.utcnow() - timedelta(days=41)))
    await db.commit()

    r = await client.get("/api/v1/bookings/my/summary", headers=auth_headers(user))
    assert r.status_code == 200
    data = r.json()
    assert data["completed_count"] == 8
    assert data["total_paid"] == 8 * 100_000
    assert 0 <= data["completed_this_year"] <= 8
    assert data["favorite_route"] == {
        "from_region": "Farg'ona viloyati", "to_region": "Toshkent shahri", "count": 10,
    }


async def test_yangi_yolovchida_statistika_bosh(client, user):
    r = await client.get("/api/v1/bookings/my/summary", headers=auth_headers(user))
    assert r.json() == {
        "completed_count": 0, "total_paid": 0, "completed_this_year": 0, "favorite_route": None,
    }
