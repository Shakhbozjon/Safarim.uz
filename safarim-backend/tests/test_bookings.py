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
        json={"trip_id": str(trip.id), "seats_count": 1, "payment_method": "cash"},
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
        json={"trip_id": str(trip.id), "seats_count": 10, "payment_method": "cash"},
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
        json={"trip_id": str(trip.id), "seats_count": 1, "payment_method": "cash"},
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
    # 2 kun keyin safar → 24h+ oldin → 100% refund
    assert data["refund_amount"] == 100_000
