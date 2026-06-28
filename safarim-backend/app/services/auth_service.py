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


async def send_otp(db: AsyncSession, phone: str, purpose: OtpPurpose) -> str:
    # Register uchun: telefon band emasligini tekshirish
    if purpose == OtpPurpose.register:
        result = await db.execute(select(User).where(User.phone == phone))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu telefon raqam allaqachon ro'yxatdan o'tgan",
            )

    # Login uchun: foydalanuvchi mavjudligini tekshirish
    if purpose == OtpPurpose.login:
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

    message = f"Safarim.uz: tasdiqlash kodingiz {code}. {settings.OTP_EXPIRE_MINUTES} daqiqa ichida foydalaning."
    await sms_service.send(phone, message)

    return code


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

    user = User(
        phone=phone,
        full_name=full_name.strip(),
        password_hash=hash_password(password),
        is_phone_verified=True,
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
