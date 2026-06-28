from datetime import datetime
import uuid as uuid_lib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.db.session import get_db
from app.models.user import User
from app.models.driver import DriverProfile
from app.models.trip import Trip
from app.models.booking import Booking
from app.models.payment import DriverMonthlyCommission
from app.models.enums import DriverStatus, BookingStatus
from app.schemas.driver import AdminDriverListResponse, RejectDriverRequest, DriverProfileResponse
from app.schemas.user import UserResponse
from app.services import driver_service, wallet_service
from app.services.storage_service import storage_service
from app.core.dependencies import get_current_admin, get_current_super_admin
from app.core.config import settings


class AdminTopupRequest(BaseModel):
    amount: int
    note: str = ""


class ResolveDisputeRequest(BaseModel):
    happened: bool   # True = safar bo'ldi, False = bo'lmadi

router = APIRouter()


# ─── Haydovchi verifikatsiya ──────────────────────────────────────────────────

@router.get(
    "/drivers/pending",
    response_model=list[AdminDriverListResponse],
    summary="Tekshirilishi kerak haydovchilar",
)
async def get_pending_drivers(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await driver_service.get_pending_drivers(db)


@router.get(
    "/drivers/{driver_id}/documents",
    summary="Haydovchi hujjatlarini ko'rish (URL)",
)
async def get_driver_documents(
    driver_id: str,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    result = await db.execute(
        select(DriverProfile).where(DriverProfile.id == uuid.UUID(driver_id))
    )
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Haydovchi topilmadi")

    return {
        "license_url": storage_service.get_url(driver.license_image, settings.MINIO_BUCKET_DOCUMENTS),
        "vehicle": {
            "make": driver.vehicle_make,
            "model": driver.vehicle_model,
            "year": driver.vehicle_year,
            "color": driver.vehicle_color,
            "plate": driver.vehicle_plate,
            "seats": driver.vehicle_seats,
        },
    }


@router.post(
    "/drivers/{driver_id}/approve",
    response_model=DriverProfileResponse,
    summary="Haydovchini tasdiqlash",
)
async def approve_driver(
    driver_id: str,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await driver_service.approve_driver(db, driver_id, admin)


@router.post(
    "/drivers/{driver_id}/reject",
    response_model=DriverProfileResponse,
    summary="Haydovchini rad etish",
)
async def reject_driver(
    driver_id: str,
    data: RejectDriverRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await driver_service.reject_driver(db, driver_id, admin, data.reason)


# ─── Foydalanuvchi boshqaruvi ─────────────────────────────────────────────────

@router.get(
    "/users",
    summary="Barcha foydalanuvchilar",
)
async def list_users(
    page: int = 1,
    limit: int = 20,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    )
    users = result.scalars().all()
    total = await db.scalar(select(func.count(User.id)))
    return {"total": total, "page": page, "users": users}


@router.post(
    "/users/{user_id}/block",
    summary="Foydalanuvchini bloklash",
)
async def block_user(
    user_id: str,
    reason: str,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    from app.models.admin import AdminAction
    from app.models.enums import AdminActionType

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    if user.is_admin:
        raise HTTPException(status_code=403, detail="Admin bloklanmaydi")

    user.is_blocked = True
    user.block_reason = reason

    db.add(AdminAction(
        admin_id=admin.id,
        action_type=AdminActionType.block_user,
        target_user_id=user.id,
        reason=reason,
    ))
    await db.commit()
    return {"message": f"{user.full_name} bloklandi"}


@router.post(
    "/users/{user_id}/unblock",
    summary="Foydalanuvchini blokdan chiqarish",
)
async def unblock_user(
    user_id: str,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    from app.models.admin import AdminAction
    from app.models.enums import AdminActionType

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

    user.is_blocked = False
    user.block_reason = None

    db.add(AdminAction(
        admin_id=admin.id,
        action_type=AdminActionType.unblock_user,
        target_user_id=user.id,
        reason="Admin tomonidan blokdan chiqarildi",
    ))
    await db.commit()
    return {"message": f"{user.full_name} blokdan chiqarildi"}


# ─── Komissiya boshqaruvi ─────────────────────────────────────────────────────

@router.get(
    "/commissions",
    summary="Naqd pul komissiyalari (to'lanmagan)",
)
async def list_commissions(
    paid: bool = False,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    paid=false → to'lanmagan (default)
    paid=true  → to'langan tarix
    """
    result = await db.execute(
        select(DriverMonthlyCommission)
        .options(selectinload(DriverMonthlyCommission.driver))
        .where(DriverMonthlyCommission.is_paid == paid)
        .order_by(DriverMonthlyCommission.month.desc())
    )
    records = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "driver": {
                "id": str(r.driver.id),
                "full_name": r.driver.full_name,
                "phone": r.driver.phone,
            },
            "month": r.month.strftime("%Y-%m"),
            "total_cash_bookings": r.total_cash_bookings,
            "total_commission": r.total_commission,
            "is_paid": r.is_paid,
            "paid_at": r.paid_at,
        }
        for r in records
    ]


@router.post(
    "/commissions/{commission_id}/mark-paid",
    summary="Komissiyani to'landi deb belgilash",
)
async def mark_commission_paid(
    commission_id: str,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    result = await db.execute(
        select(DriverMonthlyCommission)
        .options(selectinload(DriverMonthlyCommission.driver))
        .where(DriverMonthlyCommission.id == uuid.UUID(commission_id))
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Yozuv topilmadi")
    if record.is_paid:
        raise HTTPException(status_code=400, detail="Allaqachon to'langan")

    record.is_paid = True
    record.paid_at = datetime.utcnow()
    await db.commit()

    return {
        "message": f"{record.driver.full_name} — {record.total_commission:,} so'm komissiya to'landi deb belgilandi",
        "paid_at": record.paid_at,
    }


# ─── Hamyon boshqaruvi ───────────────────────────────────────────────────────

@router.get(
    "/users/{user_id}/wallet",
    summary="Haydovchi hamyon holati (admin)",
)
async def get_driver_wallet(
    user_id: str,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        uid = uuid_lib.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Noto'g'ri ID format")
    return await wallet_service.get_wallet_info(db, uid)


@router.post(
    "/users/{user_id}/wallet/topup",
    summary="Haydovchi hamyonini to'ldirish (admin)",
)
async def admin_topup_wallet(
    user_id: str,
    data: AdminTopupRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if data.amount < 1_000:
        raise HTTPException(status_code=400, detail="Minimal miqdor: 1,000 so'm")
    try:
        uid = uuid_lib.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Noto'g'ri ID format")

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user or not user.is_driver:
        raise HTTPException(status_code=404, detail="Haydovchi topilmadi")

    wallet = await wallet_service.topup(db, uid, data.amount, check_min=False)
    await db.commit()
    return {
        "message": f"{user.full_name} hamyoniga {data.amount:,} so'm qo'shildi",
        "new_balance": wallet.balance,
        "is_blocked": wallet.is_blocked,
    }


# ─── Statistika ───────────────────────────────────────────────────────────────

@router.get(
    "/stats",
    summary="Umumiy statistika",
)
async def get_stats(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    total_users = await db.scalar(select(func.count(User.id)))
    total_drivers = await db.scalar(
        select(func.count(DriverProfile.id)).where(DriverProfile.status == DriverStatus.approved)
    )
    pending_drivers = await db.scalar(
        select(func.count(DriverProfile.id)).where(DriverProfile.status == DriverStatus.pending)
    )
    total_trips = await db.scalar(select(func.count(Trip.id)))
    total_bookings = await db.scalar(select(func.count(Booking.id)))
    completed_bookings = await db.scalar(
        select(func.count(Booking.id)).where(Booking.status == BookingStatus.completed)
    )

    disputed_bookings = await db.scalar(
        select(func.count(Booking.id)).where(Booking.status == BookingStatus.disputed)
    )

    return {
        "total_users": total_users,
        "total_drivers": total_drivers,
        "pending_drivers": pending_drivers,
        "total_trips": total_trips,
        "total_bookings": total_bookings,
        "completed_bookings": completed_bookings,
        "disputed_bookings": disputed_bookings,
    }


# ─── Nizoli bronlar (safar tasdiqi) ──────────────────────────────────────────

@router.get(
    "/disputes",
    summary="Nizoli bronlar (yo'lovchi 'bo'lmadi', haydovchi 'bo'ldi')",
)
async def list_disputes(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Booking)
        .options(
            selectinload(Booking.passenger),
            selectinload(Booking.trip).selectinload(Trip.from_region),
            selectinload(Booking.trip).selectinload(Trip.to_region),
            selectinload(Booking.trip).selectinload(Trip.driver).selectinload(User.driver_profile),
        )
        .where(Booking.status == BookingStatus.disputed)
        .order_by(Booking.confirmation_requested_at.asc())
    )
    bookings = result.scalars().all()

    out = []
    for b in bookings:
        t = b.trip
        drv = t.driver if t else None
        dp = drv.driver_profile if drv else None
        out.append({
            "id": str(b.id),
            "seats_count": b.seats_count,
            "total_price": b.total_price,
            "commission_amount": b.commission_amount,
            "payment_method": b.payment_method,
            "confirmation_requested_at": b.confirmation_requested_at,
            "route": f"{t.from_region.name_uz} → {t.to_region.name_uz}" if t else "—",
            "departure_date": t.departure_date if t else None,
            "departure_time": t.departure_time if t else None,
            "passenger": {
                "id": str(b.passenger.id),
                "full_name": b.passenger.full_name,
                "phone": b.passenger.phone,
            },
            "driver": {
                "id": str(drv.id) if drv else None,
                "full_name": drv.full_name if drv else "—",
                "phone": drv.phone if drv else None,
                "fake_confirmation_count": dp.fake_confirmation_count if dp else 0,
            },
        })
    return out


@router.post(
    "/disputes/{booking_id}/resolve",
    summary="Nizoni hal qilish (safar bo'ldi / bo'lmadi)",
)
async def resolve_dispute(
    booking_id: str,
    data: ResolveDisputeRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services import booking_service
    booking = await booking_service.admin_resolve_dispute(db, booking_id, data.happened, admin)
    return booking_service.serialize_booking(booking, admin)
