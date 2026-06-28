from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, field_validator

from app.db.session import get_db
from app.models.user import User
from app.models.enums import TalkLevel, OtpPurpose
from app.schemas.user import UserResponse, UserPublicResponse
from app.core.dependencies import get_current_user
from app.core.security import hash_password
from app.services.storage_service import storage_service
from app.services import auth_service
from app.core.config import settings

router = APIRouter()


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    email: str | None = None
    talk_level: TalkLevel | None = None


class ChangePasswordRequest(BaseModel):
    otp_code: str
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
    summary="Parolni OTP orqali o'zgartirish",
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.verify_otp(db, current_user.phone, data.otp_code, OtpPurpose.password_reset)
    current_user.password_hash = hash_password(data.new_password)
    await db.commit()
    return {"message": "Parol muvaffaqiyatli o'zgartirildi"}


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
