"""Foydalanuvchi xabari — to'g'ridan-to'g'ri adminning Telegramiga.

Saytda ilgari qo'lda yozilgan telefon va email turardi: ularga hech kim
javob bermasdi. Alohida "murojaatlar qutisi" ham qilinmadi — pilotda uni
kuzatib turadigan odam yo'q. Xabar admin allaqachon o'qiydigan joyga,
Telegramga tushadi.
"""
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, field_validator

from app.core.config import settings
from app.core.ratelimit import limit_support
from app.services import telegram_service

router = APIRouter()


class SupportRequest(BaseModel):
    message: str
    # Admin javob bera olishi uchun: telefon yoki Telegram username
    contact: str
    name: str | None = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Xabarni to'liqroq yozing (kamida 10 ta belgi)")
        if len(v) > 2000:
            raise ValueError("Xabar juda uzun (2000 belgidan ko'p)")
        return v

    @field_validator("contact")
    @classmethod
    def validate_contact(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Javob berishimiz uchun telefon yoki Telegram username yozing")
        if len(v) > 100:
            raise ValueError("Aloqa ma'lumoti juda uzun")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v[:100] or None


@router.post(
    "/",
    summary="Saytdan adminga xabar yuborish",
)
async def send_support_message(data: SupportRequest, request: Request):
    await limit_support(request)

    if not settings.TELEGRAM_ADMIN_CHAT_ID or not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hozircha xabar yuborib bo'lmaydi. Birozdan keyin urinib ko'ring.",
        )

    kimdan = data.name or "ism yozilmagan"
    text = (
        "📩 Saytdan xabar\n\n"
        f"Kimdan: {kimdan}\n"
        f"Aloqa: {data.contact}\n\n"
        f"{data.message}"
    )
    sent = await telegram_service.send_message(settings.TELEGRAM_ADMIN_CHAT_ID, text)
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Xabar yuborilmadi. Birozdan keyin urinib ko'ring.",
        )

    return {"message": "Xabaringiz yuborildi — tez orada javob beramiz"}
