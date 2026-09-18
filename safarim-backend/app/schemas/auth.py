import re
from pydantic import BaseModel, field_validator
from app.models.enums import OtpPurpose

PHONE_FORMAT_ERROR = "Telefon raqam +998XXXXXXXXX formatida bo'lishi kerak"


def normalize_phone(v: str) -> str:
    """Raqamni +998XXXXXXXXX ga keltiradi, aks holda ValueError.

    Mijoz bo'sh joy, tire yoki qavs bilan yuborishi mumkin ("+998 99 123 45 67"),
    ba'zilari "998..." yoki "0"/"8" prefiksi bilan yozadi. Formatni talab qilib
    rad etishdan ko'ra tozalab qabul qilgan ma'qul — foydalanuvchi uchun bu
    farqlar ko'rinmaydi.
    """
    digits = re.sub(r"\D", "", v or "")

    if len(digits) > 9:
        if digits.startswith("998"):
            digits = digits[3:]
        elif digits[0] in "08":
            digits = digits[1:]

    if len(digits) != 9:
        raise ValueError(PHONE_FORMAT_ERROR)
    return f"+998{digits}"


class SendOtpRequest(BaseModel):
    phone: str
    purpose: OtpPurpose = OtpPurpose.register

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone(v)


class SendOtpResponse(BaseModel):
    message: str
    expires_in: int  # sekundda
    pilot_otp: str | None = None  # faqat PILOT_MODE da to'ldiriladi (SMS'siz sinov)
    # "telegram" — kod foydalanuvchining o'z chatiga bordi; "sms" — bormadi
    # (Eskiz sozlanmagan bo'lsa admin chatiga tushadi). Frontend shunga qarab
    # to'g'ri yo'riqnoma ko'rsatadi.
    channel: str = "sms"


class RegisterRequest(BaseModel):
    phone: str
    otp_code: str | None = None  # OTP hozir ishlatilmaydi (ixtiyoriy — kelajakda qaytariladi)
    full_name: str
    password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone(v)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Ism familiya kamida 3 ta harf bo'lishi kerak")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Parol kamida 6 ta belgi bo'lishi kerak")
        return v


class TelegramResetLinkRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone(v)


class ResetPasswordRequest(BaseModel):
    """Parolni tiklash — tizimga kirmasdan, OTP bilan."""
    phone: str
    otp_code: str
    new_password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone(v)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Parol kamida 6 ta belgi bo'lishi kerak")
        return v


class LoginRequest(BaseModel):
    phone: str
    password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone(v)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
