"""Telegram bot — haydovchi «doimiy yo'nalishini» shu yerdan belgilaydi.

**Nega kerak:** e'lon qilish oqimi (`telegram_driver_bot`) yo'nalish shabloniga
tayanadi, shablon esa faqat saytda belgilanardi. Ya'ni har yangi haydovchi
uchun kimdir saytga kirib, bir marta safar qo'yib, «doimiy yo'nalishim» ni
belgilashi kerak edi. Endi haydovchi buni o'zi qiladi va saytga umuman
kirmasligi mumkin.

**Holat bu yerda ham saqlanmaydi.** Tanlangan qiymatlar `callback_data`
ichida keyingi tugmaga o'tadi:

    rt:<qadam>:<fr>:<fd>:<tr>:<td>:<o'rin>:<narx>:<jo'nash>:<qaytish>

`_` — «tanlanmadi». Eng uzuni ~33 bayt, Telegram chegarasi esa 64 —
shuning uchun sessiya jadvali kerak emas.

Biznes qoidasi (qayerdan va qayerga bir xil bo'lmasin) bu yerda emas,
`route_service.set_route` ichida.
"""
from __future__ import annotations

import re
from datetime import time

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.driver import DriverProfile
from app.models.location import District, Region
from app.models.user import User
from app.services import telegram_driver_bot as dbot
from app.services import telegram_service as tg

RT = "rt:"
NONE = "_"

# Yo'nalish belgilashda narx uchun boshlang'ich variantlar. Yo'nalish hali
# yo'q, ya'ni shablon narxi ham yo'q — shuning uchun O'zbekistondagi
# viloyatlararo safar narxlari oralig'i olinadi. Mos kelmasa «Boshqa narx».
_PRICE_OPTIONS = (50_000, 70_000, 100_000, 120_000, 150_000, 180_000, 200_000, 250_000)
_PRICE_MARK = "#r"


def _arg(parts: list[str], index: int) -> int | None:
    """Callback bo'lagini o'qiydi; `_` va yo'q bo'lgani — None."""
    if index >= len(parts):
        return None
    value = parts[index]
    return None if value == NONE else int(value)


def _tail(*values) -> str:
    return ":".join(NONE if v is None else str(v) for v in values)


async def _regions(db: AsyncSession) -> list[Region]:
    return list((await db.execute(select(Region).order_by(Region.order))).scalars().all())


async def _districts(db: AsyncSession, region_id: int) -> list[District]:
    return list((await db.execute(
        select(District).where(District.region_id == region_id).order_by(District.name_uz)
    )).scalars().all())


async def _name(db: AsyncSession, model, obj_id: int | None) -> str | None:
    if obj_id is None:
        return None
    row = await db.get(model, obj_id)
    return row.name_uz if row else None


async def _summary(db: AsyncSession, fr, fd, tr, td) -> str:
    start = await _name(db, District, fd) or await _name(db, Region, fr) or "—"
    end = await _name(db, District, td) or await _name(db, Region, tr) or "—"
    return f"{start} → {end}"


# ─── Joriy yo'nalish ─────────────────────────────────────────────────────────

async def show_route(db: AsyncSession, user: User, chat_id, message_id=None) -> None:
    from app.services import route_service

    route = await route_service.get_route(db, user)
    if route is None:
        text = (
            "📍 <b>Doimiy yo'nalish</b>\n\n"
            "Hali belgilanmagan. Bir marta belgilab qo'ysangiz, keyin har kuni "
            "uch bosishda safar e'lon qilasiz."
        )
        buttons = [[{"text": "Yo'nalishni belgilash", "callback_data": f"{RT}new"}]]
    else:
        lines = [
            "📍 <b>Doimiy yo'nalish</b>",
            "",
            f"🚗 {tg._esc(dbot._route_line(route))}",
            f"💰 {dbot._money(route.price_per_seat)} so'm · {route.total_seats} o'rin",
        ]
        if route.departure_time:
            lines.append(f"🕗 Odatdagi vaqt: {route.departure_time:%H:%M}")
        if route.return_time:
            lines.append(f"🔄 Qaytish: {route.return_time:%H:%M}")
        text = "\n".join(lines)
        buttons = [
            [{"text": "✏️ O'zgartirish", "callback_data": f"{RT}new"}],
            [{"text": dbot.MENU_PUBLISH, "callback_data": f"{dbot.PB}day"}],
        ]

    await dbot._edit(chat_id, message_id, text, buttons)


# ─── 1-2: qayerdan ───────────────────────────────────────────────────────────

async def _ask_from_region(db: AsyncSession, chat_id, message_id) -> None:
    regions = await _regions(db)
    buttons = [{"text": r.name_uz, "callback_data": f"{RT}fd:{r.id}"} for r in regions]
    await dbot._edit(
        chat_id, message_id,
        "📍 <b>Doimiy yo'nalish</b>\n\nQayerdan jo'naysiz? Viloyatni tanlang:",
        dbot._rows(buttons, 2),
    )


async def _ask_from_district(db: AsyncSession, chat_id, message_id, fr: int) -> None:
    districts = await _districts(db, fr)
    buttons = [{"text": d.name_uz, "callback_data": f"{RT}tr:{_tail(fr, d.id)}"}
               for d in districts]
    rows = dbot._rows(buttons, 2)
    rows.append([{"text": "Butun viloyat", "callback_data": f"{RT}tr:{_tail(fr, None)}"}])

    region = await _name(db, Region, fr)
    await dbot._edit(
        chat_id, message_id,
        f"📍 {tg._esc(region or '')}\n\nQaysi tumandan? Aniq tuman yo'lovchiga "
        "qulay — lekin xohlasangiz butun viloyatni tanlang.",
        rows,
    )


# ─── 3-4: qayerga ────────────────────────────────────────────────────────────

async def _ask_to_region(db: AsyncSession, chat_id, message_id, fr: int, fd) -> None:
    regions = await _regions(db)
    # O'zidan o'ziga safar bo'lmaydi — jo'nash viloyatini ro'yxatdan olib tashlaymiz
    buttons = [{"text": r.name_uz, "callback_data": f"{RT}td:{_tail(fr, fd, r.id)}"}
               for r in regions if r.id != fr]
    start = await _summary(db, fr, fd, None, None)
    await dbot._edit(
        chat_id, message_id,
        f"📍 {tg._esc(start.split(' → ')[0])} → ?\n\nQayerga borasiz?",
        dbot._rows(buttons, 2),
    )


async def _ask_to_district(db: AsyncSession, chat_id, message_id, fr, fd, tr: int) -> None:
    districts = await _districts(db, tr)
    buttons = [{"text": d.name_uz, "callback_data": f"{RT}st:{_tail(fr, fd, tr, d.id)}"}
               for d in districts]
    rows = dbot._rows(buttons, 2)
    rows.append([{"text": "Butun viloyat",
                  "callback_data": f"{RT}st:{_tail(fr, fd, tr, None)}"}])

    region = await _name(db, Region, tr)
    await dbot._edit(
        chat_id, message_id,
        f"📍 {tg._esc(region or '')}\n\nQaysi tumangacha?",
        rows,
    )


# ─── 5: o'rin soni ───────────────────────────────────────────────────────────

async def _ask_seats(db: AsyncSession, user: User, chat_id, message_id, fr, fd, tr, td) -> None:
    profile = (await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == user.id)
    )).scalar_one_or_none()
    top = profile.vehicle_seats if profile else 4

    buttons = [{"text": str(n), "callback_data": f"{RT}pr:{_tail(fr, fd, tr, td, n)}"}
               for n in range(1, top + 1)]
    route = await _summary(db, fr, fd, tr, td)
    await dbot._edit(
        chat_id, message_id,
        f"🚗 {tg._esc(route)}\n\nOdatda nechta yo'lovchi olasiz?",
        dbot._rows(buttons, 4),
    )


# ─── 6: narx ─────────────────────────────────────────────────────────────────

async def _ask_price(db: AsyncSession, chat_id, message_id, fr, fd, tr, td, st) -> None:
    buttons = [{"text": dbot._money(p),
                "callback_data": f"{RT}dt:{_tail(fr, fd, tr, td, st, p)}"}
               for p in _PRICE_OPTIONS]
    rows = dbot._rows(buttons, 4)
    rows.append([{"text": "✏️ Boshqa narx",
                  "callback_data": f"{RT}po:{_tail(fr, fd, tr, td, st)}"}])

    route = await _summary(db, fr, fd, tr, td)
    await dbot._edit(
        chat_id, message_id,
        f"🚗 {tg._esc(route)}\n\nBitta o'rin odatda qancha turadi?\n"
        "<i>Keyin har e'londa o'zgartira olasiz.</i>",
        rows,
    )


async def _ask_price_text(chat_id, fr, fd, tr, td, st) -> None:
    """Kontekst xabar oxirida turadi — javob kelganda o'sha yerdan o'qiladi."""
    await tg._call("sendMessage", {
        "chat_id": str(chat_id),
        "text": (
            "💰 Bitta o'rin narxini yozing\n\n"
            "Faqat raqam, masalan: 155000\n\n"
            f"{_PRICE_MARK}:{_tail(fr, fd, tr, td, st)}"
        ),
        "reply_markup": {"force_reply": True, "input_field_placeholder": "155000"},
    })


def price_context(replied_text: str) -> list[str] | None:
    match = re.search(rf"{re.escape(_PRICE_MARK)}:([0-9_:]+)", replied_text or "")
    return match.group(1).split(":") if match else None


# ─── 7-8: vaqtlar ────────────────────────────────────────────────────────────

async def _ask_departure(db: AsyncSession, chat_id, message_id, fr, fd, tr, td, st, pr) -> None:
    buttons = [{"text": f"{h:02d}:00",
                "callback_data": f"{RT}rt:{_tail(fr, fd, tr, td, st, pr, f'{h:02d}00')}"}
               for h in dbot._HOURS]
    rows = dbot._rows(buttons, 4)
    rows.append([{"text": "Aniq vaqtim yo'q",
                  "callback_data": f"{RT}rt:{_tail(fr, fd, tr, td, st, pr, None)}"}])

    await dbot._edit(
        chat_id, message_id,
        "🕗 Odatda soat nechada jo'naysiz?\n"
        "<i>Bu faqat boshlang'ich qiymat — har e'londa vaqtni o'zingiz tanlaysiz.</i>",
        rows,
    )


async def _ask_return(db: AsyncSession, chat_id, message_id, fr, fd, tr, td, st, pr, dep) -> None:
    buttons = [{"text": f"{h:02d}:00",
                "callback_data": f"{RT}ok:{_tail(fr, fd, tr, td, st, pr, dep, f'{h:02d}00')}"}
               for h in dbot._HOURS]
    rows = dbot._rows(buttons, 4)
    rows.append([{"text": "Qaytish safari qo'ymayman",
                  "callback_data": f"{RT}ok:{_tail(fr, fd, tr, td, st, pr, dep, None)}"}])

    await dbot._edit(
        chat_id, message_id,
        "🔄 Orqaga qaytishda ham yo'lovchi olasizmi? Soatini tanlang.\n"
        "<i>Shunda e'lon qilishda qaytish safari bir bosishda qo'shiladi.</i>",
        rows,
    )


# ─── 9: tasdiq va saqlash ────────────────────────────────────────────────────

def _fmt_time(raw) -> str:
    return f"{raw[:2]}:{raw[2:]}" if raw else "—"


async def _confirm(db: AsyncSession, chat_id, message_id, parts: list[str]) -> None:
    fr, fd, tr, td = _arg(parts, 2), _arg(parts, 3), _arg(parts, 4), _arg(parts, 5)
    st, pr = _arg(parts, 6), _arg(parts, 7)
    dep = parts[8] if len(parts) > 8 and parts[8] != NONE else None
    ret = parts[9] if len(parts) > 9 and parts[9] != NONE else None

    route = await _summary(db, fr, fd, tr, td)
    lines = [
        "Tekshiring:",
        "",
        f"🚗 <b>{tg._esc(route)}</b>",
        f"💰 {dbot._money(pr)} so'm · {st} o'rin",
        f"🕗 Odatdagi vaqt: {_fmt_time(dep)}",
        f"🔄 Qaytish: {_fmt_time(ret)}",
        "",
        "Shu yo'nalishni saqlaymizmi?",
    ]
    await dbot._edit(chat_id, message_id, "\n".join(lines), [[
        {"text": "✅ Ha, saqlash", "callback_data": f"{RT}go:" + ":".join(parts[2:])},
        {"text": "❌ Bekor", "callback_data": f"{RT}cancel"},
    ]])


async def _save(db: AsyncSession, user: User, chat_id, message_id, parts: list[str]) -> None:
    from app.services import route_service

    fr, fd, tr, td = _arg(parts, 2), _arg(parts, 3), _arg(parts, 4), _arg(parts, 5)
    st, pr = _arg(parts, 6), _arg(parts, 7)
    dep = parts[8] if len(parts) > 8 and parts[8] != NONE else None
    ret = parts[9] if len(parts) > 9 and parts[9] != NONE else None

    def _as_time(raw):
        return time(int(raw[:2]), int(raw[2:])) if raw else None

    try:
        await route_service.set_route(
            db, user,
            from_region_id=fr, from_district_id=fd,
            to_region_id=tr, to_district_id=td,
            total_seats=st, price_per_seat=pr,
            departure_time=_as_time(dep), return_time=_as_time(ret),
        )
    except HTTPException as err:
        await dbot._edit(chat_id, message_id, f"❌ {tg._esc(str(err.detail))}", [[
            {"text": "Qaytadan", "callback_data": f"{RT}new"},
        ]])
        return

    route = await _summary(db, fr, fd, tr, td)
    await dbot._edit(chat_id, message_id, (
        f"✅ Yo'nalish saqlandi\n\n🚗 <b>{tg._esc(route)}</b>\n\n"
        "Endi safarni shu yerdan, uch bosishda e'lon qilasiz."
    ), [[{"text": dbot.MENU_PUBLISH, "callback_data": f"{dbot.PB}day"}]])


# ─── Yo'naltirish ────────────────────────────────────────────────────────────

async def handle_callback(db: AsyncSession, user: User, chat_id, message_id, data: str) -> None:
    parts = data.split(":")
    step = parts[1] if len(parts) > 1 else ""

    if step == "show":
        await show_route(db, user, chat_id, message_id)
    elif step == "cancel":
        await dbot._edit(chat_id, message_id, "Bekor qilindi.")
    elif step == "new":
        await _ask_from_region(db, chat_id, message_id)
    elif step == "fd":
        await _ask_from_district(db, chat_id, message_id, _arg(parts, 2))
    elif step == "tr":
        await _ask_to_region(db, chat_id, message_id, _arg(parts, 2), _arg(parts, 3))
    elif step == "td":
        await _ask_to_district(db, chat_id, message_id,
                               _arg(parts, 2), _arg(parts, 3), _arg(parts, 4))
    elif step == "st":
        await _ask_seats(db, user, chat_id, message_id,
                         _arg(parts, 2), _arg(parts, 3), _arg(parts, 4), _arg(parts, 5))
    elif step == "pr":
        await _ask_price(db, chat_id, message_id, _arg(parts, 2), _arg(parts, 3),
                         _arg(parts, 4), _arg(parts, 5), _arg(parts, 6))
    elif step == "po":
        await _ask_price_text(chat_id, _arg(parts, 2), _arg(parts, 3),
                              _arg(parts, 4), _arg(parts, 5), _arg(parts, 6))
    elif step == "dt":
        await _ask_departure(db, chat_id, message_id, _arg(parts, 2), _arg(parts, 3),
                             _arg(parts, 4), _arg(parts, 5), _arg(parts, 6), _arg(parts, 7))
    elif step == "rt":
        dep = parts[8] if len(parts) > 8 and parts[8] != NONE else None
        await _ask_return(db, chat_id, message_id, _arg(parts, 2), _arg(parts, 3),
                          _arg(parts, 4), _arg(parts, 5), _arg(parts, 6), _arg(parts, 7), dep)
    elif step == "ok":
        await _confirm(db, chat_id, message_id, parts)
    elif step == "go":
        await _save(db, user, chat_id, message_id, ["rt", "go"] + parts[2:])
    else:
        await dbot._edit(chat_id, message_id, "Bu tugma endi ishlamaydi.")


async def accept_price(db: AsyncSession, chat_id, typed: str, ctx: list[str]) -> None:
    """«Boshqa narx» javobini qabul qiladi va keyingi qadamga o'tadi."""
    digits = re.sub(r"\D", "", typed or "")
    if not digits:
        await dbot._send(chat_id, "Narxni faqat raqam bilan yozing, masalan: 155000")
        return
    price = int(digits)
    if price < dbot._MIN_PRICE:
        await dbot._send(chat_id, f"Narx kamida {dbot._money(dbot._MIN_PRICE)} so'm bo'lishi kerak.")
        return
    if price > 10_000_000:
        await dbot._send(chat_id, "Narx juda katta ko'rinyapti — qaytadan yozing.")
        return

    fr, fd, tr, td, st = (None if v == NONE else int(v) for v in ctx[:5])
    await _ask_departure(db, chat_id, None, fr, fd, tr, td, st, price)
