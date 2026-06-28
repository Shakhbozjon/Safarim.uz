from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, field_validator, ValidationError

from app.db.session import get_db
from app.models.user import User
from app.models.enums import LuggageSize
from app.schemas.driver import (
    DriverProfileResponse, UpdatePreferencesRequest,
    DriverStatusResponse, EarningsResponse,
)
from app.services import driver_service, storage_service as stor, wallet_service, image_validation
from app.services.storage_service import storage_service
from app.core.dependencies import get_current_user, get_current_driver
from app.core.config import settings


class TopupRequestBody(BaseModel):
    amount: int
    method: str  # "click" | "payme" | "uzcard" | "cash"

    @field_validator("amount")
    @classmethod
    def amount_min(cls, v: int) -> int:
        if v < 10_000:
            raise ValueError("Minimal miqdor: 10,000 so'm")
        return v


class WithdrawRequest(BaseModel):
    amount: int
    card_number: str

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: int) -> int:
        if v < 10_000:
            raise ValueError("Minimal yechish miqdori: 10,000 so'm")
        return v

    @field_validator("card_number")
    @classmethod
    def card_format(cls, v: str) -> str:
        digits = v.replace(" ", "").replace("-", "")
        if not digits.isdigit() or len(digits) != 16:
            raise ValueError("Karta raqami 16 ta raqamdan iborat bo'lishi kerak")
        return digits

router = APIRouter()


@router.post(
    "/apply",
    response_model=DriverProfileResponse,
    summary="Haydovchi arizasi — hujjat yuklash",
)
async def apply_driver(
    vehicle_make: str = Form(...),
    vehicle_model: str = Form(...),
    vehicle_year: int = Form(...),
    vehicle_color: str = Form(...),
    vehicle_plate: str = Form(...),
    vehicle_seats: int = Form(...),
    license_image: UploadFile = File(..., description="Haydovchilik guvohnomasi (JPEG/PNG, maks 5MB)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.schemas.driver import DriverApplyRequest

    # Avtomobil ma'lumotlarini tekshirish (raqam O'zbekiston formatiga mosligi shu yerda)
    try:
        data = DriverApplyRequest(
            vehicle_make=vehicle_make,
            vehicle_model=vehicle_model,
            vehicle_year=vehicle_year,
            vehicle_color=vehicle_color,
            vehicle_plate=vehicle_plate,
            vehicle_seats=vehicle_seats,
        )
    except ValidationError as e:
        msg = e.errors()[0]["msg"].replace("Value error, ", "")
        raise HTTPException(status_code=400, detail=msg)

    # Guvohnoma rasmini tekshirish — haqiqiy hujjat suratimi (har xil rasm emas)
    await image_validation.validate_license_image(license_image)

    license_key = await storage_service.upload(
        license_image, settings.MINIO_BUCKET_DOCUMENTS, folder="licenses"
    )

    driver = await driver_service.apply_driver(db, current_user, data, license_key)
    return driver


@router.get(
    "/me",
    response_model=DriverProfileResponse,
    summary="O'z haydovchi profilini ko'rish",
)
async def get_my_driver_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await driver_service.get_driver_profile(db, current_user)


@router.get(
    "/me/status",
    response_model=DriverStatusResponse,
    summary="Verifikatsiya holatini ko'rish",
)
async def get_driver_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    driver = await driver_service.get_driver_profile(db, current_user)

    messages = {
        "pending": "Arizangiz ko'rib chiqilmoqda. 1-3 ish kuni ichida javob beriladi.",
        "approved": "Tasdiqlangan. Safar e'lon qilishingiz mumkin.",
        "rejected": f"Rad etildi. Sabab: {driver.rejection_reason}",
    }

    return DriverStatusResponse(
        status=driver.status,
        rejection_reason=driver.rejection_reason,
        message=messages[driver.status.value],
    )


@router.put(
    "/me/preferences",
    response_model=DriverProfileResponse,
    summary="Safar preferences ni yangilash",
)
async def update_preferences(
    data: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    return await driver_service.update_preferences(db, current_user, data)


@router.post(
    "/me/pause",
    response_model=DriverProfileResponse,
    summary="Pauzaga o'tish — yangi bronlar qabul qilinmaydi",
)
async def pause_driver(
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    return await driver_service.toggle_pause(db, current_user, pause=True)


@router.post(
    "/me/resume",
    response_model=DriverProfileResponse,
    summary="Pauzadan qaytish",
)
async def resume_driver(
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    return await driver_service.toggle_pause(db, current_user, pause=False)


@router.get(
    "/me/earnings",
    response_model=list[EarningsResponse],
    summary="Oylik daromad statistikasi (so'nggi 12 oy)",
)
async def get_earnings(
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    commissions = await driver_service.get_monthly_earnings(db, current_user)
    return [
        EarningsResponse(
            month=c.month.strftime("%Y-%m"),
            total_cash_bookings=c.total_cash_bookings,
            total_commission=c.total_commission,
            is_paid=c.is_paid,
        )
        for c in commissions
    ]


@router.post(
    "/me/wallet/topup/pay",
    summary="Click/Payme orqali hamyon to'ldirish — to'lov URL qaytaradi",
)
async def initiate_wallet_topup(
    data: TopupRequestBody,
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    from app.services.payment_service import initiate_wallet_topup as _init_topup
    if data.method not in ("click", "payme"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="To'lov usuli: 'click' yoki 'payme'")
    return await _init_topup(db, current_user.id, data.amount, data.method)


@router.post(
    "/me/wallet/topup-request",
    summary="Hamyon to'ldirish so'rovi — adminga Telegram xabar ketadi",
)
async def request_topup(
    data: TopupRequestBody,
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    from app.services.sms_service import sms_service

    method_labels = {
        "click": "Click",
        "payme": "Payme",
        "uzcard": "Uzcard (karta)",
        "cash": "Naqd pul",
    }
    method_label = method_labels.get(data.method, data.method)

    msg = (
        f"💰 <b>Hamyon to'ldirish so'rovi</b>\n\n"
        f"👤 Haydovchi: <b>{current_user.full_name}</b>\n"
        f"📞 Telefon: <code>{current_user.phone}</code>\n"
        f"💵 Miqdor: <b>{data.amount:,} so'm</b>\n"
        f"💳 To'lov usuli: <b>{method_label}</b>\n\n"
        f"Admin panelida tasdiqlang: /admin/users"
    )
    await sms_service.notify_admin(msg)

    return {
        "message": "So'rov yuborildi",
        "amount": data.amount,
        "method": data.method,
    }


@router.get(
    "/me/wallet",
    summary="Hamyon holati + tranzaksiyalar",
)
async def get_wallet(
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    return await wallet_service.get_wallet_info(db, current_user.id)


@router.post(
    "/me/wallet/topup",
    summary="Hamyonni to'ldirish (to'lov tasdiqlanganidan keyin chaqiriladi)",
)
async def topup_wallet(
    amount: int,
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    wallet = await wallet_service.topup(db, current_user.id, amount)
    await db.commit()
    return {
        "message": f"Hamyon {amount:,} so'mga to'ldirildi",
        "new_balance": wallet.balance,
        "is_blocked": wallet.is_blocked,
    }


@router.post(
    "/me/wallet/withdraw",
    summary="Hamyondan pul yechib olish (karta raqami talab qilinadi)",
)
async def withdraw_wallet(
    data: WithdrawRequest,
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    wallet = await wallet_service.withdraw(db, current_user.id, data.amount)
    await db.commit()
    return {
        "message": f"{data.amount:,} so'm {data.card_number[:4]}****{data.card_number[-4:]} kartasiga yechib olindi",
        "new_balance": wallet.balance,
        "card_number": data.card_number,
    }
