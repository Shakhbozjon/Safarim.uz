from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.user import User
from app.models.driver import DriverProfile
from app.models.payment import DriverMonthlyCommission
from app.models.enums import DriverStatus, AdminActionType, NotificationRefType
from app.models.admin import AdminAction
from app.schemas.driver import DriverApplyRequest, UpdatePreferencesRequest
from app.core.config import settings
from app.services import notification_service, wallet_service


async def apply_driver(
    db: AsyncSession,
    user: User,
    data: DriverApplyRequest,
    license_key: str,
) -> DriverProfile:
    # Allaqachon ariza topshirganmi?
    if user.is_driver:
        result = await db.execute(
            select(DriverProfile).where(DriverProfile.user_id == user.id)
        )
        existing = result.scalar_one_or_none()
        if existing and existing.status == DriverStatus.pending:
            raise HTTPException(status_code=400, detail="Arizangiz ko'rib chiqilmoqda")
        if existing and existing.status == DriverStatus.approved:
            raise HTTPException(status_code=400, detail="Siz allaqachon haydovchi sifatida tasdiqlangansiz")

    # Avtomobil raqami band emasligini tekshirish
    result = await db.execute(
        select(DriverProfile).where(DriverProfile.vehicle_plate == data.vehicle_plate)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bu avtomobil raqami allaqachon ro'yxatdan o'tgan")

    driver = DriverProfile(
        user_id=user.id,
        license_image=license_key,
        vehicle_make=data.vehicle_make,
        vehicle_model=data.vehicle_model,
        vehicle_year=data.vehicle_year,
        vehicle_color=data.vehicle_color,
        vehicle_plate=data.vehicle_plate,
        vehicle_seats=data.vehicle_seats,
        status=DriverStatus.pending,
    )
    db.add(driver)
    user.is_driver = True
    await db.commit()
    await db.refresh(driver)
    return driver


async def update_preferences(
    db: AsyncSession,
    user: User,
    data: UpdatePreferencesRequest,
) -> DriverProfile:
    result = await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == user.id)
    )
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Haydovchi profili topilmadi")
    if driver.status != DriverStatus.approved:
        raise HTTPException(status_code=403, detail="Profil tasdiqlanmagan")

    if data.smoking_allowed is not None:
        driver.smoking_allowed = data.smoking_allowed
    if data.pets_allowed is not None:
        driver.pets_allowed = data.pets_allowed
    if data.music_allowed is not None:
        driver.music_allowed = data.music_allowed
    if data.luggage_size is not None:
        driver.luggage_size = data.luggage_size
    if data.women_only is not None:
        driver.women_only = data.women_only

    await db.commit()
    await db.refresh(driver)
    return driver


async def toggle_pause(db: AsyncSession, user: User, pause: bool) -> DriverProfile:
    result = await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == user.id)
    )
    driver = result.scalar_one_or_none()
    if not driver or driver.status != DriverStatus.approved:
        raise HTTPException(status_code=403, detail="Tasdiqlanmagan haydovchi")

    driver.is_on_pause = pause
    await db.commit()
    await db.refresh(driver)
    return driver


async def get_driver_profile(db: AsyncSession, user: User) -> DriverProfile:
    result = await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == user.id)
    )
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Haydovchi profili topilmadi")
    return driver


async def get_monthly_earnings(db: AsyncSession, user: User) -> list[DriverMonthlyCommission]:
    result = await db.execute(
        select(DriverMonthlyCommission)
        .where(DriverMonthlyCommission.driver_id == user.id)
        .order_by(DriverMonthlyCommission.month.desc())
        .limit(12)
    )
    return result.scalars().all()


# ─── Admin funksiyalari ────────────────────────────────────────────────────────

async def get_pending_drivers(db: AsyncSession) -> list[DriverProfile]:
    result = await db.execute(
        select(DriverProfile)
        .options(selectinload(DriverProfile.user))
        .where(DriverProfile.status == DriverStatus.pending)
        .order_by(DriverProfile.created_at.asc())
    )
    return result.scalars().all()


async def approve_driver(db: AsyncSession, driver_id: str, admin: User) -> DriverProfile:
    import uuid
    result = await db.execute(
        select(DriverProfile).where(DriverProfile.id == uuid.UUID(driver_id))
    )
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Haydovchi topilmadi")
    if driver.status == DriverStatus.approved:
        raise HTTPException(status_code=400, detail="Allaqachon tasdiqlangan")

    driver.status = DriverStatus.approved
    driver.verified_at = datetime.utcnow()
    driver.verified_by = admin.id
    driver.rejection_reason = None

    action = AdminAction(
        admin_id=admin.id,
        action_type=AdminActionType.approve_driver,
        target_user_id=driver.user_id,
        reason="Hujjatlar tekshirildi va tasdiqlandi",
    )
    db.add(action)

    # Haydovchiga bildirishnoma
    await notification_service.create(
        db,
        user_id=driver.user_id,
        title="Haydovchilik tasdiqlandi! 🎉",
        body="Tabriklaymiz! Siz haydovchi sifatida tasdiqlandingiz. Endi safar yarata olasiz.",
        ref_type=NotificationRefType.system,
    )

    # Hamyon avtomatik yaratiladi
    await wallet_service.get_or_create(db, driver.user_id)

    await db.commit()
    await db.refresh(driver)
    return driver


async def reject_driver(db: AsyncSession, driver_id: str, admin: User, reason: str) -> DriverProfile:
    import uuid
    result = await db.execute(
        select(DriverProfile).where(DriverProfile.id == uuid.UUID(driver_id))
    )
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Haydovchi topilmadi")
    if driver.status == DriverStatus.approved:
        raise HTTPException(status_code=400, detail="Tasdiqlangan haydovchi rad etilmaydi")

    driver.status = DriverStatus.rejected
    driver.rejection_reason = reason

    # Foydalanuvchi qayta ariza topshira olishi uchun is_driver=False
    result_user = await db.execute(select(User).where(User.id == driver.user_id))
    u = result_user.scalar_one_or_none()
    if u:
        u.is_driver = False

    action = AdminAction(
        admin_id=admin.id,
        action_type=AdminActionType.reject_driver,
        target_user_id=driver.user_id,
        reason=reason,
    )
    db.add(action)

    # Haydovchiga bildirishnoma
    await notification_service.create(
        db,
        user_id=driver.user_id,
        title="Ariza rad etildi",
        body=f"Haydovchilik arizangiz rad etildi. Sabab: {reason}",
        ref_type=NotificationRefType.system,
    )

    await db.commit()
    await db.refresh(driver)
    return driver
