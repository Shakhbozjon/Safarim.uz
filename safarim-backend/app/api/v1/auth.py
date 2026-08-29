from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.ratelimit import limit_send_otp, limit_login, limit_register
from app.schemas.auth import (
    SendOtpRequest, SendOtpResponse,
    RegisterRequest, LoginRequest, ResetPasswordRequest, TelegramResetLinkRequest,
    RefreshRequest, TokenResponse,
)
from app.schemas.user import UserResponse
from app.models.enums import TelegramLinkPurpose
from app.services import auth_service, telegram_service
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
    code, channel = await auth_service.send_otp(db, data.phone, data.purpose)
    # Pilot rejimda OTP javobda qaytadi (SMS yo'q) — FAQAT allowlist'dagi tester
    # raqamlariga. Allowlist bo'sh bo'lsa hech kimga qaytarilmaydi: aks holda
    # istalgan odam begona raqamga OTP so'rab, kodni javobdan o'qib olardi.
    allowlist = settings.pilot_otp_allowlist
    show_otp = settings.PILOT_MODE and data.phone in allowlist
    return SendOtpResponse(
        message=(
            "Tasdiqlash kodi Telegramingizga yuborildi"
            if channel == "telegram" else "Tasdiqlash kodi yuborildi"
        ),
        expires_in=settings.OTP_EXPIRE_MINUTES * 60,
        pilot_otp=code if show_otp else None,
        channel=channel,
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi foydalanuvchi ro'yxatdan o'tish",
)
async def register(data: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # OTP tasdiqlash olib tashlandi (SMS/Telegram byudjeti yo'q) — telefon+parol bilan
    # to'g'ridan-to'g'ri ro'yxat. Kelajakda tasdiqlash kerak bo'lsa: verify_otp qaytariladi.
    await limit_register(request)  # bitta IP/qurilmadan massa soxta hisobni cheklaydi
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
    "/telegram-reset-link",
    summary="Telegrami ulanmagan foydalanuvchi uchun parol tiklash havolasi",
)
async def telegram_reset_link(
    data: TelegramResetLinkRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    """Botga havola beradi: foydalanuvchi kontaktini ulashadi, raqam hisobdagiga
    mos kelsa bot chatni bog'laydi va tiklash kodini o'sha chatga yuboradi.

    Havolani olish uchun hisobga kirish shart emas (aynan kira olmagan odam
    uchun) — lekin havolaning o'zi hech narsa bermaydi: kod faqat raqam egasi
    kontaktini ulashgandagina yuboriladi.
    """
    await limit_send_otp(request, data.phone)

    if not telegram_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram orqali tiklash hozircha mavjud emas. Administrator bilan bog'laning.",
        )

    user = await auth_service.get_user_by_phone(db, data.phone)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bu telefon raqam ro'yxatdan o'tmagan",
        )

    url = await telegram_service.create_link(db, user, TelegramLinkPurpose.password_reset)
    return {"url": url}


@router.post(
    "/reset-password",
    response_model=TokenResponse,
    summary="Parolni OTP orqali tiklash (tizimga kirmasdan)",
)
async def reset_password(
    data: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    # Kod 6 xonali — bir IP dan cheksiz urinishga yo'l qo'ymaymiz.
    # (OTP yozuvining o'z urinishlar hisoblagichi ham bor: verify_otp.)
    await limit_login(request)
    user = await auth_service.reset_password(
        db, data.phone, data.otp_code, data.new_password
    )
    # Tiklangach darrov kiritamiz — foydalanuvchi yana parol terib o'tirmasin
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
