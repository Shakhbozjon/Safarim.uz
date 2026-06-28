"""
Ikki tomonlama safar tasdiqi + soxta belgilash jarimasi + admin nizo testlari.

Hal qilish jadvali (qator=yo'lovchi, ustun=haydovchi):
                Haydovchi Ha   Haydovchi Yo'q    Haydovchi Jim
  Yo'lovchi Ha   ✅ bo'ldi      ✅ bo'ldi+strike   ✅ bo'ldi
  Yo'lovchi Yo'q ⚠️ nizo        ❌ bo'lmadi        ❌ bo'lmadi
  Yo'lovchi Jim  ✅ bo'ldi      🔁→❌ (48s)         ✅ bo'ldi (48s)
"""
import uuid
from datetime import date, time, timedelta, datetime

import pytest
from sqlalchemy import select
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
    CONFIRM_YES, CONFIRM_NO,
)
from app.services import booking_service, wallet_service


# ─── Yordamchilar ────────────────────────────────────────────────────────────

async def _region(db: AsyncSession, rid: int = 99) -> Region:
    region = await db.get(Region, rid)
    if not region:
        region = Region(id=rid, name_uz="Test", name_ru="Test", slug=f"t{rid}", order=rid)
        db.add(region)
        await db.flush()
    return region


async def _past_booking(
    db: AsyncSession,
    driver: User,
    passenger: User,
    *,
    payment: PaymentMethod = PaymentMethod.cash,
    price: int = 100_000,
    seats: int = 1,
    status: BookingStatus = BookingStatus.confirmed,
) -> tuple[Trip, Booking]:
    """Jo'nash vaqti o'tgan safar + bron (tasdiqlash mumkin bo'lishi uchun)."""
    region = await _region(db)
    yesterday = date.today() - timedelta(days=1)
    trip = Trip(
        driver_id=driver.id,
        from_region_id=region.id,
        to_region_id=region.id,
        departure_date=yesterday,
        departure_time=time(10, 0),
        total_seats=4,
        available_seats=4 - seats,
        price_per_seat=price,
        payment_type=PaymentType.cash,
        luggage_size=LuggageSize.medium,
        status=TripStatus.active,
    )
    db.add(trip)
    await db.flush()

    total = price * seats
    rate, comm = calculate_commission(total)
    bk = Booking(
        trip_id=trip.id,
        passenger_id=passenger.id,
        seats_count=seats,
        price_per_seat=price,
        total_price=total,
        commission_rate=rate,
        commission_amount=comm,
        driver_amount=total - comm,
        payment_method=payment,
        payment_status=BookingPaymentStatus.pending,
        status=status,
    )
    db.add(bk)
    await db.commit()
    await db.refresh(bk)
    await db.refresh(trip)
    return trip, bk


async def _get_dp(db: AsyncSession, driver_id) -> DriverProfile:
    res = await db.execute(select(DriverProfile).where(DriverProfile.user_id == driver_id))
    return res.scalar_one()


# ─── Hal qilish jadvali ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_driver_yes_completes_and_charges_commission(db, user, driver_user):
    """Haydovchi "Ha" (yo'lovchi jim) → bo'ldi + naqd komissiya hamyondan ushiladi."""
    driver, _ = driver_user
    _, bk = await _past_booking(db, driver, user)

    result = await booking_service.confirm_booking(db, str(bk.id), driver, confirmed=True)
    assert result.status == BookingStatus.completed
    assert result.completed_at is not None

    wallet = await wallet_service.get_or_create(db, driver.id)
    assert wallet.balance == -2_000   # 100k → 2% komissiya ushildi


@pytest.mark.asyncio
async def test_passenger_yes_completes(db, user, driver_user):
    """Yo'lovchi "Ha" → bo'ldi."""
    driver, _ = driver_user
    _, bk = await _past_booking(db, driver, user)

    result = await booking_service.confirm_booking(db, str(bk.id), user, confirmed=True)
    assert result.status == BookingStatus.completed


@pytest.mark.asyncio
async def test_passenger_yes_driver_no_is_fake(db, user, driver_user):
    """Yo'lovchi "Ha" + haydovchi "Yo'q" → bo'ldi + soxtalik (strike)."""
    driver, _ = driver_user
    _, bk = await _past_booking(db, driver, user)

    # Avval haydovchi "Yo'q" deydi → kutiladi
    await booking_service.confirm_booking(db, str(bk.id), driver, confirmed=False)
    # Keyin yo'lovchi "Ha" deydi → bo'ldi + strike
    result = await booking_service.confirm_booking(db, str(bk.id), user, confirmed=True)

    assert result.status == BookingStatus.completed
    dp = await _get_dp(db, driver.id)
    assert dp.fake_confirmation_count == 1


@pytest.mark.asyncio
async def test_passenger_no_then_driver_yes_disputed(db, user, driver_user):
    """Yo'lovchi "Yo'q" (kutadi) → keyin haydovchi "Ha" → nizo (admin)."""
    driver, _ = driver_user
    _, bk = await _past_booking(db, driver, user)

    # Yo'lovchi "Yo'q" — darhol yopilmaydi, haydovchining javobini kutadi
    r1 = await booking_service.confirm_booking(db, str(bk.id), user, confirmed=False)
    assert r1.status == BookingStatus.awaiting_confirmation
    # Haydovchi "Ha" → nizo
    r2 = await booking_service.confirm_booking(db, str(bk.id), driver, confirmed=True)
    assert r2.status == BookingStatus.disputed


@pytest.mark.asyncio
async def test_both_no_not_happened_no_commission(db, user, driver_user):
    """Ikkalasi "Yo'q" → bo'lmadi, komissiya yo'q."""
    driver, _ = driver_user
    _, bk = await _past_booking(db, driver, user)

    await booking_service.confirm_booking(db, str(bk.id), user, confirmed=False)    # yo'lovchi yo'q (kutadi)
    result = await booking_service.confirm_booking(db, str(bk.id), driver, confirmed=False)  # haydovchi ham yo'q
    assert result.status in (BookingStatus.cancelled, BookingStatus.no_show)

    wallet = await wallet_service.get_or_create(db, driver.id)
    assert wallet.balance == 0   # komissiya ushilmadi


@pytest.mark.asyncio
async def test_passenger_no_alone_waits(db, user, driver_user):
    """Yo'lovchi "Yo'q" (haydovchi jim) → darhol yopilmaydi, kutadi (nizo imkoniyati uchun)."""
    driver, _ = driver_user
    _, bk = await _past_booking(db, driver, user)

    result = await booking_service.confirm_booking(db, str(bk.id), user, confirmed=False)
    assert result.status == BookingStatus.awaiting_confirmation
    assert result.passenger_confirmed == CONFIRM_NO


# ─── Avtomatik hal qilish (48 soat) ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_both_silent_autocompletes(db, user, driver_user):
    """Ikkala jim + 48s o'tdi → bo'ldi (komissiya himoyasi)."""
    driver, _ = driver_user
    _, bk = await _past_booking(db, driver, user, status=BookingStatus.awaiting_confirmation)
    bk.confirmation_requested_at = datetime.utcnow() - timedelta(hours=49)
    await db.commit()

    resolved = await booking_service.resolve_due_confirmations(db)
    assert resolved == 1
    await db.refresh(bk)
    assert bk.status == BookingStatus.completed


@pytest.mark.asyncio
async def test_driver_no_passenger_silent_final_not_happened(db, user, driver_user):
    """Haydovchi "Yo'q" + yo'lovchi jim + 48s → bo'lmadi."""
    driver, _ = driver_user
    _, bk = await _past_booking(db, driver, user, status=BookingStatus.awaiting_confirmation)
    bk.driver_confirmed = CONFIRM_NO
    bk.confirmation_requested_at = datetime.utcnow() - timedelta(hours=49)
    await db.commit()

    resolved = await booking_service.resolve_due_confirmations(db)
    assert resolved == 1
    await db.refresh(bk)
    assert bk.status == BookingStatus.no_show


@pytest.mark.asyncio
async def test_window_not_expired_not_resolved(db, user, driver_user):
    """Oyna hali tugamagan (24s) → hal qilinmaydi."""
    driver, _ = driver_user
    _, bk = await _past_booking(db, driver, user, status=BookingStatus.awaiting_confirmation)
    bk.confirmation_requested_at = datetime.utcnow() - timedelta(hours=24)
    await db.commit()

    resolved = await booking_service.resolve_due_confirmations(db)
    assert resolved == 0


# ─── Soxta belgilash jarimasi (3-strike → pauza) ─────────────────────────────

@pytest.mark.asyncio
async def test_three_fakes_trigger_pause(db, user, driver_user):
    """3 marta soxtalik → paused_until belgilanadi, hisoblagich nolga tushadi."""
    driver, _ = driver_user
    for i in range(settings.FAKE_CONFIRMATION_BLOCK_THRESHOLD):
        _, bk = await _past_booking(db, driver, user, price=100_000 + i)
        await booking_service.confirm_booking(db, str(bk.id), driver, confirmed=False)
        await booking_service.confirm_booking(db, str(bk.id), user, confirmed=True)

    dp = await _get_dp(db, driver.id)
    assert dp.paused_until is not None
    assert dp.paused_until > datetime.utcnow()
    assert dp.fake_confirmation_count == 0   # penaltidan keyin nolga


# ─── Tasdiq vaqtidan oldin ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cannot_confirm_before_departure(db, user, driver_user):
    """Safar vaqti kelmagan bo'lsa tasdiqlab bo'lmaydi → 400."""
    from fastapi import HTTPException
    driver, _ = driver_user
    region = await _region(db)
    future = date.today() + timedelta(days=2)
    trip = Trip(
        driver_id=driver.id, from_region_id=region.id, to_region_id=region.id,
        departure_date=future, departure_time=time(10, 0), total_seats=4, available_seats=3,
        price_per_seat=100_000, payment_type=PaymentType.cash, luggage_size=LuggageSize.medium,
        status=TripStatus.active,
    )
    db.add(trip)
    await db.flush()
    bk = Booking(
        trip_id=trip.id, passenger_id=user.id, seats_count=1, price_per_seat=100_000,
        total_price=100_000, commission_rate=0.02, commission_amount=2_000, driver_amount=98_000,
        payment_method=PaymentMethod.cash, payment_status=BookingPaymentStatus.pending,
        status=BookingStatus.confirmed,
    )
    db.add(bk)
    await db.commit()

    with pytest.raises(HTTPException) as exc:
        await booking_service.confirm_booking(db, str(bk.id), driver, confirmed=True)
    assert exc.value.status_code == 400


# ─── Admin nizo hal qilish ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_resolves_dispute_happened(db, user, driver_user, admin_user):
    """Admin "safar bo'ldi" deydi → completed, komissiya ushiladi, strike yo'q."""
    driver, _ = driver_user
    _, bk = await _past_booking(db, driver, user, status=BookingStatus.disputed)
    bk.driver_confirmed = CONFIRM_YES
    bk.passenger_confirmed = CONFIRM_NO
    await db.commit()

    result = await booking_service.admin_resolve_dispute(db, str(bk.id), happened=True, admin=admin_user)
    assert result.status == BookingStatus.completed

    dp = await _get_dp(db, driver.id)
    assert dp.fake_confirmation_count == 0   # haydovchi haq edi — strike yo'q


@pytest.mark.asyncio
async def test_admin_resolves_dispute_not_happened_strikes_driver(db, user, driver_user, admin_user):
    """Admin "safar bo'lmadi" deydi → bo'lmadi + haydovchiga strike."""
    driver, _ = driver_user
    _, bk = await _past_booking(db, driver, user, status=BookingStatus.disputed)
    bk.driver_confirmed = CONFIRM_YES
    bk.passenger_confirmed = CONFIRM_NO
    await db.commit()

    result = await booking_service.admin_resolve_dispute(db, str(bk.id), happened=False, admin=admin_user)
    assert result.status in (BookingStatus.cancelled, BookingStatus.no_show)

    dp = await _get_dp(db, driver.id)
    assert dp.fake_confirmation_count == 1   # yolg'on "bo'ldi" → strike
