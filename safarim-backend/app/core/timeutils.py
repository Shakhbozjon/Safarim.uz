"""Vaqt yordamchilari.

Safarlarning `departure_date`/`departure_time` maydonlari mahalliy (Toshkent)
vaqtda saqlanadi — ular bilan solishtirishda DOIM shu helperdan foydalaning.
DB timestamp'lari (created_at, confirmation_requested_at, ...) UTC'da qoladi.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

TASHKENT = ZoneInfo("Asia/Tashkent")


def now_tashkent_naive() -> datetime:
    """Joriy Toshkent vaqti (naive) — departure_dt bilan solishtirish uchun."""
    return datetime.now(TASHKENT).replace(tzinfo=None)
