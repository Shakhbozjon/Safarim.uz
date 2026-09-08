"""Celery vazifalarini asyncio bilan xavfsiz bajarish.

⚠️ **Jonli saytda topilgan nosozlik (2026-09-08).** Har bir vazifa o'ziga
yangi event loop ochardi, lekin baza ulanishlari umumiy hovuzda (pool)
qolardi. Ulanish birinchi loop'ga bog'langan bo'ladi; keyingi vazifa uni
boshqa loop'da olganda asyncpg quyidagini beradi:

    InterfaceError: cannot perform operation: another operation is in progress

Natijada `expire_old_trips` va `process_confirmations` **umuman
bajarilmasdi**: o'tgan safarlar yopilmas, safar tasdig'i so'ralmas edi.

Ikkita qoida shu yerda birga bajariladi:
  1. Vazifa tugagach hovuzdagi ulanishlar yopiladi (`engine.dispose`) —
     hech bir ulanish keyingi loop'ga o'tmaydi;
  2. Telegram xabarlari fon vazifasi sifatida yuboriladi
     (`notification_service._queue_telegram`), shuning uchun loop yopilishidan
     oldin ular kutiladi — aks holda xabarlar yo'lda uzilib qolardi.
"""
import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Telegram xabarlari yuborilishini shuncha kutamiz (vazifa cheksiz osilmasin)
PENDING_TIMEOUT = 20.0


def run_task(coro_factory: Callable[[], Awaitable[T]]) -> T:
    """Korutinani o'z event loop'ida bajaradi va ulanishlarni tozalab ketadi."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run(coro_factory))
    finally:
        try:
            loop.close()
        finally:
            asyncio.set_event_loop(None)


async def _run(coro_factory: Callable[[], Awaitable[T]]) -> T:
    from app.db.session import engine
    from app.services import notification_service

    try:
        return await coro_factory()
    finally:
        try:
            await notification_service.flush_pending(PENDING_TIMEOUT)
        except Exception as exc:  # xabar yuborilmasa ham vazifa tugashi kerak
            logger.warning("Fon xabarlarini kutishda xato: %s", exc)
        try:
            # Shu loop'da ochilgan ulanishlar shu yerda yopiladi
            await engine.dispose()
        except Exception as exc:
            # Vazifa bajarilib bo'lgan — ulanishni yopishdagi nosozlik uning
            # natijasini yo'qotmasligi kerak
            logger.warning("Ulanishlarni yopishda xato: %s", exc)
