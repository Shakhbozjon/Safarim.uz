import random
import string
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User
from app.models.otp import OtpCode
from app.models.enums import OtpPurpose
from app.core.security import hash_password, verify_password
from app.core.config import settings
from app.services.sms_service import sms_service


def _generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


async def send_otp(db: AsyncSession, phone: str, purpose: OtpPurpose) -> tuple[str, str]:
    """OTP yaratadi va yetkazadi. `(kod, kanal)` qaytaradi.

    Kanal: "telegram" — foydalanuvchining o'z chatiga bordi; "sms" — Eskiz
    yoki admin chatiga tushdi (ya'ni foydalanuvchi kodni ko'rmaydi).
    """
    # Register uchun: telefon band emasligini tekshirish
    if purpose == OtpPurpose.register:
        result = await db.execute(select(User).where(User.phone == phone))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu telefon raqam allaqachon ro'yxatdan o'tgan",
            )

    # Login va parol tiklash uchun: foydalanuvchi mavjudligini tekshirish
    if purpose in (OtpPurpose.login, OtpPurpose.password_reset):
        result = await db.execute(select(User).where(User.phone == phone))
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bu telefon raqam ro'yxatdan o'tmagan",
            )

    # Avvalgi ishlatilmagan OTPlarni bekor qilish
    result = await db.execute(
        select(OtpCode).where(
            OtpCode.phone == phone,
            OtpCode.purpose == purpose,
            OtpCode.is_used == False,
        )
    )
    for old_otp in result.scalars().all():
        old_otp.is_used = True

    code = _generate_otp()
    otp = OtpCode(
        phone=phone,
        code=code,
        purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )
    db.add(otp)
    await db.commit()

    message = f"UzSafar: tasdiqlash kodingiz {code}. {settings.OTP_EXPIRE_MINUTES} daqiqa ichida foydalaning."
    channel = await _deliver_otp(db, phone, message)

    return code, channel


async def _deliver_otp(db: AsyncSession, phone: str, message: str) -> str:
    """Kodni imkon qadar foydalanuvchining O'Z Telegramiga yetkazadi.

    Eskiz SMS sozlanmagan (yuridik shaxs talab qiladi), `sms_service` esa bunday
    holatda kodni ADMIN chatiga yuboradi — ya'ni foydalanuvchi uni ko'rmaydi va
    parolini o'zi tiklay olmaydi. Raqamini Telegram orqali tasdiqlagan
    foydalanuvchining chati bizda bor, shuning uchun avval o'shanga uriniladi.
    """
    from app.services import telegram_service

    user = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
    chat_id = getattr(user, "telegram_chat_id", None) if user else None

    if chat_id and await telegram_service.send_message(chat_id, message):
        return "telegram"

    await sms_service.send(phone, message)
    return "sms"


async def get_user_by_phone(db: AsyncSession, phone: str) -> User | None:
    return (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()


async def reset_password(db: AsyncSession, phone: str, code: str, new_password: str) -> User:
    """Parolni OTP orqali tiklaydi (tizimga kirmasdan).

    Kod `send_otp(..., password_reset)` orqali foydalanuvchining Telegramiga
    yuborilgan bo'ladi; `verify_otp` urinishlar sonini va muddatni tekshiradi.
    """
    user = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bu telefon raqam ro'yxatdan o'tmagan",
        )

    await verify_otp(db, phone, code, OtpPurpose.password_reset)

    user.password_hash = hash_password(new_password)
    await db.commit()
    return user


async def verify_otp(db: AsyncSession, phone: str, code: str, purpose: OtpPurpose) -> None:
    result = await db.execute(
        select(OtpCode)
        .where(
            OtpCode.phone == phone,
            OtpCode.purpose == purpose,
            OtpCode.is_used == False,
            OtpCode.expires_at > datetime.utcnow(),
        )
        .order_by(OtpCode.created_at.desc())
    )
    otp = result.scalar_one_or_none()

    if not otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP topilmadi yoki muddati o'tgan. Qaytadan so'rang",
        )

    otp.attempts += 1

    if otp.attempts > settings.OTP_MAX_ATTEMPTS:
        otp.is_used = True
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ko'p marta noto'g'ri kiritildi. Yangi kod so'rang",
        )

    if otp.code != code:
        await db.commit()
        remaining = settings.OTP_MAX_ATTEMPTS - otp.attempts
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Noto'g'ri kod. {remaining} ta urinish qoldi",
        )

    otp.is_used = True
    await db.commit()


async def register_user(db: AsyncSession, phone: str, full_name: str, password: str) -> User:
    # Ikki marta tekshirish (race condition uchun)
    result = await db.execute(select(User).where(User.phone == phone))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu telefon raqam allaqachon ro'yxatdan o'tgan",
        )

    # is_phone_verified qo'yilmaydi (default False): ro'yxatda raqam tekshirilmaydi.
    # Tasdiqlash birinchi haqiqiy harakatdan oldin — band qilish yoki safar e'lon
    # qilishda — Telegram orqali so'raladi. Avval bu yerda True qilingan edi,
    # natijada profilda tekshirilmagan raqamga "Telefon tasdiqlangan" deb yozilardi.
    user = User(
        phone=phone,
        full_name=full_name.strip(),
        password_hash=hash_password(password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def login_user(db: AsyncSession, phone: str, password: str) -> User:
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telefon raqam yoki parol noto'g'ri",
        )

    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hisobingiz bloklangan. Sabab: " + (user.block_reason or "ko'rsatilmagan"),
        )

    user.last_login_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_id(db: AsyncSession, user_id: str) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi")
    return user
