"""Telegram bot — yo'lovchi va haydovchi shu yerning o'zida ro'yxatdan o'tadi.

**Nega kerak:** saytdagi forma (parol o'ylab topish, mashina ma'lumotlari)
ko'p odamni to'xtatardi. Botda raqamni Telegram o'zi tasdiqlaydi — SMS ham,
parol ham kerak emas:

    yo'lovchi:  raqam → ism → tayyor
    haydovchi:  raqam → ism → marka → model → rang → davlat raqami → o'rinlar

**Holat bazada** (`TelegramSignup`): har xabar boshqa gunicorn workeriga
tushishi mumkin. Ro'yxatdan o'tish tugagach yozuv o'chiriladi.

**Biznes qoidalari takrorlanmaydi.** Haydovchi profili `driver_service.apply_driver`
orqali yaratiladi — davlat raqami bandligi, avtomatik tasdiqlash, hamyon,
bildirishnoma o'sha yerda, saytdagi bilan bir xil.

**Parol yo'q.** Hisob tasodifiy (hech kim bilmaydigan) parol bilan ochiladi.
Saytga botdagi «Saytga kirish» tugmasi orqali kiriladi (bir martalik havola),
parol kerak bo'lsa — «Parolni tiklash» Telegram orqali ishlaydi.
"""
from __future__ import annotations

import logging
import re
import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.core.validators import validate_uz_plate
from app.models.driver import DriverProfile
from app.models.enums import DriverStatus
from app.models.telegram import TelegramLoginToken, TelegramSignup
from app.models.user import User
from app.services import telegram_service as tg

logger = logging.getLogger(__name__)

RG = "rg:"

# Deep-link: t.me/<bot>?start=haydovchi — guruhdagi taklifdan to'g'ri haydovchi oqimiga
START_DRIVER = "haydovchi"
START_PASSENGER = "royxat"

LOGIN_TTL_MINUTES = 5

# Eng ko'p uchraydigan markalar — tugma bilan. Qolgani «Boshqa» orqali yoziladi.
MAKES = ("Chevrolet", "Kia", "Hyundai", "Toyota", "BYD", "Daewoo")
# Chevrolet modellari (O'zbekistonda eng ko'p) — tugma bilan
CHEVROLET_MODELS = ("Cobalt", "Gentra", "Nexia", "Lacetti", "Spark", "Malibu", "Tracker", "Onix")
COLORS = ("Oq", "Qora", "Kumush", "Kulrang", "Ko'k", "Qizil")
SEATS = (3, 4, 5, 6, 7)

_PHONE_RE = re.compile(r"^\+998\d{9}$")
_MAX_TEXT = 40


# ─── Yordamchilar ────────────────────────────────────────────────────────────

async def _send(chat_id, text: str, markup: dict | None = None) -> None:
    payload: dict = {"chat_id": str(chat_id), "text": text, "parse_mode": "HTML"}
    if markup is not None:
        payload["reply_markup"] = markup
    await tg._call("sendMessage", payload)


def _rows(buttons: list[dict], per_row: int) -> list[list[dict]]:
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


async def _draft(db: AsyncSession, chat_id) -> TelegramSignup | None:
    return await db.get(TelegramSignup, str(chat_id))


async def _set_step(db: AsyncSession, draft: TelegramSignup, step: str, **data) -> None:
    draft.step = step
    if data:
        # JSONB o'zgarishini SQLAlchemy sezishi uchun yangi dict beriladi
        draft.data = {**(draft.data or {}), **data}
    await db.commit()


async def _drop_draft(db: AsyncSession, chat_id) -> None:
    draft = await _draft(db, chat_id)
    if draft is not None:
        await db.delete(draft)
        await db.commit()


async def _user_for_chat(db: AsyncSession, chat_id) -> User | None:
    return (await db.execute(
        select(User).where(User.telegram_chat_id == str(chat_id))
    )).scalar_one_or_none()


def _clean(text: str) -> str:
    return " ".join((text or "").split())[:_MAX_TEXT]


# ─── Kirish nuqtalari ────────────────────────────────────────────────────────

async def start_screen(db: AsyncSession, chat_id) -> None:
    """`/start` (havolasiz) — ro'yxatdan o'tmagan yoki yo'lovchi uchun.

    Tasdiqlangan haydovchiga bu chaqirilmaydi: unga ish menyusi chiqadi.
    """
    user = await _user_for_chat(db, chat_id)
    if user is not None:
        await passenger_menu(chat_id, user.full_name)
        return

    await _send(chat_id, (
        "Assalomu alaykum! Bu — <b>UzSafar</b>, viloyatlararo safar xizmati.\n\n"
        "Ro'yxatdan o'tish shu yerning o'zida, bir daqiqa ichida: "
        "parol ham, SMS kod ham kerak emas.\n\n"
        "Kim sifatida ro'yxatdan o'tasiz?"
    ), {"inline_keyboard": [
        [{"text": "🧳 Yo'lovchi sifatida", "callback_data": f"{RG}p"}],
        [{"text": "🚗 Haydovchi sifatida", "callback_data": f"{RG}d"}],
    ]})


async def passenger_menu(chat_id, full_name: str | None = None) -> None:
    hello = f"Assalomu alaykum, {tg._esc(full_name)}!\n\n" if full_name else ""
    site = settings.PUBLIC_SITE_URL.rstrip("/")
    await _send(chat_id, (
        f"{hello}Safarni saytda qidirib, joy band qilasiz. Bron tasdig'i va "
        "haydovchi raqami shu yerga keladi."
    ), {"inline_keyboard": [
        [{"text": "🌐 Saytga kirish", "callback_data": f"{RG}login"}],
        [{"text": "🔍 Safar qidirish", "url": f"{site}/trips"}],
        [{"text": "🚗 Haydovchi bo'lish", "callback_data": f"{RG}d"}],
    ]})


async def begin(db: AsyncSession, chat_id, role: str, tg_name: str = "") -> None:
    """Ro'yxatdan o'tishni boshlaydi (`role` — "passenger" | "driver")."""
    user = await _user_for_chat(db, chat_id)

    if user is not None:
        # Chat allaqachon hisobga ulangan — raqam qayta so'ralmaydi
        if role == "passenger":
            await passenger_menu(chat_id, user.full_name)
            return
        status = await db.scalar(
            select(DriverProfile.status).where(DriverProfile.user_id == user.id)
        )
        if status == DriverStatus.approved:
            from app.services import telegram_driver_bot as dbot
            await dbot.show_menu(db, user, chat_id, "Siz allaqachon haydovchisiz.")
            return
        if status == DriverStatus.pending:
            await _send(chat_id, "Haydovchilik arizangiz ko'rib chiqilmoqda — natija shu yerga keladi.")
            return
        await _drop_draft(db, chat_id)
        db.add(TelegramSignup(chat_id=str(chat_id), role="driver", step="make",
                              data={"user_id": str(user.id)}))
        await db.commit()
        await _ask_make(chat_id)
        return

    await _drop_draft(db, chat_id)
    db.add(TelegramSignup(chat_id=str(chat_id), role=role, step="contact",
                          data={"tg_name": _clean(tg_name)}))
    await db.commit()
    await _ask_contact(chat_id)


async def _ask_contact(chat_id) -> None:
    await _send(chat_id, (
        "📱 Pastdagi <b>«Raqamni ulashish»</b> tugmasini bosing.\n\n"
        "Raqamingizni Telegram o'zi yuboradi va tasdiqlaydi — kod terish shart emas."
    ), {
        "keyboard": [[{"text": "📱 Raqamni ulashish", "request_contact": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    })


# ─── Kontakt ─────────────────────────────────────────────────────────────────

async def handle_contact(db: AsyncSession, chat_id, phone_raw: str) -> bool:
    """Ro'yxatdan o'tish jarayonida ulashilgan raqam. Jarayon bo'lmasa — False.

    Kontakt jo'natuvchining O'ZINIKI ekani chaqiruvchida tekshiriladi.
    """
    draft = await _draft(db, chat_id)
    if draft is None or draft.step != "contact":
        return False

    phone = tg.normalize_phone(phone_raw)
    if not _PHONE_RE.match(phone):
        await _send(chat_id, (
            "Hozircha faqat O'zbekiston raqami (+998) bilan ro'yxatdan o'tish mumkin."
        ), {"remove_keyboard": True})
        await _drop_draft(db, chat_id)
        return True

    existing = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
    if existing is not None:
        if existing.is_blocked or not existing.is_active:
            await _send(chat_id, "Bu hisob bloklangan. Administrator bilan bog'laning.",
                        {"remove_keyboard": True})
            await _drop_draft(db, chat_id)
            return True
        # Raqam saytda allaqachon ro'yxatda — yangi hisob ochilmaydi, shu hisob ulanadi
        existing.is_phone_verified = True
        await tg._bind_chat(db, existing, chat_id)
        await db.commit()
        await _send(chat_id, (
            f"✅ Hisobingiz topildi va Telegram ulandi, {tg._esc(existing.full_name)}."
        ), {"remove_keyboard": True})
        role = draft.role
        await _drop_draft(db, chat_id)
        await begin(db, chat_id, role)
        return True

    await _set_step(db, draft, "name", phone=phone)
    await _send(chat_id, "✅ Raqam qabul qilindi.", {"remove_keyboard": True})
    await _ask_name(chat_id, (draft.data or {}).get("tg_name") or "")
    return True


async def _ask_name(chat_id, suggestion: str) -> None:
    markup = None
    if suggestion:
        markup = {"inline_keyboard": [[
            {"text": f"✅ {suggestion}", "callback_data": f"{RG}nm"},
        ]]}
        text = (
            "Ismingiz qanday? Saytda va haydovchiga shu ism ko'rinadi.\n\n"
            "Telegramdagi ismingiz to'g'ri bo'lsa tugmani bosing, "
            "aks holda ism va familiyangizni yozib yuboring."
        )
    else:
        text = "Ism va familiyangizni yozib yuboring.\n\nMasalan: Akmal Karimov"
    await _send(chat_id, text, markup)


# ─── Matnli javoblar ─────────────────────────────────────────────────────────

async def handle_text(db: AsyncSession, chat_id, text: str) -> bool:
    """Ro'yxatdan o'tishdagi yozma javob. Jarayon bo'lmasa — False."""
    draft = await _draft(db, chat_id)
    if draft is None:
        return False

    text = _clean(text)
    step = draft.step

    if step == "contact":
        await _ask_contact(chat_id)
    elif step == "name":
        await _accept_name(db, chat_id, draft, text)
    elif step == "make":
        await _accept_make(db, chat_id, draft, text)
    elif step == "model":
        await _accept_model(db, chat_id, draft, text)
    elif step == "color":
        await _accept_color(db, chat_id, draft, text)
    elif step == "plate":
        await _accept_plate(db, chat_id, draft, text)
    elif step == "seats":
        await _send(chat_id, "O'rinlar sonini tugma orqali tanlang.")
    else:
        return False
    return True


def _valid_name(name: str) -> bool:
    return 2 <= len(name) <= _MAX_TEXT and not any(ch in name for ch in "<>@/\\")


async def _accept_name(db: AsyncSession, chat_id, draft: TelegramSignup, name: str) -> None:
    if not _valid_name(name):
        await _send(chat_id, "Ismni to'g'ri yozing (2 dan 40 gacha harf). Masalan: Akmal Karimov")
        return

    user = await _create_user(db, chat_id, draft.data["phone"], name)
    if draft.role == "passenger":
        await _drop_draft(db, chat_id)
        await _send(chat_id, f"🎉 Ro'yxatdan o'tdingiz, {tg._esc(name)}!")
        await passenger_menu(chat_id)
        return

    await _set_step(db, draft, "make", user_id=str(user.id))
    await _ask_make(chat_id)


async def _create_user(db: AsyncSession, chat_id, phone: str, name: str) -> User:
    """Yangi hisob. Raqam Telegram tomonidan tasdiqlangan — shuning uchun darrov
    `is_phone_verified`. Parol tasodifiy: hech kim bilmaydi, kerak bo'lsa tiklanadi."""
    user = User(
        id=uuid.uuid4(),
        phone=phone,
        full_name=name,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        is_phone_verified=True,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        # Shu orada sayt orqali shu raqam bilan ro'yxatdan o'tilgan bo'lsa
        await db.rollback()
        user = (await db.execute(select(User).where(User.phone == phone))).scalar_one()
        user.is_phone_verified = True
    await tg._bind_chat(db, user, chat_id)
    await db.commit()
    await db.refresh(user)
    return user


# ─── Haydovchi: mashina ──────────────────────────────────────────────────────

async def _ask_make(chat_id) -> None:
    buttons = [{"text": m, "callback_data": f"{RG}mk:{i}"} for i, m in enumerate(MAKES)]
    buttons.append({"text": "Boshqa", "callback_data": f"{RG}mk:o"})
    await _send(chat_id, (
        "🚗 Endi mashinangiz haqida — yo'lovchi uni shu ma'lumotlar bo'yicha taniydi.\n\n"
        "Markasi qanday?"
    ), {"inline_keyboard": _rows(buttons, 3)})


async def _accept_make(db, chat_id, draft, make: str) -> None:
    if len(make) < 2:
        await _send(chat_id, "Markani yozing. Masalan: Chevrolet")
        return
    await _set_step(db, draft, "model", make=make)
    await _ask_model(chat_id, make)


async def _ask_model(chat_id, make: str) -> None:
    if make == "Chevrolet":
        buttons = [{"text": m, "callback_data": f"{RG}md:{i}"} for i, m in enumerate(CHEVROLET_MODELS)]
        buttons.append({"text": "Boshqa", "callback_data": f"{RG}md:o"})
        await _send(chat_id, "Modeli qanday?", {"inline_keyboard": _rows(buttons, 4)})
    else:
        await _send(chat_id, f"{tg._esc(make)} — modelini yozing. Masalan: K5")


async def _accept_model(db, chat_id, draft, model: str) -> None:
    if len(model) < 1:
        await _send(chat_id, "Modelni yozing.")
        return
    await _set_step(db, draft, "color", model=model)
    await _ask_color(chat_id)


async def _ask_color(chat_id) -> None:
    buttons = [{"text": c, "callback_data": f"{RG}cl:{i}"} for i, c in enumerate(COLORS)]
    buttons.append({"text": "Boshqa", "callback_data": f"{RG}cl:o"})
    await _send(chat_id, "Rangi qanday?", {"inline_keyboard": _rows(buttons, 4)})


async def _accept_color(db, chat_id, draft, color: str) -> None:
    if len(color) < 2:
        await _send(chat_id, "Rangni yozing. Masalan: Oq")
        return
    await _set_step(db, draft, "plate", color=color)
    await _ask_plate(chat_id)


async def _ask_plate(chat_id) -> None:
    await _send(chat_id, (
        "Davlat raqamini yozing.\n\nMasalan: <code>01A123BC</code>\n\n"
        "Raqam yo'lovchiga faqat bron tasdiqlangandan keyin ko'rinadi."
    ))


async def _accept_plate(db, chat_id, draft, raw: str) -> None:
    try:
        plate = validate_uz_plate(raw)
    except ValueError as err:
        await _send(chat_id, f"❌ {tg._esc(str(err))}\n\nQaytadan yozing.")
        return

    user_id = uuid.UUID(draft.data["user_id"])
    taken = await db.scalar(
        select(DriverProfile.user_id).where(
            DriverProfile.vehicle_plate == plate, DriverProfile.user_id != user_id,
        )
    )
    if taken:
        await _send(chat_id, (
            "❌ Bu davlat raqami boshqa haydovchida ro'yxatdan o'tgan.\n\n"
            "Raqamni tekshirib qaytadan yozing yoki administrator bilan bog'laning."
        ))
        return

    await _set_step(db, draft, "seats", plate=plate)
    buttons = [{"text": str(n), "callback_data": f"{RG}st:{n}"} for n in SEATS]
    await _send(chat_id, (
        "Mashinada yo'lovchi uchun nechta o'rin bor? (haydovchidan tashqari)"
    ), {"inline_keyboard": [buttons]})


async def _finish_driver(db: AsyncSession, chat_id, draft: TelegramSignup, seats: int) -> None:
    from app.schemas.driver import DriverApplyRequest
    from app.services import driver_service
    from app.services import telegram_driver_bot as dbot

    data = draft.data or {}
    user = await db.get(User, uuid.UUID(data["user_id"]))
    try:
        request = DriverApplyRequest(
            vehicle_make=data["make"],
            vehicle_model=data["model"],
            vehicle_color=data["color"],
            vehicle_plate=data["plate"],
            vehicle_seats=seats,
        )
        driver = await driver_service.apply_driver(db, user, request)
    except (HTTPException, ValidationError) as err:
        detail = getattr(err, "detail", None) or "Ma'lumotlarda xato bor"
        await _set_step(db, draft, "plate")
        await _send(chat_id, f"❌ {tg._esc(str(detail))}\n\nDavlat raqamini qaytadan yozing.")
        return

    await _drop_draft(db, chat_id)

    if driver.status != DriverStatus.approved:
        await _send(chat_id, (
            "✅ Arizangiz qabul qilindi. Administrator 1–2 ish kunida ko'rib chiqadi — "
            "natija shu yerga keladi."
        ))
        return

    await _send(chat_id, (
        "🎉 Tabriklaymiz, siz haydovchi sifatida ro'yxatdan o'tdingiz!\n\n"
        f"{tg._esc(data['make'])} {tg._esc(data['model'])}, {tg._esc(data['color'])} · "
        f"<code>{tg._esc(data['plate'])}</code> · {seats} o'rin\n\n"
        "Endi doimiy yo'nalishingizni belgilang (<b>📍 Yo'nalishim</b>) — shundan keyin "
        "safar e'lon qilish ikki bosishda bo'ladi. Hujjatlarni keyinroq saytda yuklashingiz mumkin."
    ))
    await dbot.show_menu(db, user, chat_id)


# ─── Tugmalar ────────────────────────────────────────────────────────────────

async def handle_callback(db: AsyncSession, cq: dict, data: str) -> None:
    cq_id = cq.get("id")
    msg = cq.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    sender = cq.get("from") or {}
    await tg._answer_callback(cq_id)

    parts = data.split(":")
    action = parts[1] if len(parts) > 1 else ""

    if action in ("p", "d"):
        name = " ".join(filter(None, [sender.get("first_name"), sender.get("last_name")]))
        await begin(db, chat_id, "passenger" if action == "p" else "driver", name)
        return
    if action == "login":
        await send_login_link(db, chat_id)
        return

    draft = await _draft(db, chat_id)
    if draft is None:
        await _send(chat_id, "Bu tugma endi ishlamaydi. Boshlash uchun /start bosing.")
        return

    try:
        if action == "nm" and draft.step == "name":
            await _accept_name(db, chat_id, draft, (draft.data or {}).get("tg_name") or "")
        elif action == "mk" and draft.step == "make":
            if parts[2] == "o":
                await _send(chat_id, "Markani yozing. Masalan: Chevrolet")
            else:
                await _accept_make(db, chat_id, draft, MAKES[int(parts[2])])
        elif action == "md" and draft.step == "model":
            if parts[2] == "o":
                await _send(chat_id, "Modelni yozing.")
            else:
                await _accept_model(db, chat_id, draft, CHEVROLET_MODELS[int(parts[2])])
        elif action == "cl" and draft.step == "color":
            if parts[2] == "o":
                await _send(chat_id, "Rangni yozing. Masalan: Sariq")
            else:
                await _accept_color(db, chat_id, draft, COLORS[int(parts[2])])
        elif action == "st" and draft.step == "seats":
            seats = int(parts[2])
            if seats not in SEATS:
                raise ValueError(seats)
            await _finish_driver(db, chat_id, draft, seats)
        else:
            await _send(chat_id, "Bu tugma endi ishlamaydi.")
    except (IndexError, ValueError):
        logger.warning("Telegram ro'yxat: tushunarsiz tugma %r", data)
        await _send(chat_id, "Bu tugma endi ishlamaydi.")


# ─── Saytga kirish ───────────────────────────────────────────────────────────

async def send_login_link(db: AsyncSession, chat_id) -> None:
    """Bir martalik, qisqa muddatli havola — bosilsa sayt parolsiz ochiladi."""
    user = await _user_for_chat(db, chat_id)
    if user is None:
        await start_screen(db, chat_id)
        return

    now = datetime.utcnow()
    # Oldingi ishlatilmagan havolalar bekor — bir vaqtda bittasi amal qilsin
    await db.execute(
        update(TelegramLoginToken)
        .where(TelegramLoginToken.user_id == user.id, TelegramLoginToken.used_at.is_(None))
        .values(used_at=now)
    )
    token = secrets.token_urlsafe(32)
    db.add(TelegramLoginToken(
        id=uuid.uuid4(), token=token, user_id=user.id,
        expires_at=now + timedelta(minutes=LOGIN_TTL_MINUTES),
    ))
    await db.commit()

    site = settings.PUBLIC_SITE_URL.rstrip("/")
    await tg._call("sendMessage", {
        "chat_id": str(chat_id),
        "text": (
            f"Saytga kirish uchun tugmani bosing. Havola {LOGIN_TTL_MINUTES} daqiqa "
            "amal qiladi va faqat bir marta ishlaydi.\n\n"
            "⚠️ Bu havolani hech kimga yubormang — u orqali hisobingizga kiriladi."
        ),
        "link_preview_options": {"is_disabled": True},
        "reply_markup": {"inline_keyboard": [[
            {"text": "🌐 Saytni ochish", "url": f"{site}/auth/telegram?t={token}"},
        ]]},
    })


async def redeem_login_token(db: AsyncSession, token: str) -> User | None:
    """Havoladagi tokenni foydalanuvchiga almashtiradi. Bir marta ishlaydi."""
    if not token or len(token) > 64:
        return None
    row = (await db.execute(
        select(TelegramLoginToken).where(
            TelegramLoginToken.token == token,
            TelegramLoginToken.used_at.is_(None),
            TelegramLoginToken.expires_at > datetime.utcnow(),
        ).with_for_update()
    )).scalar_one_or_none()
    if row is None:
        return None
    user = await db.get(User, row.user_id)
    if user is None or user.is_blocked or not user.is_active:
        return None
    row.used_at = datetime.utcnow()
    user.last_login_at = datetime.utcnow()
    await db.commit()
    return user
