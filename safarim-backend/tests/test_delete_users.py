"""Sinov hisoblarini bazadan o'chirish skripti.

Bu qaytarib bo'lmaydigan amal, shuning uchun ikki narsa qo'riqlanadi:
admin hisobi hech qachon o'chmasin va bog'liq yozuvlar (safar, bron,
hamyon, bildirishnoma) chet kalit xatosisiz to'g'ri tartibda o'chsin.
"""
import datetime as dt
import uuid

import pytest
from sqlalchemy import func, select

from app.models.booking import Booking
from app.models.driver import DriverProfile
from app.models.enums import (
    BookingPaymentStatus, BookingStatus, DriverStatus, LuggageSize,
    NotificationChannel, PaymentMethod, PaymentType, TripStatus,
)
from app.models.location import Region
from app.models.notification import Notification
from app.models.trip import Trip
from app.models.user import User
from app.models.wallet import DriverWallet

from scripts.delete_users import _collect, _delete


async def _full_driver(db, phone: str) -> User:
    """Haydovchi + safar + boshqa odamning broni + hamyon + bildirishnoma."""
    driver = User(id=uuid.uuid4(), phone=phone, full_name="Sinov Haydovchi",
                  password_hash="x", is_driver=True, is_phone_verified=True)
    passenger = User(id=uuid.uuid4(), phone="+998907000001", full_name="Begona Yo'lovchi",
                     password_hash="x", is_phone_verified=True)
    region = Region(id=95, name_uz="Test 95", name_ru="Test 95", slug="t95", order=95)
    db.add_all([driver, passenger, region])
    await db.commit()

    db.add(DriverProfile(
        id=uuid.uuid4(), user_id=driver.id, license_image="documents/x.jpg",
        vehicle_make="Chevrolet", vehicle_model="Cobalt", vehicle_year=2020,
        vehicle_color="Oq", vehicle_plate="01A555BC", vehicle_seats=4,
        status=DriverStatus.approved,
    ))
    db.add(DriverWallet(id=uuid.uuid4(), driver_id=driver.id, balance=0))
    trip = Trip(
        id=uuid.uuid4(), driver_id=driver.id, from_region_id=95, to_region_id=95,
        departure_date=dt.date.today(), departure_time=dt.time(9, 0),
        total_seats=4, available_seats=3, price_per_seat=100_000,
        payment_type=PaymentType.cash, luggage_size=LuggageSize.medium,
        status=TripStatus.active,
    )
    db.add(trip)
    await db.commit()

    db.add(Booking(
        id=uuid.uuid4(), trip_id=trip.id, passenger_id=passenger.id,
        seats_count=1, price_per_seat=100_000, total_price=100_000,
        commission_rate=0.02, commission_amount=2_000, driver_amount=98_000,
        payment_method=PaymentMethod.cash, payment_status=BookingPaymentStatus.pending,
        status=BookingStatus.confirmed,
    ))
    db.add(Notification(
        id=uuid.uuid4(), user_id=driver.id, channel=NotificationChannel.inapp,
        title="Sinov", body="Sinov xabari",
    ))
    await db.commit()
    return driver


@pytest.mark.asyncio
async def test_admin_is_never_deleted(db, admin_user: User):
    users, admins, missing, *_ = await _collect(db, [admin_user.phone])
    assert users == []                       # o'chiriladiganlar ro'yxatida yo'q
    assert [a.phone for a in admins] == [admin_user.phone]


@pytest.mark.asyncio
async def test_unknown_phone_is_reported(db):
    users, _, missing, *_ = await _collect(db, ["+998900000009"])
    assert users == []
    assert missing == ["+998900000009"]


@pytest.mark.asyncio
async def test_deletes_driver_with_all_related_rows(db):
    phone = "+998907000002"
    driver = await _full_driver(db, phone)

    users, _, _, trip_ids, booking_ids, others = await _collect(db, [phone])
    assert [u.id for u in users] == [driver.id]
    assert len(trip_ids) == 1
    assert len(booking_ids) == 1
    # Safarga begona odam bron qilgan — skript buni ogohlantirishi uchun sanaydi
    assert others == 1

    await _delete(db, users, trip_ids, booking_ids, [phone])

    assert await db.scalar(select(func.count(User.id)).where(User.phone == phone)) == 0
    assert await db.scalar(select(func.count(Trip.id))) == 0
    assert await db.scalar(select(func.count(Booking.id))) == 0
    assert await db.scalar(select(func.count(DriverProfile.id))) == 0
    assert await db.scalar(select(func.count(DriverWallet.id))) == 0
    assert await db.scalar(select(func.count(Notification.id))) == 0
    # Begona yo'lovchining o'zi qoladi — faqat uning broni o'chadi
    assert await db.scalar(
        select(func.count(User.id)).where(User.phone == "+998907000001")
    ) == 1
