"""Vaqt yordamchilari.

Safarlarning `departure_date`/`departure_time` maydonlari mahalliy (Toshkent)
vaqtda saqlanadi — ular bilan solishtirishda DOIM shu helperdan foydalaning.
DB timestamp'lari (created_at, confirmation_requested_at, ...) UTC'da qoladi.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

TASHKENT = ZoneInfo("Asia/Tashkent")

MONTHS_UZ = (
    "yanvar", "fevral", "mart", "aprel", "may", "iyun",
    "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
)


def now_tashkent_naive() -> datetime:
    """Joriy Toshkent vaqti (naive) — departure_dt bilan solishtirish uchun."""
    return datetime.now(TASHKENT).replace(tzinfo=None)


def format_day_uz(d: date) -> str:
    """Sanani odam o'qiydigan qilib: «Bugun, 19-sentabr», «21-sentabr».

    Nisbiy yorliq («Bugun») bilan birga ANIQ SANA ham qoldiriladi. Sabab:
    Telegram guruhidagi e'lon posti abadiy turadi va faqat safar holati
    o'zgarganda qayta yoziladi. Yarim tun o'tib ketsa, «Ertaga» degan post
    o'z-o'zidan yangilanmaydi — yonida sana turmasa, odamni adashtirardi.

    Bugun/ertaga Toshkent kuni bo'yicha aniqlanadi (server UTC'da ishlaydi).
    """
    label = f"{d.day}-{MONTHS_UZ[d.month - 1]}"
    delta = (d - now_tashkent_naive().date()).days
    if delta == 0:
        return f"Bugun, {label}"
    if delta == 1:
        return f"Ertaga, {label}"
    return label
