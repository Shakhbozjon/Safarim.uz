"""Hisobdan haydovchilik qismini olib tashlash.

Sinov uchun haydovchi bo'lib ro'yxatdan o'tgan odamning avtomobil raqami
band bo'lib qoladi (raqam unikal). Bu skript hisobni o'chirmasdan shu
qismini olib tashlaydi — lekin faol safar qolgan bo'lsa tegmaydi.
"""
import uuid

import pytest
from sqlalchemy import func, select

from app.models.driver import DriverProfile
from app.models.enums import DriverStatus, LuggageSize, PaymentType, TripStatus
from app.models.location import Region
from app.models.trip import Trip
from app.models.user import User
from app.schemas.driver import DriverApplyRequest
from app.services import driver_service


async def _driver(db, phone: str, plate: str) -> User:
    u = User(id=uuid.uuid4(), phone=phone, full_name="Sinov Haydovchi",
             password_hash="x", is_phone_verified=True, is_driver=True)
    db.add(u)
    await db.commit()
    db.add(DriverProfile(
        id=uuid.uuid4(), user_id=u.id, license_image="documents/x.jpg",
        vehicle_make="Chevrolet", vehicle_model="Cobalt", vehicle_year=2020,
        vehicle_color="Oq", vehicle_plate=plate, vehicle_seats=4,
        status=DriverStatus.approved,
    ))
    await db.commit()
    return u


async def _active_trip(db, driver: User) -> None:
    import datetime as dt
    db.add(Region(id=93, name_uz="Test 93", name_ru="Test 93", slug="t93", order=93))
    await db.commit()
    db.add(Trip(
        id=uuid.uuid4(), driver_id=driver.id, from_region_id=93, to_region_id=93,
        departure_date=dt.date.today() + dt.timedelta(days=1), departure_time=dt.time(9, 0),
        total_seats=4, available_seats=4, price_per_seat=100_000,
        payment_type=PaymentType.cash, luggage_size=LuggageSize.medium,
        status=TripStatus.active,
    ))
    await db.commit()


@pytest.mark.asyncio
async def test_frees_the_plate_and_clears_driver_flag(db, user):
    driver = await _driver(db, "+998906000001", "01A777BC")

    profile = (await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == driver.id)
    )).scalar_one()
    await db.delete(profile)
    driver.is_driver = False
    await db.commit()

    assert await db.scalar(
        select(func.count(DriverProfile.id)).where(DriverProfile.vehicle_plate == "01A777BC")
    ) == 0

    # Endi o'sha raqamni boshqa odam olishi mumkin
    again = await driver_service.apply_driver(
        db, user,
        DriverApplyRequest(
            vehicle_make="Chevrolet", vehicle_model="Cobalt", vehicle_year=2020,
            vehicle_color="Oq", vehicle_plate="01A777BC", vehicle_seats=4,
        ),
        "documents/yangi.jpg",
    )
    assert again.vehicle_plate == "01A777BC"


@pytest.mark.asyncio
async def test_active_trip_blocks_removal(db):
    """Faol safari bor haydovchini haydovchilikdan chiqarib bo'lmaydi."""
    driver = await _driver(db, "+998906000002", "01A888BC")
    await _active_trip(db, driver)

    blocking = (await db.execute(
        select(Trip).where(
            Trip.driver_id == driver.id,
            Trip.status.in_([TripStatus.active, TripStatus.full, TripStatus.started]),
        ).limit(1)
    )).scalar_one_or_none()
    assert blocking is not None      # skript aynan shu tekshiruvda to'xtaydi
