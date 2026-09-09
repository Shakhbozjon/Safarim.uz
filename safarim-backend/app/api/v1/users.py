import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, field_validator

from app.db.session import get_db
from app.models.user import User
from app.models.enums import TalkLevel, Gender
from app.schemas.user import UserResponse, UserPublicResponse
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.services.storage_service import storage_service
from app.core.config import settings

router = APIRouter()


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    email: str | None = None
    talk_level: TalkLevel | None = None
    gender: Gender | None = None


class ChangePasswordRequest(BaseModel):
    """Tizimga kirgan foydalanuvchi parolni joriy parol bilan almashtiradi.

    Bu yerda OTP ishlatilmaydi: odam allaqachon kirgan, shuning uchun uni
    tasdiqlashning eng ishonchli va hech qanday yetkazish kanaliga bog'liq
    bo'lmagan usuli — joriy parolni so'rash. OTP faqat parolni UNUTGAN,
    ya'ni kira olmagan holat uchun qoladi (`/auth/reset-password`).
    """
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Parol kamida 6 ta belgidan iborat bo'lishi kerak")
        return v


@router.get(
    "/me",
    response_model=UserResponse,
    summary="O'z profilini ko'rish",
)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Profilni yangilash",
)
async def update_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.full_name is not None:
        current_user.full_name = data.full_name.strip()
    if data.email is not None:
        # Email band emasligini tekshirish
        result = await db.execute(
            select(User).where(User.email == data.email, User.id != current_user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Bu email allaqachon ishlatilgan")
        current_user.email = data.email
        current_user.is_email_verified = False
    if data.talk_level is not None:
        current_user.talk_level = data.talk_level
    if data.gender is not None:
        current_user.gender = data.gender

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post(
    "/me/photo",
    response_model=UserResponse,
    summary="Profil rasmini yuklash",
)
async def upload_profile_photo(
    photo: UploadFile = File(..., description="Profil rasmi (JPEG/PNG, maks 5MB)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    key = await storage_service.upload(photo, settings.MINIO_BUCKET_PHOTOS, folder="avatars")
    current_user.profile_photo = key
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post(
    "/me/change-password",
    summary="Parolni o'zgartirish (joriy parol bilan)",
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Joriy parol noto'g'ri")

    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=400, detail="Yangi parol eskisidan farq qilishi kerak"
        )

    current_user.password_hash = hash_password(data.new_password)
    # Parol o'zgardi — barcha eski tokenlar yaroqsiz bo'ladi (o'g'irlangan
    # sessiya ham). Shu qurilmadagi odam esa qaytadan kirmasin: unga darrov
    # yangi token beramiz.
    current_user.token_version += 1
    await db.commit()
    await db.refresh(current_user)
    return {
        "message": "Parol muvaffaqiyatli o'zgartirildi",
        "access_token": create_access_token(str(current_user.id), current_user.token_version),
        "refresh_token": create_refresh_token(str(current_user.id), current_user.token_version),
    }


class DeleteAccountRequest(BaseModel):
    """Hisobni o'chirish — joriy parol bilan tasdiqlanadi."""
    password: str


@router.delete(
    "/me",
    summary="Hisobni o'chirish",
)
async def delete_my_account(
    data: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Hisobni o'chiradi (anonimlashtirish yo'li bilan).

    Yozuvni butunlay o'chirib bo'lmaydi: safarlar, band qilishlar va baholar
    unga bog'langan — o'chirilsa boshqa odamlarning safar tarixi ham buziladi.
    Shuning uchun shaxsiy ma'lumot (ism, telefon, email, rasm, Telegram)
    tozalanadi va hisobga kirish yopiladi.
    """
    if not verify_password(data.password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Parol noto'g'ri")

    if current_user.is_admin:
        raise HTTPException(
            status_code=400, detail="Admin hisobini bu yerdan o'chirib bo'lmaydi"
        )

    # Ochiq ishlar borligini tekshiramiz — kimdir yo'lda qolib ketmasin
    from app.models.booking import Booking
    from app.models.driver import DriverProfile
    from app.models.trip import Trip
    from app.models.enums import BookingStatus, TripStatus

    active_booking = (await db.execute(
        select(Booking).where(
            Booking.passenger_id == current_user.id,
            Booking.status.in_([BookingStatus.pending, BookingStatus.confirmed]),
        ).limit(1)
    )).scalar_one_or_none()
    if active_booking:
        raise HTTPException(
            status_code=400,
            detail="Avval faol band qilishlaringizni bekor qiling yoki yakunlang",
        )

    active_trip = (await db.execute(
        select(Trip).where(
            Trip.driver_id == current_user.id,
            Trip.status.in_([TripStatus.active, TripStatus.full, TripStatus.started]),
        ).limit(1)
    )).scalar_one_or_none()
    if active_trip:
        raise HTTPException(
            status_code=400,
            detail="Avval e'lon qilgan safarlaringizni yakunlang yoki bekor qiling",
        )

    # Hamyonda qarz bo'lsa o'chirib bo'lmaydi: aks holda komissiya qaytarilgan
    # kunlarda "qarzni yig'ib, hisobni o'chirib, qayta ro'yxatdan o'tish" degan
    # yo'l ochilardi.
    from app.models.wallet import DriverWallet

    wallet = (await db.execute(
        select(DriverWallet).where(DriverWallet.driver_id == current_user.id)
    )).scalar_one_or_none()
    if wallet and wallet.balance < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Hamyoningizda {abs(wallet.balance):,} so'm qarz bor. Avval uni yoping",
        )

    # Haydovchi profili butunlay o'chiriladi. Ikki sabab:
    #  1. Avtomobil raqami unikal — profil qolsa, o'sha odam qaytadan
    #     ro'yxatdan o'tib O'Z MASHINASI bilan haydovchi bo'la olmasdi
    #     ("bu raqam allaqachon ro'yxatdan o'tgan" degan boshi berk ko'cha);
    #  2. Guvohnoma surati — shaxsiy hujjat, "hisobni o'chirdim" degan odamda
    #     u saqlanib qolmasligi kerak.
    driver_profile = (await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == current_user.id)
    )).scalar_one_or_none()
    if driver_profile:
        if driver_profile.license_image:
            storage_service.delete_file(
                driver_profile.license_image, settings.MINIO_BUCKET_DOCUMENTS
            )
        await db.delete(driver_profile)
        current_user.is_driver = False

    # Anonimlashtirish. Telefon unikal bo'lgani uchun o'rniga qaytarib
    # bo'lmaydigan qiymat qo'yiladi — shu raqam bilan qaytadan ro'yxatdan
    # o'tish mumkin bo'lsin.
    # phone ustuni 13 belgi — shunga sig'adigan belgi qo'yamiz
    current_user.phone = f"del_{uuid_lib.uuid4().hex[:9]}"
    current_user.full_name = "O'chirilgan foydalanuvchi"
    current_user.email = None
    current_user.profile_photo = None
    current_user.telegram_chat_id = None
    current_user.is_phone_verified = False
    current_user.is_active = False
    current_user.is_blocked = True
    current_user.block_reason = "Foydalanuvchi hisobni o'chirdi"
    current_user.password_hash = hash_password(uuid_lib.uuid4().hex)
    current_user.token_version += 1  # barcha qurilmalardagi sessiyalar uziladi
    await db.commit()
    return {"message": "Hisobingiz o'chirildi"}


@router.get(
    "/{user_id}",
    response_model=UserPublicResponse,
    summary="Boshqa foydalanuvchi profilini ko'rish",
)
async def get_user_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    import uuid
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Noto'g'ri ID format")

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    return user
