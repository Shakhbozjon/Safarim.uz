from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services import telegram_service

router = APIRouter()


@router.post(
    "/webhook",
    summary="Telegram bot webhook (faqat Telegram chaqiradi)",
    include_in_schema=False,
)
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    # Sirsiz webhook ochiq eshik bo'lardi: istalgan odam soxta "kontakt ulashildi"
    # so'rovini yuborib, begona raqamni tasdiqlangan qilib qo'yishi mumkin edi.
    secret = settings.TELEGRAM_WEBHOOK_SECRET
    if not secret or x_telegram_bot_api_secret_token != secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ruxsat yo'q")

    update = await request.json()
    await telegram_service.handle_update(db, update)
    # Telegram 200 dan boshqa javobda yangilanishni qayta-qayta yuboraveradi
    return {"ok": True}


@router.post(
    "/link",
    summary="Raqamni tasdiqlash uchun Telegram havolasini olish",
)
async def create_telegram_link(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.is_phone_verified:
        return {"url": None, "already_verified": True}

    if not telegram_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram tasdiqlash hozircha mavjud emas. Administrator bilan bog'laning.",
        )

    url = await telegram_service.create_link(db, current_user)
    return {"url": url, "already_verified": False}
