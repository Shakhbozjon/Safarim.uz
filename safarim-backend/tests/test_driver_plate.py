"""Avtomobil raqami va qayta ariza berish.

Uchta holat qo'riqlanadi:
  1. Begona odam band raqamni olib qo'ya olmaydi (yozilish shakli muhim emas);
  2. Rad etilgan haydovchi O'Z mashinasi bilan qayta ariza bera oladi;
  3. Rad etilgan haydovchi boshqa mashina bilan ham qayta ariza bera oladi
     (ilgari bu `driver_profiles.user_id` cheklovini buzib 500 berardi).
"""
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.models.driver import DriverProfile
from app.models.enums import DriverStatus
from app.models.user import User
from app.schemas.driver import DriverApplyRequest
from app.services import driver_service


def _apply(plate: str) -> DriverApplyRequest:
    return DriverApplyRequest(
        vehicle_make="Chevrolet", vehicle_model="Cobalt",
        vehicle_color="Oq", vehicle_plate=plate, vehicle_seats=4,
    )


async def _second_user(db, like: User) -> User:
    u = User(
        id=uuid.uuid4(), phone="+998905555555", full_name="Ikkinchi haydovchi",
        password_hash=like.password_hash, is_phone_verified=True,
    )
    db.add(u)
    await db.commit()
    return u


@pytest.mark.asyncio
async def test_other_driver_cannot_take_busy_plate(db, user):
    other = await _second_user(db, user)
    await driver_service.apply_driver(db, user, _apply("01A123BC"), "docs/a.jpg")

    # Bo'sh joy va kichik harf bilan yozish ham yordam bermaydi —
    # raqam solishtirishdan oldin normallashtiriladi
    with pytest.raises(HTTPException) as e:
        await driver_service.apply_driver(db, other, _apply("01 a 123 bc"), "docs/b.jpg")
    assert e.value.status_code == 400
    assert "avtomobil raqami" in e.value.detail.lower()


@pytest.mark.asyncio
async def test_rejected_driver_can_reapply_with_same_car(db, user, admin_user):
    dp = await driver_service.apply_driver(db, user, _apply("01A123BC"), "docs/a.jpg")
    await driver_service.reject_driver(db, str(dp.id), admin_user, "Rasm noaniq")

    again = await driver_service.apply_driver(db, user, _apply("01A123BC"), "docs/a2.jpg")
    assert again.status == DriverStatus.pending
    assert again.rejection_reason is None
    assert again.license_image == "docs/a2.jpg"


@pytest.mark.asyncio
async def test_rejected_driver_can_reapply_with_other_car(db, user, admin_user):
    dp = await driver_service.apply_driver(db, user, _apply("01A123BC"), "docs/a.jpg")
    await driver_service.reject_driver(db, str(dp.id), admin_user, "Boshqa mashina kerak")

    again = await driver_service.apply_driver(db, user, _apply("30BB777AA"), "docs/a3.jpg")
    assert again.vehicle_plate == "30BB777AA"
    assert again.status == DriverStatus.pending

    # Ikkinchi yozuv yaratilmadi — o'sha yozuv yangilandi
    count = await db.scalar(
        select(func.count()).select_from(DriverProfile).where(DriverProfile.user_id == user.id)
    )
    assert count == 1
    # Eski raqam bo'shadi: endi uni boshqa odam ola oladi
    other = await _second_user(db, user)
    freed = await driver_service.apply_driver(db, other, _apply("01A123BC"), "docs/b.jpg")
    assert freed.vehicle_plate == "01A123BC"


@pytest.mark.asyncio
async def test_pending_and_approved_are_still_blocked(db, user, admin_user):
    dp = await driver_service.apply_driver(db, user, _apply("01A123BC"), "docs/a.jpg")

    with pytest.raises(HTTPException) as e:
        await driver_service.apply_driver(db, user, _apply("30BB777AA"), "docs/b.jpg")
    assert "ko'rib chiqilmoqda" in e.value.detail

    await driver_service.approve_driver(db, str(dp.id), admin_user)
    with pytest.raises(HTTPException) as e:
        await driver_service.apply_driver(db, user, _apply("30BB777AA"), "docs/c.jpg")
    assert "tasdiqlangansiz" in e.value.detail
