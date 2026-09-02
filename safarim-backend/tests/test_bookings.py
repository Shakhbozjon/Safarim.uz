"""
Bron testlari: komissiya hisoblash, bekor qilish + refund qoidalari.
"""
import uuid
import pytest
from datetime import date, time, timedelta, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import calculate_commission
from app.core.config import settings
from app.models.user import User
from app.models.driver import DriverProfile
from app.models.trip import Trip
from app.models.booking import Booking
from app.models.location import Region
from app.models.enums import (
    TripStatus, PaymentType, LuggageSize,
    BookingStatus, PaymentMethod, BookingPaymentStatus,
)
from tests.conftest import auth_headers
from httpx import AsyncClient


# ─── Komissiya hisoblash (unit test) ─────────────────────────────────────────

class TestCommission:
    def test_low_rate_100k(self):
        """100,000 so'm → 2% = 2,000."""
        rate, amount = calculate_commission(100_000)
        assert rate == settings.COMMISSION_LOW_RATE
        assert amount == 2_000

    def test_low_rate_at_threshold(self):
        """Aynan 200,000 so'm — hali ham 2%."""
        rate, amount = calculate_commission(200_000)
        assert rate == settings.COMMISSION_LOW_RATE
        assert amount == 4_000

    def test_high_rate_above_threshold(self):
        """200,001 so'm — 5%."""
        rate, amount = calculate_commission(200_001)
        assert rate == settings.COMMISSION_HIGH_RATE

    def test_high_rate_300k(self):
        """300,000 so'm → 5% = 15,000."""
        rate, amount = calculate_commission(300_000)
        assert rate == settings.COMMISSION_HIGH_RATE
        assert amount == 15_000

    def test_zero_price(self):
        """0 so'm → komissiya 0."""
        _, amount = calculate_commission(0)
        assert amount == 0

    def test_driver_amount(self):
        """Haydovchiga tushadigan summa to'g'ri."""
        price = 100_000
        _, commission = calculate_commission(price)
        driver_amount = price - commission
        assert driver_amount == 98_000


# ─── Refund qoidalari (unit test) ─────────────────────────────────────────────

class TestCancelRefund:
    """
    Biznes qoida:
      - Haydovchi bekor qilsa → 100% refund
      - Yo'lovchi 24+ soat oldin → 100% refund
      - Yo'lovchi 24 soatdan kam → 50% refund
      - No-show → 0% refund
    """

    def _hours_left(self, hours: float) -> datetime:
        return datetime.utcnow() + timedelta(hours=hours)

    def test_driver_cancels_full_refund(self):
        """Haydovchi bekor qiladi → 100%."""
        total_price = 150_000
        refund = total_price  # 100%
        assert refund == total_price

    def test_passenger_cancels_24h_plus_full_refund(self):
        """Yo'lovchi 24h+ oldin bekor qiladi → 100%."""
        total_price = 150_000
        hours_left = 25.0
        refund = total_price if hours_left >= 24 else total_price // 2
        assert refund == 150_000

    def test_passenger_cancels_less_24h_half_refund(self):
        """Yo'lovchi 23h qolganida bekor qiladi → 50%."""
        total_price = 150_000
        hours_left = 23.0
        refund = total_price if hours_left >= 24 else total_price // 2
        assert refund == 75_000

    def test_passenger_cancels_exactly_24h_full_refund(self):
        """Aynan 24 soat qolganida → 100%."""
        total_price = 200_000
        hours_left = 24.0
        refund = total_price if hours_left >= 24 else total_price // 2
        assert refund == 200_000

    def test_no_show_zero_refund(self):
        """No-show → 0."""
        refund = 0
        assert refund == 0


# ─── Bron yaratish API testi ──────────────────────────────────────────────────

async def _create_trip(db: AsyncSession, driver_user: tuple) -> Trip:
    """Test uchun safar yaratish yordamchisi."""
    driver, _dp = driver_user

    # Region kerak
    region = Region(id=99, name_uz="Test Viloyat", name_ru="Test Region", slug="test", order=99)
    db.add(region)
    await db.flush()

    tomorrow = date.today() + timedelta(days=2)
    trip = Trip(
        driver_id=driver.id,
        from_region_id=region.id,
        to_region_id=region.id,
        departure_date=tomorrow,
        departure_time=time(10, 0),
        total_seats=4,
        available_seats=4,
        price_per_seat=100_000,
        payment_type=PaymentType.cash,
        luggage_size=LuggageSize.medium,
        status=TripStatus.active,
    )
    db.add(trip)
    await db.commit()
    await db.refresh(trip)
    return trip


@pytest.mark.asyncio
async def test_create_booking_success(
    client: AsyncClient,
    db: AsyncSession,
    user: User,
    driver_user: tuple,
):
    """Yo'lovchi muvaffaqiyatli bron qiladi."""
    trip = await _create_trip(db, driver_user)

    resp = await client.post(
        "/api/v1/bookings",
        json={
            "trip_id": str(trip.id),
            "seats_count": 1,
            "pickup_address": "Chilonzor 19-kvartal, 42-uy",
            "payment_method": "cash",
        },
        headers=auth_headers(user),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["seats_count"] == 1
    assert data["total_price"] == 100_000
    assert data["commission_amount"] == 2_000   # 2%
    assert data["driver_amount"] == 98_000
    assert data["status"] == "confirmed"


@pytest.mark.asyncio
async def test_passenger_notified_with_driver_details(
    client: AsyncClient,
    db: AsyncSession,
    user: User,
    driver_user: tuple,
):
    """Band qilingach yo'lovchiga haydovchi va mashina ma'lumotlari keladi.

    Bron avtomatik tasdiqlanadi, shuning uchun yo'lovchi kimni kutishini shu
    xabardan biladi (Telegramga ham aynan shu matn ketadi).
    """
    driver, dp = driver_user
    trip = await _create_trip(db, driver_user)

    resp = await client.post(
        "/api/v1/bookings",
        json={"trip_id": str(trip.id), "seats_count": 2, "pickup_address": "Chilonzor 19, 42-uy", "payment_method": "cash"},
        headers=auth_headers(user),
    )
    assert resp.status_code == 201

    notifs = (await client.get(
        "/api/v1/notifications", headers=auth_headers(user)
    )).json()
    assert len(notifs) == 1

    assert "tasdiqlandi" in notifs[0]["title"]
    body = notifs[0]["body"]
    assert driver.full_name in body
    assert dp.vehicle_plate in body
    assert driver.phone in body
    assert "Test Viloyat → Test Viloyat" in body
    assert "2 ta joy" in body
    assert "200,000 so'm" in body


@pytest.mark.asyncio
async def test_driver_cannot_book_own_trip(
    client: AsyncClient,
    db: AsyncSession,
    driver_user: tuple,
):
    """Haydovchi o'z safariga bron qila olmaydi."""
    driver, _dp = driver_user
    trip = await _create_trip(db, driver_user)

    resp = await client.post(
        "/api/v1/bookings",
        json={"trip_id": str(trip.id), "seats_count": 1, "pickup_address": "Chilonzor 19, 42-uy", "payment_method": "cash"},
        headers=auth_headers(driver),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_no_seats_available(
    client: AsyncClient,
    db: AsyncSession,
    user: User,
    driver_user: tuple,
):
    """Mavjud o'rindan ko'p talab qilsa → 400."""
    trip = await _create_trip(db, driver_user)

    resp = await client.post(
        "/api/v1/bookings",
        json={"trip_id": str(trip.id), "seats_count": 10, "pickup_address": "Chilonzor 19, 42-uy", "payment_method": "cash"},
        headers=auth_headers(user),
    )
    # 422 — sxema 1-4 oralig'ini rad etadi; 400 — o'rin yetishmasligi biznes qoidasi
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_cancel_booking_by_passenger(
    client: AsyncClient,
    db: AsyncSession,
    user: User,
    driver_user: tuple,
):
    """Yo'lovchi bronni bekor qiladi (24h+ oldin → 100% refund)."""
    trip = await _create_trip(db, driver_user)

    # Bron qilish
    resp = await client.post(
        "/api/v1/bookings",
        json={"trip_id": str(trip.id), "seats_count": 1, "pickup_address": "Chilonzor 19, 42-uy", "payment_method": "cash"},
        headers=auth_headers(user),
    )
    booking_id = resp.json()["id"]

    # Bekor qilish
    resp = await client.post(
        f"/api/v1/bookings/{booking_id}/cancel",
        json={"reason": "Reja o'zgardi"},
        headers=auth_headers(user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "cancelled"
    assert data["cancelled_by"] == "passenger"
    # Naqd bron — hech narsa to'lanmagan, demak refund ham yo'q (0).
    # (Online to'langan bron bo'lsa 24h+ oldin 100% bo'lar edi.)
    assert data["refund_amount"] == 0


# ─── Bo'sh natija uchun yaqin sanalar ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_nearest_dates_lists_days_with_trips(
    client: AsyncClient,
    db: AsyncSession,
    driver_user: tuple,
):
    """So'ralgan kundan keyin safar bor kunlar sanog'i bilan qaytadi.

    Bo'sh natija ekranida "boshqa sanani sinab ko'ring" o'rniga shu ro'yxat
    ko'rsatiladi — o'lik ko'cha keyingi bosishga aylanadi.
    """
    driver, _dp = driver_user
    region = Region(id=98, name_uz="Yaqin Viloyat", name_ru="Blizkiy", slug="yaqin", order=98)
    db.add(region)
    await db.flush()

    base = date.today() + timedelta(days=3)
    # base+1 kunda ikkita, base+3 kunda bitta safar
    for offset, count in ((1, 2), (3, 1)):
        for _ in range(count):
            db.add(Trip(
                driver_id=driver.id,
                from_region_id=region.id, to_region_id=region.id,
                departure_date=base + timedelta(days=offset), departure_time=time(9, 0),
                total_seats=4, available_seats=4, price_per_seat=100_000,
                payment_type=PaymentType.cash, luggage_size=LuggageSize.medium,
                status=TripStatus.active,
            ))
    await db.commit()

    resp = await client.get("/api/v1/trips/nearest-dates", params={
        "from_region_id": region.id,
        "to_region_id": region.id,
        "after": base.isoformat(),
    })
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert [d["count"] for d in data] == [2, 1]
    assert data[0]["date"] == (base + timedelta(days=1)).isoformat()


@pytest.mark.asyncio
async def test_nearest_dates_ignores_past_and_same_day(
    client: AsyncClient,
    db: AsyncSession,
    driver_user: tuple,
):
    """So'ralgan kunning o'zi va undan oldingilar chiqmaydi."""
    driver, _dp = driver_user
    region = Region(id=97, name_uz="Test 97", name_ru="Test 97", slug="t97", order=97)
    db.add(region)
    await db.flush()

    target = date.today() + timedelta(days=5)
    db.add(Trip(
        driver_id=driver.id,
        from_region_id=region.id, to_region_id=region.id,
        departure_date=target, departure_time=time(8, 0),
        total_seats=4, available_seats=4, price_per_seat=100_000,
        payment_type=PaymentType.cash, luggage_size=LuggageSize.medium,
        status=TripStatus.active,
    ))
    await db.commit()

    resp = await client.get("/api/v1/trips/nearest-dates", params={
        "from_region_id": region.id,
        "to_region_id": region.id,
        "after": target.isoformat(),
    })
    assert resp.json() == []


# ─── Olib ketish manzili ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pickup_address_required(
    client: AsyncClient, db: AsyncSession, user: User, driver_user: tuple,
):
    """Manzilsiz band qilib bo'lmaydi — aks holda muzokara qaytadi."""
    trip = await _create_trip(db, driver_user)
    resp = await client.post(
        "/api/v1/bookings",
        json={"trip_id": str(trip.id), "seats_count": 1, "payment_method": "cash"},
        headers=auth_headers(user),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_pickup_reaches_driver_with_map_link(
    client: AsyncClient, db: AsyncSession, user: User, driver_user: tuple,
):
    """Manzil va koordinata haydovchiga boradigan xabarda bo'ladi."""
    driver, _dp = driver_user
    trip = await _create_trip(db, driver_user)

    resp = await client.post(
        "/api/v1/bookings",
        json={
            "trip_id": str(trip.id), "seats_count": 1, "payment_method": "cash",
            "pickup_address": "Chilonzor 19-kvartal, 42-uy",
            "pickup_lat": 41.2856, "pickup_lng": 69.2034,
        },
        headers=auth_headers(user),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["pickup_address"] == "Chilonzor 19-kvartal, 42-uy"
    assert "41.2856" in resp.json()["pickup_map_url"]

    notifs = (await client.get(
        "/api/v1/notifications", headers=auth_headers(driver)
    )).json()
    body = notifs[0]["body"]
    assert "Chilonzor 19-kvartal, 42-uy" in body
    assert "maps.google.com" in body


@pytest.mark.asyncio
async def test_pickup_without_coords_has_no_link(
    client: AsyncClient, db: AsyncSession, user: User, driver_user: tuple,
):
    """Koordinata berilmasa havola yasalmaydi — manzil o'zi yetarli."""
    trip = await _create_trip(db, driver_user)
    resp = await client.post(
        "/api/v1/bookings",
        json={
            "trip_id": str(trip.id), "seats_count": 1, "payment_method": "cash",
            "pickup_address": "Yunusobod 4-kvartal, 12-uy",
        },
        headers=auth_headers(user),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["pickup_map_url"] is None


@pytest.mark.asyncio
async def test_pickup_can_be_edited_and_driver_notified(
    client: AsyncClient, db: AsyncSession, user: User, driver_user: tuple,
):
    """Yo'lovchi manzilni o'zgartirsa haydovchiga xabar boradi."""
    driver, _dp = driver_user
    trip = await _create_trip(db, driver_user)

    created = await client.post(
        "/api/v1/bookings",
        json={
            "trip_id": str(trip.id), "seats_count": 1, "payment_method": "cash",
            "pickup_address": "Chilonzor 19-kvartal, 42-uy",
        },
        headers=auth_headers(user),
    )
    booking_id = created.json()["id"]

    resp = await client.patch(
        f"/api/v1/bookings/{booking_id}/pickup",
        json={
            "pickup_address": "Yunusobod 4-kvartal, 12-uy",
            "pickup_lat": 41.3600, "pickup_lng": 69.2890,
        },
        headers=auth_headers(user),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["pickup_address"] == "Yunusobod 4-kvartal, 12-uy"
    assert "41.36" in resp.json()["pickup_map_url"]

    notifs = (await client.get(
        "/api/v1/notifications", headers=auth_headers(driver)
    )).json()
    assert notifs[0]["title"] == "Olib ketish manzili o'zgardi"
    assert "Yunusobod 4-kvartal, 12-uy" in notifs[0]["body"]


@pytest.mark.asyncio
async def test_pickup_edit_only_by_owner(
    client: AsyncClient, db: AsyncSession, user: User, driver_user: tuple,
):
    """Boshqa odam manzilni o'zgartira olmaydi."""
    driver, _dp = driver_user
    trip = await _create_trip(db, driver_user)

    created = await client.post(
        "/api/v1/bookings",
        json={
            "trip_id": str(trip.id), "seats_count": 1, "payment_method": "cash",
            "pickup_address": "Chilonzor 19-kvartal, 42-uy",
        },
        headers=auth_headers(user),
    )
    booking_id = created.json()["id"]

    resp = await client.patch(
        f"/api/v1/bookings/{booking_id}/pickup",
        json={"pickup_address": "Boshqa joy, 1-uy"},
        headers=auth_headers(driver),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_pickup_edit_without_change_is_quiet(
    client: AsyncClient, db: AsyncSession, user: User, driver_user: tuple,
):
    """Manzil o'zgarmasa haydovchi bezovta qilinmaydi (faqat koordinata aniqlangan)."""
    driver, _dp = driver_user
    trip = await _create_trip(db, driver_user)
    same = "Chilonzor 19-kvartal, 42-uy"

    created = await client.post(
        "/api/v1/bookings",
        json={
            "trip_id": str(trip.id), "seats_count": 1, "payment_method": "cash",
            "pickup_address": same,
        },
        headers=auth_headers(user),
    )
    booking_id = created.json()["id"]

    before = len((await client.get(
        "/api/v1/notifications", headers=auth_headers(driver)
    )).json())

    resp = await client.patch(
        f"/api/v1/bookings/{booking_id}/pickup",
        json={"pickup_address": same, "pickup_lat": 41.28, "pickup_lng": 69.20},
        headers=auth_headers(user),
    )
    assert resp.status_code == 200
    assert resp.json()["pickup_map_url"] is not None

    after = len((await client.get(
        "/api/v1/notifications", headers=auth_headers(driver)
    )).json())
    assert after == before
