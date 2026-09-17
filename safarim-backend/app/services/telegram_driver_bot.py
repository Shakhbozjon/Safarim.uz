"""Telegram bot — haydovchi safarni shu yerdan e'lon qiladi va bekor qiladi.

**Nega kerak:** dala sinovida ko'p haydovchi saytdan ro'yxatdan o'tish va safar
e'lon qilishni uddalay olmadi. Ro'yxatdan o'tish — bir martalik to'siq, unga
qo'lda yordam berish mumkin. Safar e'lon qilish esa HAR KUNGI harakat: o'sha
yerdagi ishqalanish haydovchini bir hafta ichida yo'qotadi. Shuning uchun
avval kundalik harakat botga ko'chiriladi.

**Oqim ataylab sehrgar emas.** Haydovchining «doimiy yo'nalishi»
(`route_service`) shablon bo'lib turadi — yo'nalish, narx, o'rin soni va
afzalliklar o'sha yerdan olinadi. Botdan faqat *qachon*, *soat nechada* va
*qaytish ham kerakmi* so'raladi. Ko'p holatda uch bosish.

**Holat saqlanmaydi.** Har bosishning natijasi `callback_data` ichida keyingi
tugmaga o'tadi (Telegram chegarasi 64 bayt, bizda eng uzuni ~45). Shuning
uchun na sessiya jadvali, na Redis kerak: bot qayta ishga tushsa ham yarim
qolgan oqim buzilmaydi, eski tugmalar esa baribir ishlayveradi.

Biznes-qoidalar bu yerda TAKRORLANMAYDI — hammasi `trip_service.create_trip`
ichida (tasdiqlangan haydovchimi, pauzadami, o'rin soni, dublikat safar).
Bot faqat so'rov yig'adi va xatoni odam tushunadigan qilib ko'rsatadi.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timeutils import now_tashkent_naive
from app.models.driver import DriverProfile
from app.models.enums import DriverStatus, TripStatus
from app.models.user import User
from app.services import telegram_service as tg

logger = logging.getLogger(__name__)

# ─── Menyu (doimiy tugmalar) ─────────────────────────────────────────────────
# Buyruq (`/safar`) emas, aynan tugma: auditoriyamiz buyruq yodlamaydi, lekin
# ekran pastidagi tugmani ko'radi.
MENU_PUBLISH = "🚗 Safar e'lon qilish"
MENU_MY = "📋 Safarlarim"

PB = "pb:"   # e'lon qilish oqimi
MT = "mt:"   # safarlarim

# Kun tanlash — bugundan boshlab shuncha kun ko'rsatiladi
_DAYS = 3
_DAY_NAMES = ("Bugun", "Ertaga", "Indinga")

# Soat panjarasi. Yarim soatlar yo'q: shablondagi aniq vaqt alohida birinchi
# tugma bo'lib chiqadi, qolganlari uchun sayt bor.
_HOURS = tuple(range(5, 22))

_MONTHS_UZ = (
    "yanvar", "fevral", "mart", "aprel", "may", "iyun",
    "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
)


def menu_keyboard() -> dict:
    return {
        "keyboard": [[{"text": MENU_PUBLISH}], [{"text": MENU_MY}]],
        "resize_keyboard": True,
        "is_persistent": True,
    }


async def _send(chat_id, text: str, keyboard: dict | None = None) -> None:
    payload: dict = {"chat_id": str(chat_id), "text": text, "parse_mode": "HTML"}
    if keyboard is not None:
        payload["reply_markup"] = keyboard
    await tg._call("sendMessage", payload)


async def _edit(chat_id, message_id, text: str, buttons: list | None = None) -> None:
    payload: dict = {
        "chat_id": str(chat_id),
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
    }
    # Bo'sh ro'yxat ham yuboriladi: oqim tugagach tugmalar olib tashlansin,
    # aks holda haydovchi o'sha tugmani yana bosaveradi.
    payload["reply_markup"] = {"inline_keyboard": buttons or []}
    await tg._call("editMessageText", payload)


# ─── Kim kirishi mumkin ──────────────────────────────────────────────────────

async def _approved_driver(db: AsyncSession, user: User) -> DriverProfile | None:
    return (await db.execute(
        select(DriverProfile).where(
            DriverProfile.user_id == user.id,
            DriverProfile.status == DriverStatus.approved,
        )
    )).scalar_one_or_none()


async def user_for_chat(db: AsyncSession, chat_id) -> User | None:
    return (await db.execute(
        select(User).where(User.telegram_chat_id == str(chat_id))
    )).scalar_one_or_none()


async def show_menu(db: AsyncSession, user: User, chat_id, greeting: str | None = None) -> bool:
    """Haydovchiga menyuni ko'rsatadi. Haydovchi bo'lmasa — False."""
    if await _approved_driver(db, user) is None:
        return False
    await _send(chat_id, greeting or (
        "Quyidagi tugmalar orqali safaringizni boshqarasiz."
    ), menu_keyboard())
    return True


# ─── Ko'rinish yordamchilari ─────────────────────────────────────────────────

def _place(region, district) -> str:
    if district is not None:
        return district.name_uz
    return region.name_uz if region is not None else "—"


def _route_line(route) -> str:
    return (f"{_place(route.from_region, route.from_district)} → "
            f"{_place(route.to_region, route.to_district)}")


def _day_label(offset: int) -> str:
    d = now_tashkent_naive().date() + timedelta(days=offset)
    name = _DAY_NAMES[offset] if offset < len(_DAY_NAMES) else ""
    return f"{name}, {d.day}-{_MONTHS_UZ[d.month - 1]}"


def _money(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


def _rows(buttons: list[dict], per_row: int) -> list[list[dict]]:
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


# ─── 1-qadam: qachon ─────────────────────────────────────────────────────────

async def _ask_day(db: AsyncSession, user: User, chat_id, message_id=None) -> None:
    from app.services import route_service

    route = await route_service.get_route(db, user)
    if route is None:
        text = (
            "Sizda <b>doimiy yo'nalish</b> belgilanmagan.\n\n"
            "Bir marta saytda safar e'lon qilib, «Bu mening doimiy yo'nalishim» "
            "ni belgilang — shundan keyin bu yerdan uch bosishda e'lon qilasiz.\n\n"
            "uzsafar.uz"
        )
        if message_id:
            await _edit(chat_id, message_id, text)
        else:
            await _send(chat_id, text)
        return

    text = (
        f"🚗 <b>{tg._esc(_route_line(route))}</b>\n"
        f"{_money(route.price_per_seat)} so'm · {route.total_seats} o'rin\n\n"
        "Qachon jo'naysiz?"
    )
    buttons = [[{"text": _day_label(i), "callback_data": f"{PB}t:{i}"}] for i in range(_DAYS)]

    if message_id:
        await _edit(chat_id, message_id, text, buttons)
    else:
        await tg._call("sendMessage", {
            "chat_id": str(chat_id), "text": text, "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": buttons},
        })


# ─── 2-qadam: soat ───────────────────────────────────────────────────────────

async def _ask_time(db: AsyncSession, user: User, chat_id, message_id, day: int) -> None:
    from app.services import route_service

    route = await route_service.get_route(db, user)
    if route is None:
        await _ask_day(db, user, chat_id, message_id)
        return

    usual = route.departure_time.strftime("%H:%M") if route.departure_time else None

    buttons: list[dict] = []
    if usual and route.departure_time.minute != 0:
        # Odatdagi vaqti butun soat emas — uni alohida birinchi qilib qo'yamiz
        buttons.append({"text": f"{usual} ✓", "callback_data": f"{PB}r:{day}:{usual.replace(':', '')}"})
    for h in _HOURS:
        label = f"{h:02d}:00"
        if usual == label:
            label += " ✓"
        buttons.append({"text": label, "callback_data": f"{PB}r:{day}:{h:02d}00"})

    text = f"📅 {tg._esc(_day_label(day))}\n\nSoat nechada jo'naysiz?"
    await _edit(chat_id, message_id, text, _rows(buttons, 4))


# ─── 3-qadam: qaytish ────────────────────────────────────────────────────────

async def _ask_return(
    db: AsyncSession, user: User, chat_id, message_id, day: int, hhmm: str
) -> None:
    from app.services import route_service

    route = await route_service.get_route(db, user)
    # Shablonda qaytish vaqti yo'q bo'lsa savol ham bermaymiz — ortiqcha bosish
    if route is None or route.return_time is None:
        await _publish(db, user, chat_id, message_id, day, hhmm, want_return=False)
        return

    ret = route.return_time.strftime("%H:%M")
    text = (
        f"📅 {tg._esc(_day_label(day))}, {_fmt(hhmm)}\n\n"
        f"Qaytish safarini ham e'lon qilaymizmi?"
    )
    buttons = [[
        {"text": f"Ha, {ret} da", "callback_data": f"{PB}go:{day}:{hhmm}:1"},
        {"text": "Yo'q", "callback_data": f"{PB}go:{day}:{hhmm}:0"},
    ]]
    await _edit(chat_id, message_id, text, buttons)


def _fmt(hhmm: str) -> str:
    return f"{hhmm[:2]}:{hhmm[2:]}"


# ─── Yakun: e'lon qilish ─────────────────────────────────────────────────────

async def _publish(
    db: AsyncSession, user: User, chat_id, message_id,
    day: int, hhmm: str, want_return: bool, force: bool = False,
) -> None:
    from app.schemas.route import RoutePublishRequest
    from app.services import route_service

    route = await route_service.get_route(db, user)
    if route is None:
        await _ask_day(db, user, chat_id, message_id)
        return

    dep_date: date = now_tashkent_naive().date() + timedelta(days=day)
    ret_time = route.return_time.strftime("%H:%M") if route.return_time else None

    try:
        trips, warning = await route_service.publish(db, user, RoutePublishRequest(
            departure_date=dep_date,
            departure_time=_fmt(hhmm),
            include_return=bool(want_return and ret_time),
            return_time=ret_time if want_return else None,
            confirm_day_conflict=force,
        ))
    except HTTPException as err:
        detail = str(err.detail)
        if err.status_code == 409 and not force:
            # «Bu kunga mos kelmaydigan yo'nalish» — to'siq emas, tasdiq so'raladi
            await _edit(chat_id, message_id, f"⚠️ {tg._esc(detail)}", [[
                {"text": "Ha, baribir e'lon qil",
                 "callback_data": f"{PB}go:{day}:{hhmm}:{int(want_return)}:1"},
                {"text": "Bekor qilish", "callback_data": f"{PB}cancel"},
            ]])
            return
        await _edit(chat_id, message_id, f"❌ {tg._esc(detail)}")
        return

    lines = [f"✅ E'lon qilindi — <b>{len(trips)} ta safar</b>" if len(trips) > 1
             else "✅ Safar e'lon qilindi"]
    for t in trips:
        lines.append(
            f"\n🚗 {tg._esc(_place(t.from_region, t.from_district))} → "
            f"{tg._esc(_place(t.to_region, t.to_district))}\n"
            f"📅 {t.departure_date.day}-{_MONTHS_UZ[t.departure_date.month - 1]}, "
            f"{t.departure_time:%H:%M} · {_money(t.price_per_seat)} so'm · "
            f"{t.total_seats} o'rin"
        )
    if warning:
        lines.append(f"\n⚠️ {tg._esc(warning)}")
    lines.append("\nGuruhga ham chiqdi. Band qilinsa shu yerga xabar keladi.")

    await _edit(chat_id, message_id, "\n".join(lines))


# ─── Safarlarim ──────────────────────────────────────────────────────────────

_OPEN = (TripStatus.active, TripStatus.full, TripStatus.started)


async def _my_trips(db: AsyncSession, user: User, chat_id, message_id=None) -> None:
    from app.services import trip_service

    trips = [t for t in await trip_service.get_my_trips(db, user) if t.status in _OPEN]
    trips.sort(key=lambda t: (t.departure_date, t.departure_time))

    if not trips:
        text = "Hozircha ochiq safaringiz yo'q."
        buttons = [[{"text": MENU_PUBLISH, "callback_data": f"{PB}day"}]]
    else:
        text = "📋 <b>Ochiq safarlaringiz</b>\n\nBekor qilish uchun tugmani bosing:"
        buttons = [[{
            "text": (f"{t.departure_date.day}-{_MONTHS_UZ[t.departure_date.month - 1]} "
                     f"{t.departure_time:%H:%M} · "
                     f"{_place(t.from_region, t.from_district)} → "
                     f"{_place(t.to_region, t.to_district)}"),
            "callback_data": f"{MT}x:{t.id}",
        }] for t in trips[:8]]

    if message_id:
        await _edit(chat_id, message_id, text, buttons)
    else:
        await tg._call("sendMessage", {
            "chat_id": str(chat_id), "text": text, "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": buttons},
        })


async def _ask_cancel(db: AsyncSession, user: User, chat_id, message_id, trip_id: str) -> None:
    from app.services import trip_service

    try:
        trip = await trip_service.get_trip(db, trip_id)
    except HTTPException:
        await _edit(chat_id, message_id, "Safar topilmadi.")
        return

    booked = trip.total_seats - trip.available_seats
    warn = (f"\n\n⚠️ Bu safarda <b>{booked} ta yo'lovchi</b> bor — ularga bekor "
            "qilingani haqida xabar boradi.") if booked > 0 else ""

    text = (
        f"Shu safarni bekor qilamizmi?\n\n"
        f"🚗 {tg._esc(_place(trip.from_region, trip.from_district))} → "
        f"{tg._esc(_place(trip.to_region, trip.to_district))}\n"
        f"📅 {trip.departure_date.day}-{_MONTHS_UZ[trip.departure_date.month - 1]}, "
        f"{trip.departure_time:%H:%M}{warn}"
    )
    await _edit(chat_id, message_id, text, [[
        {"text": "Ha, bekor qil", "callback_data": f"{MT}xx:{trip.id}"},
        {"text": "Yo'q", "callback_data": f"{MT}list"},
    ]])


async def _do_cancel(db: AsyncSession, user: User, chat_id, message_id, trip_id: str) -> None:
    from app.services import trip_service

    try:
        await trip_service.cancel_trip(db, trip_id, user, "Haydovchi bekor qildi")
    except HTTPException as err:
        await _edit(chat_id, message_id, f"❌ {tg._esc(str(err.detail))}")
        return
    await _edit(chat_id, message_id, "✅ Safar bekor qilindi.")


# ─── Kiruvchi hodisalar ──────────────────────────────────────────────────────

async def handle_text(db: AsyncSession, chat_id, text: str) -> bool:
    """Menyu tugmasi bosildimi? Ha bo'lsa — bajaradi va True qaytaradi."""
    if text not in (MENU_PUBLISH, MENU_MY):
        return False

    user = await user_for_chat(db, chat_id)
    if user is None or await _approved_driver(db, user) is None:
        await _send(chat_id, (
            "Bu bo'lim tasdiqlangan haydovchilar uchun.\n\n"
            "Haydovchi bo'lmoqchi bo'lsangiz: uzsafar.uz"
        ))
        return True

    if text == MENU_PUBLISH:
        await _ask_day(db, user, chat_id)
    else:
        await _my_trips(db, user, chat_id)
    return True


async def handle_callback(db: AsyncSession, cq: dict, data: str) -> None:
    cq_id = cq.get("id")
    msg = cq.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    message_id = msg.get("message_id")

    user = await user_for_chat(db, chat_id)
    if user is None or await _approved_driver(db, user) is None:
        await tg._answer_callback(cq_id, "Hisobingiz topilmadi")
        return

    await tg._answer_callback(cq_id)
    parts = data.split(":")

    try:
        if data == f"{PB}day":
            await _ask_day(db, user, chat_id, message_id)
        elif data == f"{PB}cancel":
            await _edit(chat_id, message_id, "Bekor qilindi.")
        elif parts[1] == "t":                       # pb:t:<day>
            await _ask_time(db, user, chat_id, message_id, int(parts[2]))
        elif parts[1] == "r":                       # pb:r:<day>:<hhmm>
            await _ask_return(db, user, chat_id, message_id, int(parts[2]), parts[3])
        elif parts[1] == "go":                      # pb:go:<day>:<hhmm>:<ret>[:1]
            await _publish(
                db, user, chat_id, message_id,
                day=int(parts[2]), hhmm=parts[3],
                want_return=parts[4] == "1",
                force=len(parts) > 5 and parts[5] == "1",
            )
        elif data == f"{MT}list":
            await _my_trips(db, user, chat_id, message_id)
        elif parts[1] == "x":                       # mt:x:<trip_id>
            await _ask_cancel(db, user, chat_id, message_id, parts[2])
        elif parts[1] == "xx":                      # mt:xx:<trip_id>
            await _do_cancel(db, user, chat_id, message_id, parts[2])
        else:
            await _edit(chat_id, message_id, "Bu tugma endi ishlamaydi.")
    except (IndexError, ValueError):
        logger.warning("Telegram: tushunarsiz callback %r", data)
        await _edit(chat_id, message_id, "Bu tugma endi ishlamaydi.")
