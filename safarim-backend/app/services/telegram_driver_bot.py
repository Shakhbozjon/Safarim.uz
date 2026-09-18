"""Telegram bot — haydovchi safarni shu yerdan e'lon qiladi, boshlaydi va bekor qiladi.

**Nega kerak:** dala sinovida ko'p haydovchi saytdan ro'yxatdan o'tish va safar
e'lon qilishni uddalay olmadi. Ro'yxatdan o'tish — bir martalik to'siq, unga
qo'lda yordam berish mumkin. Safar e'lon qilish esa HAR KUNGI harakat: o'sha
yerdagi ishqalanish haydovchini bir hafta ichida yo'qotadi. Shuning uchun
avval kundalik harakat botga ko'chiriladi.

**Oqim ataylab sehrgar emas.** Haydovchining «doimiy yo'nalishi»
(`route_service`) shablon bo'lib turadi — yo'nalish, o'rin soni va afzalliklar
o'sha yerdan olinadi. Botdan so'raladigani:

    qachon → soat → narx → qaytish ham kerakmi → tasdiq

Narx alohida so'raladi, chunki u kundan-kunga o'zgaradi; shablon narxi
tugmalar uchun boshlang'ich qiymat bo'lib xizmat qiladi. Qaytish narxi
standart holda borish narxiga teng, lekin tasdiq ekranida ochiq yoziladi va
bir bosishda o'zgartiriladi — u doim ham teng bo'lavermaydi.

Oxirgi ekranda hammasi qayta ko'rsatiladi (qaytish safarining yo'nalishi,
SANASI va narxi ham): e'lon qilingach uni faqat bekor qilish mumkin, bekor
qilish esa yo'lovchiga noqulaylik. Qaytish sanasi alohida muhim — qaytish
vaqti borish vaqtidan kichik bo'lsa u ertangi kunga tushadi.

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
import re
from datetime import date, time, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timeutils import format_day_uz, now_tashkent_naive
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
MENU_ROUTE = "📍 Yo'nalishim"

PB = "pb:"   # e'lon qilish oqimi
MT = "mt:"   # safarlarim
RT = "rt:"   # doimiy yo'nalish (telegram_route_setup)

# Kun tanlash — bugundan boshlab shuncha kun ko'rsatiladi
_DAYS = 3

# Soat panjarasi. Yarim soatlar yo'q: shablondagi aniq vaqt alohida birinchi
# tugma bo'lib chiqadi, qolganlari uchun sayt bor.
_HOURS = tuple(range(5, 22))


def menu_keyboard() -> dict:
    return {
        "keyboard": [[{"text": MENU_PUBLISH}], [{"text": MENU_MY}, {"text": MENU_ROUTE}]],
        "resize_keyboard": True,
        "is_persistent": True,
    }


async def _send(chat_id, text: str, keyboard: dict | None = None) -> None:
    payload: dict = {"chat_id": str(chat_id), "text": text, "parse_mode": "HTML"}
    if keyboard is not None:
        payload["reply_markup"] = keyboard
    await tg._call("sendMessage", payload)


async def _edit(chat_id, message_id, text: str, buttons: list | None = None) -> None:
    """Oqim bitta xabar ichida boradi — chat qadamlar bilan to'lib ketmasin.

    `message_id` bo'lmasa (masalan haydovchi narxni yozib yuborgan, ya'ni
    tahrirlanadigan xabar yo'q) — yangi xabar yuboriladi.
    """
    # Bo'sh ro'yxat ham yuboriladi: oqim tugagach tugmalar olib tashlansin,
    # aks holda haydovchi o'sha tugmani yana bosaveradi.
    markup = {"inline_keyboard": buttons or []}
    if not message_id:
        await tg._call("sendMessage", {
            "chat_id": str(chat_id), "text": text,
            "parse_mode": "HTML", "reply_markup": markup,
        })
        return
    await tg._call("editMessageText", {
        "chat_id": str(chat_id),
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": markup,
    })


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
    return format_day_uz(now_tashkent_naive().date() + timedelta(days=offset))


def _money(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


def _rows(buttons: list[dict], per_row: int) -> list[list[dict]]:
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


def _opt_int(parts: list[str], index: int) -> int | None:
    """Callback bo'lagini o'qiydi; `_` yoki yo'q bo'lsa — None."""
    if index >= len(parts) or parts[index] in ("_", ""):
        return None
    return int(parts[index])


# ─── 1-qadam: qachon ─────────────────────────────────────────────────────────

async def _ask_day(db: AsyncSession, user: User, chat_id, message_id=None) -> None:
    from app.services import route_service

    route = await route_service.get_route(db, user)
    if route is None:
        await _edit(chat_id, message_id, (
            "Sizda <b>doimiy yo'nalish</b> belgilanmagan.\n\n"
            "Bir marta belgilab qo'ysangiz, keyin har kuni uch bosishda safar "
            "e'lon qilasiz."
        ), [[{"text": "Yo'nalishni belgilash", "callback_data": f"{RT}new"}]])
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
        buttons.append({"text": f"{usual} ✓", "callback_data": f"{PB}p:{day}:{usual.replace(':', '')}"})
    for h in _HOURS:
        label = f"{h:02d}:00"
        if usual == label:
            label += " ✓"
        buttons.append({"text": label, "callback_data": f"{PB}p:{day}:{h:02d}00"})

    text = f"📅 {tg._esc(_day_label(day))}\n\nSoat nechada jo'naysiz?"
    await _edit(chat_id, message_id, text, _rows(buttons, 4))


# ─── 3-qadam: narx ───────────────────────────────────────────────────────────
# Narx kundan-kunga o'zgaradi (talab, yoqilg'i, bayram), shuning uchun shablon
# narxi faqat BOSHLANG'ICH qiymat. Tayyor tugmalar terishdan tez va holat ham
# talab qilmaydi; grid ichiga tushmaydigan summa uchun «Boshqa narx» bor.

_PRICE_STEPS = (-20_000, -10_000, -5_000, 0, 5_000, 10_000, 20_000, 30_000)
_MIN_PRICE = 1_000                  # `TripCreate.validate_price` bilan bir xil
_PRICE_MARK = "#p"                  # javobdan kontekstni topish uchun belgi


async def _ask_price(
    db: AsyncSession, user: User, chat_id, message_id, day: int, hhmm: str
) -> None:
    from app.services import route_service

    route = await route_service.get_route(db, user)
    if route is None:
        await _ask_day(db, user, chat_id, message_id)
        return

    base = route.price_per_seat
    buttons: list[dict] = []
    for step in _PRICE_STEPS:
        value = base + step
        if value < _MIN_PRICE:
            continue
        label = _money(value) + (" ✓" if step == 0 else "")
        buttons.append({"text": label, "callback_data": f"{PB}r:{day}:{hhmm}:{value}"})

    rows = _rows(buttons, 4)
    rows.append([{"text": "✏️ Boshqa narx", "callback_data": f"{PB}other:{day}:{hhmm}"}])

    text = f"📅 {tg._esc(_day_label(day))}, {_fmt(hhmm)}\n\nBitta o'rin qancha turadi?"
    await _edit(chat_id, message_id, text, rows)


async def _ask_price_text(chat_id, day: int, hhmm: str) -> None:
    """Narxni qo'lda yozish. Kontekst shu xabarning OXIRIDA turadi.

    Haydovchi javob berganda Telegram asl xabarni `reply_to_message` ichida
    qaytaradi — kun va soatni o'sha yerdan o'qiymiz. Shu sababli bu yerda ham
    sessiya jadvali kerak emas.
    """
    await tg._call("sendMessage", {
        "chat_id": str(chat_id),
        "text": (
            "💰 Bitta o'rin narxini yozing\n\n"
            f"{_day_label(day)}, {_fmt(hhmm)}\n"
            "Faqat raqam, masalan: 155000\n\n"
            f"{_PRICE_MARK}{day}-{hhmm}"
        ),
        "reply_markup": {"force_reply": True, "input_field_placeholder": "155000"},
    })


# ─── 4-qadam: qaytish ────────────────────────────────────────────────────────

async def _ask_return(
    db: AsyncSession, user: User, chat_id, message_id,
    day: int, hhmm: str, price: int,
) -> None:
    from app.services import route_service

    route = await route_service.get_route(db, user)
    # Shablonda qaytish vaqti yo'q bo'lsa savol ham bermaymiz — ortiqcha bosish
    if route is None or route.return_time is None:
        await _confirm(db, user, chat_id, message_id, day, hhmm, price, want_return=False)
        return

    ret = route.return_time.strftime("%H:%M")
    text = (
        f"📅 {tg._esc(_day_label(day))}, {_fmt(hhmm)} · {_money(price)} so'm\n\n"
        f"Qaytish safarini ham e'lon qilaymizmi?"
    )
    # `_` — qaytish narxi borish narxi bilan bir xil. Haydovchi uni tasdiq
    # ekranida ko'radi va xohlasa bir bosishda o'zgartiradi.
    buttons = [[
        {"text": f"Ha, {ret} da", "callback_data": f"{PB}c:{day}:{hhmm}:{price}:1:_"},
        {"text": "Yo'q", "callback_data": f"{PB}c:{day}:{hhmm}:{price}:0:_"},
    ]]
    await _edit(chat_id, message_id, text, buttons)


# ─── Qaytish narxi (ixtiyoriy qadam) ─────────────────────────────────────────
# Qaytish narxi doim borish narxiga teng emas (talab yo'nalish bo'yicha farq
# qiladi). Shuning uchun u tasdiqda ochiq ko'rsatiladi va shu yerdan
# o'zgartiriladi — narx bir xil bo'lgan kunlarda ortiqcha bosish bo'lmasin.

_RETURN_MARK = "#q"


async def _ask_return_price(
    db: AsyncSession, user: User, chat_id, message_id, day: int, hhmm: str, price: int
) -> None:
    buttons: list[dict] = []
    for step in _PRICE_STEPS:
        value = price + step
        if value < _MIN_PRICE:
            continue
        label = _money(value) + (" ✓" if step == 0 else "")
        buttons.append({"text": label,
                        "callback_data": f"{PB}c:{day}:{hhmm}:{price}:1:{value}"})

    rows = _rows(buttons, 4)
    rows.append([{"text": "✏️ Boshqa narx",
                  "callback_data": f"{PB}qo:{day}:{hhmm}:{price}"}])

    await _edit(chat_id, message_id, (
        "🔄 <b>Qaytish safari</b>\n\nBitta o'rin qancha turadi?"
    ), rows)


async def _ask_return_price_text(chat_id, day: int, hhmm: str, price: int) -> None:
    await tg._call("sendMessage", {
        "chat_id": str(chat_id),
        "text": (
            "🔄 Qaytish safari narxini yozing\n\n"
            "Faqat raqam, masalan: 140000\n\n"
            f"{_RETURN_MARK}{day}-{hhmm}-{price}"
        ),
        "reply_markup": {"force_reply": True, "input_field_placeholder": "140000"},
    })


def _return_price_context(replied_text: str) -> tuple[int, str, int] | None:
    match = re.search(
        rf"{re.escape(_RETURN_MARK)}(\d+)-(\d{{4}})-(\d+)", replied_text or "")
    if match is None:
        return None
    return int(match.group(1)), match.group(2), int(match.group(3))


# ─── 5-qadam: tasdiq ─────────────────────────────────────────────────────────
# E'lon qilingach uni faqat bekor qilish mumkin (va bekor qilish yo'lovchiga
# noqulaylik) — shuning uchun oxirida hamma narsa bir ekranda ko'rsatiladi.

async def _confirm(
    db: AsyncSession, user: User, chat_id, message_id,
    day: int, hhmm: str, price: int, want_return: bool, return_price: int | None = None,
) -> None:
    from app.services import route_service

    route = await route_service.get_route(db, user)
    if route is None:
        await _ask_day(db, user, chat_id, message_id)
        return

    lines = [
        "Tekshiring:",
        "",
        f"🚗 <b>{tg._esc(_route_line(route))}</b>",
        f"📅 {tg._esc(_day_label(day))}, {_fmt(hhmm)}",
        f"💰 {_money(price)} so'm · {route.total_seats} o'rin",
    ]

    buttons: list[list[dict]] = []
    show_return = bool(want_return and route.return_time)
    rprice = return_price or price

    if show_return:
        # Qaytish sanasi o'zi hisoblanadi: qaytish vaqti borish vaqtidan
        # kichik bo'lsa u ERTASI kunga tushadi. Haydovchi buni ko'rmasa,
        # bilmagan holda ertangi kunga safar qo'yib yuborardi.
        dep_date = now_tashkent_naive().date() + timedelta(days=day)
        ret_date = route_service.default_return_date(
            dep_date, time(int(hhmm[:2]), int(hhmm[2:])), route.return_time)
        lines += [
            "",
            "🔄 <b>Qaytish safari</b>",
            f"   {tg._esc(_place(route.to_region, route.to_district))} → "
            f"{tg._esc(_place(route.from_region, route.from_district))}",
            f"   {tg._esc(format_day_uz(ret_date))}, {route.return_time:%H:%M}",
            f"   {_money(rprice)} so'm",
        ]
        buttons.append([{
            "text": "✏️ Qaytish narxini o'zgartirish",
            "callback_data": f"{PB}qp:{day}:{hhmm}:{price}",
        }])

    lines += ["", "Hammasi to'g'rimi?"]

    buttons.append([
        {"text": "✅ Ha, e'lon qil",
         "callback_data": (f"{PB}go:{day}:{hhmm}:{price}:{int(want_return)}:"
                           f"{return_price or '_'}")},
        {"text": "❌ Bekor", "callback_data": f"{PB}cancel"},
    ])
    await _edit(chat_id, message_id, "\n".join(lines), buttons)


def _fmt(hhmm: str) -> str:
    return f"{hhmm[:2]}:{hhmm[2:]}"


# ─── Yakun: e'lon qilish ─────────────────────────────────────────────────────

async def _publish(
    db: AsyncSession, user: User, chat_id, message_id,
    day: int, hhmm: str, price: int, want_return: bool,
    return_price: int | None = None, force: bool = False,
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
            price_per_seat=price,
            include_return=bool(want_return and ret_time),
            return_time=ret_time if want_return else None,
            return_price=return_price if want_return else None,
            confirm_day_conflict=force,
        ))
    except HTTPException as err:
        detail = str(err.detail)
        if err.status_code == 409 and not force:
            # «Bu kunga mos kelmaydigan yo'nalish» — to'siq emas, tasdiq so'raladi
            await _edit(chat_id, message_id, f"⚠️ {tg._esc(detail)}", [[
                {"text": "Ha, baribir e'lon qil",
                 "callback_data": (f"{PB}go:{day}:{hhmm}:{price}:{int(want_return)}:"
                                   f"{return_price or '_'}:1")},
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
            f"📅 {tg._esc(format_day_uz(t.departure_date))}, "
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
        text = "📋 <b>Ochiq safarlaringiz</b>\n\nBoshqarish uchun tugmani bosing:"
        buttons = [[{
            "text": (("🚗 " if t.status == TripStatus.started else "")
                     + f"{format_day_uz(t.departure_date)} "
                     f"{t.departure_time:%H:%M} · "
                     f"{_place(t.from_region, t.from_district)} → "
                     f"{_place(t.to_region, t.to_district)}"),
            "callback_data": f"{MT}v:{t.id}",
        }] for t in trips[:8]]

    await _edit(chat_id, message_id, text, buttons)


async def _confirmed_seats(db: AsyncSession, trip_id) -> int:
    """Tasdiqlangan yo'lovchilar soni — «boshlash» aynan shunga bog'liq."""
    from app.models.booking import Booking
    from app.models.enums import BookingStatus

    return await db.scalar(
        select(func.count()).select_from(Booking).where(
            Booking.trip_id == trip_id,
            Booking.status == BookingStatus.confirmed,
        )
    ) or 0


async def _trip_card(db: AsyncSession, chat_id, message_id, trip_id: str) -> None:
    """Bitta safar: holati va mumkin bo'lgan amallar."""
    from app.services import trip_service

    try:
        trip = await trip_service.get_trip(db, trip_id)
    except HTTPException:
        await _edit(chat_id, message_id, "Safar topilmadi.")
        return

    booked = trip.total_seats - trip.available_seats
    confirmed = await _confirmed_seats(db, trip.id)

    lines = [
        f"🚗 <b>{tg._esc(_place(trip.from_region, trip.from_district))} → "
        f"{tg._esc(_place(trip.to_region, trip.to_district))}</b>",
        f"📅 {tg._esc(format_day_uz(trip.departure_date))}, {trip.departure_time:%H:%M}",
        f"💰 {_money(trip.price_per_seat)} so'm · {trip.available_seats} bo'sh o'rin",
    ]
    if booked:
        lines.append(f"👥 {booked} ta yo'lovchi")

    buttons: list[list[dict]] = []

    if trip.status == TripStatus.started:
        lines.append("\n🚗 <b>Yo'ldasiz</b> — safar boshlangan.")
    else:
        if confirmed:
            buttons.append([{"text": "▶️ Safarni boshlash",
                             "callback_data": f"{MT}s:{trip.id}"}])
        else:
            lines.append("\nYo'lovchi bo'lmagani uchun safarni boshlab bo'lmaydi.")
        buttons.append([{"text": "❌ Safarni bekor qilish",
                         "callback_data": f"{MT}x:{trip.id}"}])

    buttons.append([{"text": "← Orqaga", "callback_data": f"{MT}list"}])
    await _edit(chat_id, message_id, "\n".join(lines), buttons)


# ─── Safarni boshlash ────────────────────────────────────────────────────────

async def _ask_start(db: AsyncSession, chat_id, message_id, trip_id: str) -> None:
    from app.services import trip_service

    try:
        trip = await trip_service.get_trip(db, trip_id)
    except HTTPException:
        await _edit(chat_id, message_id, "Safar topilmadi.")
        return

    # Saytdagi tasdiq oynasi bilan bir xil ogohlantirish — haydovchi ikki
    # joyda ikki xil gap eshitmasin
    text = (
        f"Safarni boshlaysizmi?\n\n"
        f"🚗 {tg._esc(_place(trip.from_region, trip.from_district))} → "
        f"{tg._esc(_place(trip.to_region, trip.to_district))}\n"
        f"📅 {tg._esc(format_day_uz(trip.departure_date))}, "
        f"{trip.departure_time:%H:%M}\n\n"
        "Safar <b>qidiruvdan olib tashlanadi</b> — yangi buyurtma qabul "
        "qilinmaydi (o'rin bo'sh bo'lsa ham). Tasdiqlangan yo'lovchilar qoladi, "
        "tasdiqlanmagan buyurtmalar bekor qilinadi."
    )
    await _edit(chat_id, message_id, text, [[
        {"text": "Ha, boshlash", "callback_data": f"{MT}ss:{trip.id}"},
        {"text": "Yo'q", "callback_data": f"{MT}v:{trip.id}"},
    ]])


async def _do_start(db: AsyncSession, user: User, chat_id, message_id, trip_id: str) -> None:
    from app.services import trip_service

    try:
        await trip_service.start_trip(db, trip_id, user)
    except HTTPException as err:
        await _edit(chat_id, message_id, f"❌ {tg._esc(str(err.detail))}", [[
            {"text": "← Orqaga", "callback_data": f"{MT}list"},
        ]])
        return
    await _edit(chat_id, message_id, (
        "✅ Safar boshlandi — yaxshi yo'l!\n\n"
        "Safar tugagach «bo'ldimi?» degan savol shu yerga keladi."
    ))


# ─── Bekor qilish ────────────────────────────────────────────────────────────

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
        f"📅 {tg._esc(format_day_uz(trip.departure_date))}, "
        f"{trip.departure_time:%H:%M}{warn}"
    )
    await _edit(chat_id, message_id, text, [[
        {"text": "Ha, bekor qil", "callback_data": f"{MT}xx:{trip.id}"},
        {"text": "Yo'q", "callback_data": f"{MT}v:{trip.id}"},
    ]])


async def _do_cancel(db: AsyncSession, user: User, chat_id, message_id, trip_id: str) -> None:
    from app.services import trip_service

    try:
        await trip_service.cancel_trip(db, trip_id, user, "Haydovchi bekor qildi")
    except HTTPException as err:
        await _edit(chat_id, message_id, f"❌ {tg._esc(str(err.detail))}", [[
            {"text": "← Orqaga", "callback_data": f"{MT}list"},
        ]])
        return
    await _edit(chat_id, message_id, "✅ Safar bekor qilindi.")


# ─── Kiruvchi hodisalar ──────────────────────────────────────────────────────

def _price_context(replied_text: str) -> tuple[int, str] | None:
    """Narx so'ralgan xabardan kun va soatni ajratadi (`#p1-0800`)."""
    match = re.search(rf"{re.escape(_PRICE_MARK)}(\d+)-(\d{{4}})", replied_text or "")
    if match is None:
        return None
    return int(match.group(1)), match.group(2)


async def _accept_price(
    db: AsyncSession, user: User, chat_id, typed: str, day: int, hhmm: str
) -> None:
    # "155 000", "155000 so'm" — hammasidan raqamni ajratib olamiz
    price, problem = _parse_price(typed)
    if problem:
        await _send(chat_id, problem)
        return

    await _ask_return(db, user, chat_id, None, day, hhmm, price)


def _parse_price(typed: str) -> tuple[int | None, str | None]:
    """Yozilgan matndan narxni ajratadi; xato bo'lsa sababini qaytaradi."""
    digits = re.sub(r"\D", "", typed or "")
    if not digits:
        return None, "Narxni faqat raqam bilan yozing, masalan: 155000"
    value = int(digits)
    if value < _MIN_PRICE:
        return None, f"Narx kamida {_money(_MIN_PRICE)} so'm bo'lishi kerak."
    if value > 10_000_000:
        return None, "Narx juda katta ko'rinyapti — qaytadan yozing."
    return value, None


async def _accept_return_price(
    db: AsyncSession, user: User, chat_id, typed: str,
    day: int, hhmm: str, price: int,
) -> None:
    value, problem = _parse_price(typed)
    if problem:
        await _send(chat_id, problem)
        return
    await _confirm(db, user, chat_id, None, day, hhmm, price,
                   want_return=True, return_price=value)


async def handle_text(db: AsyncSession, chat_id, text: str, message: dict | None = None) -> bool:
    """Menyu tugmasi yoki narx javobimi? Ha bo'lsa — bajaradi va True qaytaradi."""
    from app.services import telegram_route_setup as rt

    replied = ((message or {}).get("reply_to_message") or {}).get("text") or ""
    price_ctx = _price_context(replied)           # e'lon qilishdagi borish narxi
    return_ctx = _return_price_context(replied)   # qaytish narxi
    route_ctx = rt.price_context(replied)         # yo'nalish belgilashdagi narx

    if (price_ctx is None and return_ctx is None and route_ctx is None
            and text not in (MENU_PUBLISH, MENU_MY, MENU_ROUTE)):
        return False

    user = await user_for_chat(db, chat_id)
    if user is None or await _approved_driver(db, user) is None:
        await _send(chat_id, (
            "Bu bo'lim tasdiqlangan haydovchilar uchun.\n\n"
            "Haydovchi bo'lmoqchi bo'lsangiz: uzsafar.uz"
        ))
        return True

    if route_ctx is not None:
        await rt.accept_price(db, chat_id, text, route_ctx)
    elif return_ctx is not None:
        await _accept_return_price(db, user, chat_id, text, *return_ctx)
    elif price_ctx is not None:
        await _accept_price(db, user, chat_id, text, *price_ctx)
    elif text == MENU_PUBLISH:
        await _ask_day(db, user, chat_id)
    elif text == MENU_ROUTE:
        await rt.show_route(db, user, chat_id)
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
        if data.startswith(RT):
            from app.services import telegram_route_setup
            await telegram_route_setup.handle_callback(db, user, chat_id, message_id, data)
        elif data == f"{PB}day":
            await _ask_day(db, user, chat_id, message_id)
        elif data == f"{PB}cancel":
            await _edit(chat_id, message_id, "Bekor qilindi.")
        elif parts[1] == "t":                       # pb:t:<day>
            await _ask_time(db, user, chat_id, message_id, int(parts[2]))
        elif parts[1] == "p":                       # pb:p:<day>:<hhmm>
            await _ask_price(db, user, chat_id, message_id, int(parts[2]), parts[3])
        elif parts[1] == "other":                   # pb:other:<day>:<hhmm>
            await _ask_price_text(chat_id, int(parts[2]), parts[3])
        elif parts[1] == "r":                       # pb:r:<day>:<hhmm>:<price>
            await _ask_return(
                db, user, chat_id, message_id,
                int(parts[2]), parts[3], int(parts[4]),
            )
        elif parts[1] == "c":                # pb:c:<day>:<hhmm>:<price>:<ret>:<rnarx>
            await _confirm(
                db, user, chat_id, message_id,
                day=int(parts[2]), hhmm=parts[3], price=int(parts[4]),
                want_return=parts[5] == "1",
                return_price=_opt_int(parts, 6),
            )
        elif parts[1] == "qp":                      # pb:qp:<day>:<hhmm>:<price>
            await _ask_return_price(db, user, chat_id, message_id,
                                    int(parts[2]), parts[3], int(parts[4]))
        elif parts[1] == "qo":                      # pb:qo:<day>:<hhmm>:<price>
            await _ask_return_price_text(chat_id, int(parts[2]), parts[3], int(parts[4]))
        elif parts[1] == "go":       # pb:go:<day>:<hhmm>:<price>:<ret>:<rnarx>[:1]
            await _publish(
                db, user, chat_id, message_id,
                day=int(parts[2]), hhmm=parts[3], price=int(parts[4]),
                want_return=parts[5] == "1",
                return_price=_opt_int(parts, 6),
                force=len(parts) > 7 and parts[7] == "1",
            )
        elif data == f"{MT}list":
            await _my_trips(db, user, chat_id, message_id)
        elif parts[1] == "v":                       # mt:v:<trip_id>
            await _trip_card(db, chat_id, message_id, parts[2])
        elif parts[1] == "s":                       # mt:s:<trip_id>
            await _ask_start(db, chat_id, message_id, parts[2])
        elif parts[1] == "ss":                      # mt:ss:<trip_id>
            await _do_start(db, user, chat_id, message_id, parts[2])
        elif parts[1] == "x":                       # mt:x:<trip_id>
            await _ask_cancel(db, user, chat_id, message_id, parts[2])
        elif parts[1] == "xx":                      # mt:xx:<trip_id>
            await _do_cancel(db, user, chat_id, message_id, parts[2])
        else:
            await _edit(chat_id, message_id, "Bu tugma endi ishlamaydi.")
    except (IndexError, ValueError):
        logger.warning("Telegram: tushunarsiz callback %r", data)
        await _edit(chat_id, message_id, "Bu tugma endi ishlamaydi.")
