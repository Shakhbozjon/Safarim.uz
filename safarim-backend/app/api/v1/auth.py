from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.ratelimit import limit_send_otp, limit_login
from app.schemas.auth import (
    SendOtpRequest, SendOtpResponse,
    RegisterRequest, LoginRequest,
    RefreshRequest, TokenResponse,
)
from app.schemas.user import UserResponse
from app.models.enums import OtpPurpose
from app.services import auth_service
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.core.config import settings
from app.core.dependencies import get_current_user

router = APIRouter()


@router.post(
    "/send-otp",
    response_model=SendOtpResponse,
    summary="Telefonga OTP yuborish",
)
async def send_otp(data: SendOtpRequest, request: Request, db: AsyncSession = Depends(get_db)):
    await limit_send_otp(request, data.phone)
    code = await auth_service.send_otp(db, data.phone, data.purpose)
    # Pilot rejimda OTP javobda qaytadi (SMS yo'q). Allowlist berilgan bo'lsa —
    # faqat shu raqamlarga; boshqalar OTP'ni Telegram/SMS orqali oladi.
    allowlist = settings.pilot_otp_allowlist
    show_otp = settings.PILOT_MODE and (not allowlist or data.phone in allowlist)
    return SendOtpResponse(
        message="Tasdiqlash kodi yuborildi",
        expires_in=settings.OTP_EXPIRE_MINUTES * 60,
        pilot_otp=code if show_otp else None,
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi foydalanuvchi ro'yxatdan o'tish",
)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.verify_otp(db, data.phone, data.otp_code, OtpPurpose.register)
    user = await auth_service.register_user(db, data.phone, data.full_name, data.password)
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Tizimga kirish",
)
async def login(data: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    await limit_login(request)
    user = await auth_service.login_user(db, data.phone, data.password)
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Access tokenni yangilash",
)
async def refresh_token(data: RefreshRequest):
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token yaroqsiz yoki muddati o'tgan",
        )
    user_id = payload["sub"]
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.post(
    "/logout",
    summary="Tizimdan chiqish",
)
async def logout(current_user=Depends(get_current_user)):
    # JWT stateless — clientda tokenni o'chirish yetarli
    # Kelajakda Redis blacklist qo'shish mumkin
    return {"message": "Muvaffaqiyatli chiqildi"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="O'z profilini ko'rish",
)
async def get_me(current_user=Depends(get_current_user)):
    return current_user
