import re
from pydantic import BaseModel, field_validator
from app.models.enums import OtpPurpose


class SendOtpRequest(BaseModel):
    phone: str
    purpose: OtpPurpose = OtpPurpose.register

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^\+998\d{9}$", v):
            raise ValueError("Telefon raqam +998XXXXXXXXX formatida bo'lishi kerak")
        return v


class SendOtpResponse(BaseModel):
    message: str
    expires_in: int  # sekundda
    pilot_otp: str | None = None  # faqat PILOT_MODE da to'ldiriladi (SMS'siz sinov)


class RegisterRequest(BaseModel):
    phone: str
    otp_code: str
    full_name: str
    password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^\+998\d{9}$", v):
            raise ValueError("Telefon raqam +998XXXXXXXXX formatida bo'lishi kerak")
        return v

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


class LoginRequest(BaseModel):
    phone: str
    password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^\+998\d{9}$", v):
            raise ValueError("Telefon raqam +998XXXXXXXXX formatida bo'lishi kerak")
        return v


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
