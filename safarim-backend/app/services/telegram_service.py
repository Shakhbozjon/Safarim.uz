"""Telegram bot — telefon raqamni tasdiqlash va bildirishnoma yuborish.

Tasdiqlash oqimi:
  1. Saytda foydalanuvchi "Telegram orqali tasdiqlash" ni bosadi
     → `create_link(user)` bir martalik token yaratadi va `t.me/<bot>?start=<token>` qaytaradi.
  2. Foydalanuvchi havolani ochib Start bosadi → bot `/start <token>` oladi,
     tokenni tanib, "Raqamni ulashish" tugmasini ko'rsatadi.
  3. Foydalanuvchi tugmani bosadi → Telegram uning O'Z tasdiqlangan raqamini yuboradi.
  4. Raqam hisobdagi raqamga mos kelsa — `is_phone_verified=True` va `telegram_chat_id`
     saqlanadi. Shundan keyin bildirishnomalar ham shu chatga boradi.

Eskiz SMS'dan farqi: bepul va yuridik shaxs talab qilmaydi. Telegram raqamni
o'zi tekshirgan bo'ladi, shuning uchun kod terish ham shart emas.
"""
from __future__ import annotations

import logging
import re
import secrets
import uuid as uuid_lib
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.telegram import TelegramLinkToken
from app.models.user import User

logger = logging.getLogger(__name__)

API = "https://api.telegram.org/bot{token}/{method}"


def is_configured() -> bool:
    return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_USERNAME)


def normalize_phone(raw: str) -> str:
    """Telegram raqamni "998901112233" yoki "+998901112233" ko'rinishida beradi.

    Saytda raqam har doim "+998XXXXXXXXX" formatida saqlanadi — shunga keltiramiz.
    """
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        return ""
    return "+" + digits


async def _call(method: str, payload: dict) -> dict | None:
    if not settings.TELEGRAM_BOT_TOKEN:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(API.format(token=settings.TELEGRAM_BOT_TOKEN, method=method), json=payload)
            if r.status_code != 200:
                logger.warning("Telegram %s xatosi: %s %s", method, r.status_code, r.text[:200])
                return None
            return r.json()
    except Exception as exc:
        logger.error("Telegram %s ulanish xatosi: %s", method, exc)
        return None


async def send_message(chat_id: str | int, text: str, remove_keyboard: bool = False) -> bool:
    """Foydalanuvchining o'z chatiga xabar yuboradi (bildirishnomalar uchun ham)."""
    payload: dict = {"chat_id": str(chat_id), "text": text, "parse_mode": "HTML"}
    if remove_keyboard:
        payload["reply_markup"] = {"remove_keyboard": True}
    return await _call("sendMessage", payload) is not None


async def _ask_for_contact(chat_id: int, full_name: str) -> None:
    await _call("sendMessage", {
        "chat_id": chat_id,
        "text": (
            f"Assalomu alaykum, {full_name}!\n\n"
            "Raqamingizni tasdiqlash uchun quyidagi tugmani bosing. "
            "Telegram raqamingizni o'zi yuboradi — kod terish shart emas."
        ),
        "reply_markup": {
            "keyboard": [[{"text": "📱 Raqamni ulashish", "request_contact": True}]],
            "resize_keyboard": True,
            "one_time_keyboard": True,
        },
    })


# ─── Havola yaratish ────────────────────────────────────────────────────────
async def create_link(db: AsyncSession, user: User) -> str:
    """Foydalanuvchi uchun bir martalik tasdiqlash havolasini qaytaradi."""
    if not is_configured():
        raise RuntimeError("Telegram bot sozlanmagan")

    # Eski ishlatilmagan tokenlarni bekor qilamiz — bir vaqtda bittasi amal qilsin
    rows = (await db.execute(
        select(TelegramLinkToken).where(
            TelegramLinkToken.user_id == user.id,
            TelegramLinkToken.used_at.is_(None),
        )
    )).scalars().all()
    now = datetime.utcnow()
    for row in rows:
        row.used_at = now

    token = secrets.token_urlsafe(24)[:48]  # Telegram start payload'i 64 belgidan oshmasin
    db.add(TelegramLinkToken(
        id=uuid_lib.uuid4(),
        token=token,
        user_id=user.id,
        expires_at=now + timedelta(minutes=settings.TELEGRAM_LINK_TTL_MINUTES),
    ))
    await db.commit()
    return f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={token}"


# ─── Webhook ishlovchisi ────────────────────────────────────────────────────
async def handle_update(db: AsyncSession, update: dict) -> None:
    """Telegram'dan kelgan yangilanishni qayta ishlaydi.

    Faqat ikki holat qiziq: `/start <token>` va kontakt ulashish.
    Qolganiga qisqa yo'riqnoma qaytaradi.
    """
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not chat_id:
        return

    sender = message.get("from") or {}
    contact = message.get("contact")
    text = (message.get("text") or "").strip()

    # 1) /start <token> — qaysi hisob tasdiqlanayotganini eslab qolamiz
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        payload = parts[1].strip() if len(parts) > 1 else ""
        if not payload:
            await send_message(chat_id, (
                "Bu — <b>UzSafar</b> tasdiqlash boti.\n\n"
                "Raqamni tasdiqlash uchun saytdagi <b>«Telegram orqali tasdiqlash»</b> "
                "tugmasi orqali qayting."
            ))
            return

        link = await _get_valid_token(db, token=payload)
        if link is None:
            await send_message(chat_id, (
                "Havola eskirgan yoki allaqachon ishlatilgan.\n"
                "Saytga qaytib, tasdiqlash tugmasini qaytadan bosing."
            ))
            return

        # Tokenni shu chatga bog'laymiz — kontakt keyingi xabarda kelganda
        # qaysi hisob haqida ekani ma'lum bo'lsin.
        link.chat_id = str(chat_id)
        await db.commit()
        await _ask_for_contact(chat_id, link.user.full_name)
        return

    # 2) Kontakt ulashildi
    if contact:

        # Boshqa odamning kontakt kartasini yuborib bo'lmasin:
        # Telegram faqat o'z raqamida `user_id` ni jo'natuvchi bilan bir xil qiladi.
        if contact.get("user_id") != sender.get("id"):
            await send_message(chat_id, (
                "Faqat <b>o'z</b> raqamingizni ulashishingiz mumkin."
            ), remove_keyboard=True)
            return

        link = await _get_valid_token(db, chat_id=str(chat_id))
        if link is None:
            await send_message(chat_id, (
                "Avval saytdagi tasdiqlash havolasini oching, so'ng raqamni ulashing."
            ), remove_keyboard=True)
            return

        user = link.user
        shared = normalize_phone(contact.get("phone_number", ""))
        if shared != user.phone:
            await send_message(chat_id, (
                f"Bu raqam hisobdagi raqamga mos kelmadi.\n\n"
                f"Hisobda: <code>{user.phone}</code>\n"
                f"Yuborildi: <code>{shared}</code>\n\n"
                "Saytga o'sha raqam bilan kiring yoki profildagi raqamni to'g'rilang."
            ), remove_keyboard=True)
            return

        user.is_phone_verified = True
        user.telegram_chat_id = str(chat_id)
        link.used_at = datetime.utcnow()
        await db.commit()

        await send_message(chat_id, (
            "✅ Raqamingiz tasdiqlandi!\n\n"
            "Endi saytga qaytishingiz mumkin. Yangi buyurtma va safar xabarlari "
            "shu yerga keladi."
        ), remove_keyboard=True)
        return

    await send_message(chat_id, (
        "Raqamni tasdiqlash uchun saytdagi <b>«Telegram orqali tasdiqlash»</b> "
        "tugmasi orqali qayting."
    ))


async def _get_valid_token(
    db: AsyncSession, *, token: str | None = None, chat_id: str | None = None
) -> TelegramLinkToken | None:
    """Amaldagi (ishlatilmagan, muddati o'tmagan) tokenni token yoki chat bo'yicha topadi."""
    from sqlalchemy.orm import selectinload

    query = (
        select(TelegramLinkToken)
        .options(selectinload(TelegramLinkToken.user))
        .where(
            TelegramLinkToken.used_at.is_(None),
            TelegramLinkToken.expires_at > datetime.utcnow(),
        )
        .order_by(TelegramLinkToken.created_at.desc())
    )
    if token is not None:
        query = query.where(TelegramLinkToken.token == token)
    if chat_id is not None:
        query = query.where(TelegramLinkToken.chat_id == chat_id)

    return (await db.execute(query.limit(1))).scalar_one_or_none()
