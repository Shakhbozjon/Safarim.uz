from datetime import datetime
import uuid as uuid_lib
from fastapi import APIRouter, Depends, HTTPException, Query
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
from app.services import admin_stats_service, driver_service, wallet_service
from app.services.storage_service import storage_service
from app.core.dependencies import get_current_admin, get_current_super_admin
from app.core.config import settings


class AdminTopupRequest(BaseModel):
    amount: int
    note: str = ""


# Admin qo'lda qo'shadigan eng katta summa (bitta amalda)
MAX_ADMIN_TOPUP = 5_000_000


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
    "/drivers",
    response_model=list[AdminDriverListResponse],
    summary="Haydovchilar ro'yxati (holat bo'yicha + qidiruv)",
)
async def list_drivers(
    status: str = Query("pending", pattern="^(pending|approved|rejected|all)$"),
    q: str | None = Query(None, description="Ism, telefon yoki avtomobil raqami"),
    needs_review: bool = Query(False, description="Hujjat yuklagan, hali tekshirilmaganlar"),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Tasdiqlangan haydovchini ham topib bo'lsin.

    Ilgari faqat `/drivers/pending` bor edi: ariza ko'rib chiqilgach haydovchi
    admin panelidan butunlay yo'qolardi — mashinasini yoki raqamini keyin
    tekshirishning yo'li qolmasdi.
    """
    return await driver_service.list_drivers(
        db,
        status=None if status == "all" else DriverStatus(status),
        q=q,
        needs_review=needs_review,
    )


@router.get(
    "/drivers/{driver_id}",
    response_model=AdminDriverListResponse,
    summary="Bitta haydovchi (holatidan qat'i nazar)",
)
async def get_driver(
    driver_id: str,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin sahifasi ilgari haydovchini "kutayotganlar" ro'yxatidan qidirardi —
    tasdiqlangani ochilmasdi. Avtomatik tasdiqlashda u ro'yxat butunlay bo'sh
    bo'ladi, shuning uchun bitta haydovchini olish yo'li kerak."""
    return await driver_service.get_driver_by_id(db, driver_id)


@router.get(
    "/drivers/{driver_id}/documents",
    summary="Haydovchi hujjatlarini ko'rish (URL)",
)
async def get_driver_documents(
    driver_id: str,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    driver = await driver_service.get_driver_by_id(db, driver_id)

    return {
        # Ishga tushirish davrida hujjat yuklash majburiy emas — admin
        # haydovchini yuzma-yuz ko'rib tasdiqlagan bo'lishi mumkin
        "license_url": (
            storage_service.get_url(driver.license_image, settings.MINIO_BUCKET_DOCUMENTS)
            if driver.license_image
            else None
        ),
        # Texpasport talabi kiritilgunga qadar tasdiqlangan haydovchilarda yo'q
        "tech_passport_url": (
            storage_service.get_url(driver.tech_passport_image, settings.MINIO_BUCKET_DOCUMENTS)
            if driver.tech_passport_image
            else None
        ),
        "vehicle": {
            "make": driver.vehicle_make,
            "model": driver.vehicle_model,
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
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, description="Ism yoki telefon bo'yicha qidiruv"),
    role: str = Query("all", pattern="^(all|driver|passenger|admin)$"),
    status_filter: str = Query("all", alias="status", pattern="^(all|blocked|unverified)$"),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ro'yxat + qidiruv + filtrlar.

    ⚠️ Qidiruv BAZADA bajariladi. Ilgari frontend faqat ochilgan sahifadagi
    20 ta qatorni filtrlardi — 5-sahifadagi odamni qidirib topib bo'lmasdi.
    """
    conditions = []
    if q:
        needle = f"%{q.strip().lower()}%"
        conditions.append(
            func.lower(User.full_name).like(needle) | User.phone.like(needle)
        )
    if role == "driver":
        conditions.append(User.is_driver.is_(True))
    elif role == "passenger":
        conditions.append(User.is_driver.is_(False))
    elif role == "admin":
        conditions.append(User.is_admin.is_(True))

    if status_filter == "blocked":
        conditions.append(User.is_blocked.is_(True))
    elif status_filter == "unverified":
        conditions.append(User.is_phone_verified.is_(False))

    offset = (page - 1) * limit
    result = await db.execute(
        select(User).where(*conditions).order_by(User.created_at.desc()).offset(offset).limit(limit)
    )
    users = result.scalars().all()
    total = await db.scalar(select(func.count(User.id)).where(*conditions))
    return {"total": total, "page": page, "limit": limit, "users": users}


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
    "/users/{user_id}/verify-phone",
    summary="Telefon raqamni qo'lda tasdiqlash (Telegrami yo'q foydalanuvchi uchun)",
)
async def verify_user_phone(
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
    if user.is_phone_verified:
        return {"message": f"{user.full_name} raqami allaqachon tasdiqlangan"}

    # Admin raqam egasi bilan bevosita bog'langan bo'lishi kerak — bu yozuv
    # keyin kim tasdiqlaganini aniqlash uchun qoladi.
    user.is_phone_verified = True
    db.add(AdminAction(
        admin_id=admin.id,
        action_type=AdminActionType.verify_phone,
        target_user_id=user.id,
        reason="Telefon raqami qo'lda tasdiqlandi (Telegramsiz)",
    ))
    await db.commit()
    return {"message": f"{user.full_name} raqami tasdiqlandi"}


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

    from app.models.admin import AdminAction
    from app.models.enums import AdminActionType

    record.is_paid = True
    record.paid_at = datetime.utcnow()
    db.add(AdminAction(
        admin_id=admin.id,
        action_type=AdminActionType.commission_paid,
        target_user_id=record.driver_id,
        reason=f"{record.total_commission:,} so'm komissiya to'landi deb belgilandi",
    ))
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

    # Yuqori chegara: bu yerda pul yo'qdan bor bo'ladi, shuning uchun bitta
    # noto'g'ri nol ham hisobni buzmasin.
    if data.amount > MAX_ADMIN_TOPUP:
        raise HTTPException(
            status_code=400,
            detail=f"Bir martada eng ko'pi {MAX_ADMIN_TOPUP:,} so'm qo'shish mumkin",
        )

    from app.models.admin import AdminAction
    from app.models.enums import AdminActionType

    wallet = await wallet_service.topup(db, uid, data.amount, check_min=False)
    # Iz qoldiramiz: pulga tegadigan yagona admin harakati yozuvsiz edi
    db.add(AdminAction(
        admin_id=admin.id,
        action_type=AdminActionType.wallet_topup,
        target_user_id=user.id,
        reason=f"Hamyonga {data.amount:,} so'm qo'shildi",
    ))
    await db.commit()
    return {
        "message": f"{user.full_name} hamyoniga {data.amount:,} so'm qo'shildi",
        "new_balance": wallet.balance,
        "is_blocked": wallet.is_blocked,
    }


# ─── Statistika ───────────────────────────────────────────────────────────────

@router.get(
    "/stats",
    summary="Dashboard statistikasi (davr bo'yicha)",
)
async def get_stats(
    days: int = Query(30, ge=1, le=180, description="Necha kunlik davr"),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Davr ko'rsatkichlari, sifat foizlari, ish navbati, kunlik qatorlar.

    Hisob-kitob `admin_stats_service` da — bu yerda faqat ulagich.
    """
    return await admin_stats_service.dashboard(db, days=days)


# ─── Nizoli band qilishlar (safar tasdiqi) ──────────────────────────────────────────

@router.get(
    "/disputes",
    summary="Nizoli band qilishlar (yo'lovchi 'bo'lmadi', haydovchi 'bo'ldi')",
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
