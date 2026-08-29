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
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import TelegramLinkPurpose
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


async def send_notification(
    chat_id: str | int,
    title: str,
    body: str,
    buttons: list[list[dict]] | None = None,
) -> bool:
    """Ilova ichidagi bildirishnomani Telegramga ham yuboradi.

    `buttons` — inline tugmalar: [[{"text": "Ha", "callback_data": "cfy:<id>"}]].
    Telegram callback_data uchun 64 baytdan oshmasligini talab qiladi.
    """
    payload: dict = {
        "chat_id": str(chat_id),
        "text": f"<b>{_esc(title)}</b>\n\n{_esc(body)}",
        "parse_mode": "HTML",
    }
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    return await _call("sendMessage", payload) is not None


def _esc(s: str) -> str:
    """HTML parse_mode uchun — foydalanuvchi ismidagi < > & xabarni buzmasin."""
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def deliver_notification(notification_id: str, buttons=None) -> dict:
    """Yaratilgan bildirishnomani egasining Telegram chatiga yetkazadi.

    Fon rejimida chaqiriladi (`notification_service`), shuning uchun o'z
    sessiyasini ochadi. Telegram ulanmagan bo'lsa jim to'xtaydi — bildirishnoma
    ilova ichida baribir ko'rinadi.
    """
    import uuid as uuid_lib

    from sqlalchemy.orm import selectinload

    from app.db.session import AsyncSessionLocal
    from app.models.notification import Notification

    async with AsyncSessionLocal() as db:
        notif = (await db.execute(
            select(Notification)
            .options(selectinload(Notification.user))
            .where(Notification.id == uuid_lib.UUID(notification_id))
        )).scalar_one_or_none()

        # Caller tranzaksiyasi orqaga qaytgan bo'lishi mumkin
        if notif is None:
            return {"status": "not_found"}

        chat_id = getattr(notif.user, "telegram_chat_id", None)
        if not chat_id:
            return {"status": "no_telegram"}

        sent = await send_notification(chat_id, notif.title, notif.body, buttons)
        return {"status": "sent" if sent else "failed"}


async def _ask_for_contact(chat_id: int, full_name: str, purpose: TelegramLinkPurpose) -> None:
    if purpose == TelegramLinkPurpose.password_reset:
        text = (
            f"Assalomu alaykum, {full_name}!\n\n"
            "Parolni tiklash uchun raqamingizni ulashing — u hisobdagi raqamga "
            "mos kelsa, tiklash kodini shu yerga yuboraman."
        )
    elif purpose == TelegramLinkPurpose.change_phone:
        text = (
            f"Assalomu alaykum, {full_name}!\n\n"
            "Hisobingizdagi raqam <b>ushbu Telegram raqamiga</b> almashtiriladi. "
            "Davom etish uchun quyidagi tugmani bosing."
        )
    else:
        text = (
            f"Assalomu alaykum, {full_name}!\n\n"
            "Raqamingizni tasdiqlash uchun quyidagi tugmani bosing. "
            "Telegram raqamingizni o'zi yuboradi — kod terish shart emas."
        )
    await _call("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {
            "keyboard": [[{
                "text": "📱 Yangi raqamni ulashish" if purpose == TelegramLinkPurpose.change_phone
                        else "📱 Raqamni ulashish",
                "request_contact": True,
            }]],
            "resize_keyboard": True,
            "one_time_keyboard": True,
        },
    })


# ─── Havola yaratish ────────────────────────────────────────────────────────
async def create_link(
    db: AsyncSession,
    user: User,
    purpose: TelegramLinkPurpose = TelegramLinkPurpose.verify,
) -> str:
    """Bir martalik havola qaytaradi — raqamni tasdiqlash yoki almashtirish uchun."""
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
        purpose=purpose,
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
    # Inline tugma bosildi (safar tasdiqi)
    if update.get("callback_query"):
        await _handle_callback(db, update["callback_query"])
        return

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
        await _ask_for_contact(chat_id, link.user.full_name, link.purpose)
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

        if link.purpose == TelegramLinkPurpose.change_phone:
            await _apply_phone_change(db, link, chat_id, shared)
            return

        if link.purpose == TelegramLinkPurpose.password_reset:
            await _send_reset_code(db, link, chat_id, shared)
            return

        if shared != user.phone:
            await send_message(chat_id, (
                f"Bu raqam hisobdagi raqamga mos kelmadi.\n\n"
                f"Hisobda: <code>{user.phone}</code>\n"
                f"Yuborildi: <code>{shared}</code>\n\n"
                "Saytga o'sha raqam bilan kiring yoki profildagi "
                "<b>«Raqamni o'zgartirish»</b> tugmasi orqali raqamni almashtiring."
            ), remove_keyboard=True)
            return

        user.is_phone_verified = True
        await _bind_chat(db, user, chat_id)
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


async def _bind_chat(db: AsyncSession, user: User, chat_id: int | str) -> None:
    """Chatni foydalanuvchiga biriktiradi — bitta chat faqat bitta hisobga.

    Tugma bosilganda javob bergan odam chat bo'yicha topiladi
    (`_handle_callback`). Ikki hisob bir chatni ulashsa, o'sha so'rov ikki qator
    qaytarib yiqilardi — raqam almashgach eski bog'lanish qolib ketmasin.
    """
    await db.execute(
        update(User)
        .where(User.telegram_chat_id == str(chat_id), User.id != user.id)
        .values(telegram_chat_id=None)
    )
    user.telegram_chat_id = str(chat_id)


async def _send_reset_code(
    db: AsyncSession, link: TelegramLinkToken, chat_id: int, shared: str
) -> None:
    """Parolni tiklash kodini shu chatga yuboradi.

    Bu yerda raqam SOLISHTIRILADI (almashtirishdan farqi shu): odam hisobga
    kirmagan, shuning uchun uning aynan shu hisob egasi ekanini isbotlaydigan
    yagona narsa — Telegram kafolatlagan raqamning hisobdagi raqamga mos
    kelishi. Mos kelmasa hech narsa aytilmaydi va hech narsa o'zgarmaydi.
    """
    from app.models.enums import OtpPurpose
    from app.services import auth_service

    user = link.user

    if shared != user.phone:
        await send_message(chat_id, (
            "Bu raqam tiklanayotgan hisobdagi raqamga mos kelmadi.\n\n"
            "Saytda o'sha hisobning raqamini kiritganingizni tekshiring."
        ), remove_keyboard=True)
        return

    # Chatni bog'laymiz — bundan keyingi kodlar va bildirishnomalar shu yerga keladi
    await _bind_chat(db, user, chat_id)
    link.used_at = datetime.utcnow()
    await db.commit()

    # Yangi kod yaratamiz: chat endi bog'langani uchun `send_otp` uni o'zi
    # shu chatga yetkazadi. Eski kod foydalanuvchiga baribir yetib bormagan.
    await auth_service.send_otp(db, user.phone, OtpPurpose.password_reset)

    await send_message(chat_id, (
        "Yuqoridagi kodni saytdagi <b>«Tasdiqlash kodi»</b> maydoniga kiriting "
        "va yangi parolni o'rnating."
    ), remove_keyboard=True)


async def _apply_phone_change(
    db: AsyncSession, link: TelegramLinkToken, chat_id: int, shared: str
) -> None:
    """Hisobdagi raqamni Telegram tasdiqlagan yangi raqamga almashtiradi.

    Bu yerda raqam solishtirilmaydi — o'rnatiladi. Ikki tomon ham tekshirilgan:
    raqam egaligini Telegram kafolatlaydi (kontakt faqat jo'natuvchining o'ziniki
    bo'lishi mumkin), havolani esa faqat hisobga kirgan odam yarata oladi.
    """
    user = link.user

    if not shared:
        await send_message(chat_id, (
            "Raqamni o'qib bo'lmadi. Saytdan havolani qaytadan oching."
        ), remove_keyboard=True)
        return

    if shared == user.phone:
        # O'sha raqamning o'zi — almashtirishga hojat yo'q, tasdiqlab qo'yamiz
        user.is_phone_verified = True
        await _bind_chat(db, user, chat_id)
        link.used_at = datetime.utcnow()
        await db.commit()
        await send_message(chat_id, (
            "Bu allaqachon hisobingizdagi raqam — tasdiqlandi ✅"
        ), remove_keyboard=True)
        return

    # Raqam boshqa hisobda bo'lsa almashtirib bo'lmaydi: aks holda bir raqam
    # ikki hisobda qolardi va kirish qaysi biriga tegishli ekani noaniq bo'lardi.
    taken = (await db.execute(
        select(User).where(User.phone == shared, User.id != user.id)
    )).scalar_one_or_none()
    if taken is not None:
        await send_message(chat_id, (
            f"<code>{shared}</code> raqami boshqa hisobga biriktirilgan.\n\n"
            "O'sha hisobga shu raqam bilan kiring yoki administrator bilan bog'laning."
        ), remove_keyboard=True)
        return

    old_phone = user.phone
    user.phone = shared
    user.is_phone_verified = True
    await _bind_chat(db, user, chat_id)
    link.used_at = datetime.utcnow()
    await db.commit()

    await send_message(chat_id, (
        "✅ Raqamingiz o'zgartirildi.\n\n"
        f"Eski: <code>{old_phone}</code>\n"
        f"Yangi: <code>{shared}</code>\n\n"
        "Bundan keyin saytga shu raqam bilan kiring."
    ), remove_keyboard=True)


# ─── Tugma bosishlari ───────────────────────────────────────────────────────
CONFIRM_YES_PREFIX = "cfy:"
CONFIRM_NO_PREFIX = "cfn:"


def confirmation_buttons(booking_id) -> list[list[dict]]:
    """"Safaringiz bo'ldimi?" xabari uchun Ha/Yo'q tugmalari."""
    return [[
        {"text": "✅ Ha, bo'ldi", "callback_data": f"{CONFIRM_YES_PREFIX}{booking_id}"},
        {"text": "❌ Yo'q", "callback_data": f"{CONFIRM_NO_PREFIX}{booking_id}"},
    ]]


async def _answer_callback(callback_id: str, text: str = "") -> None:
    """Telegramga javob — busiz tugmada aylanma belgisi qotib qoladi."""
    await _call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})


async def _replace_message(chat_id, message_id, text: str) -> None:
    """Tugmalarni olib tashlab, natijani o'sha xabarning o'zida ko'rsatadi —
    foydalanuvchi ikkinchi marta bosa olmasin."""
    await _call("editMessageText", {
        "chat_id": str(chat_id),
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
    })


async def _handle_callback(db: AsyncSession, cq: dict) -> None:
    data = (cq.get("data") or "").strip()
    cq_id = cq.get("id")
    msg = cq.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    message_id = msg.get("message_id")

    if data.startswith(CONFIRM_YES_PREFIX):
        booking_id, confirmed = data[len(CONFIRM_YES_PREFIX):], True
    elif data.startswith(CONFIRM_NO_PREFIX):
        booking_id, confirmed = data[len(CONFIRM_NO_PREFIX):], False
    else:
        await _answer_callback(cq_id, "Bu tugma endi ishlamaydi")
        return

    # Tugmani bosgan odam — chat egasi. Kim ekanini shu orqali topamiz.
    user = (await db.execute(
        select(User).where(User.telegram_chat_id == str(chat_id))
    )).scalar_one_or_none()
    if user is None:
        await _answer_callback(cq_id, "Hisobingiz topilmadi")
        return

    from app.services import booking_service

    try:
        await booking_service.confirm_booking(db, booking_id, user, confirmed)
    except Exception as exc:  # HTTPException ham shu yerga tushadi
        detail = getattr(exc, "detail", None) or "Amalni bajarib bo'lmadi"
        await _answer_callback(cq_id, str(detail)[:180])
        return

    await _answer_callback(cq_id, "Javobingiz qabul qilindi")
    await _replace_message(
        chat_id, message_id,
        "✅ Javobingiz qabul qilindi: safar <b>bo'ldi</b>." if confirmed
        else "Javobingiz qabul qilindi: safar <b>bo'lmadi</b>.",
    )


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
