"""
Notification service — in-app bildirishnomalar yaratish va o'qish.
"""
from __future__ import annotations
import logging
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.models.notification import Notification
from app.models.enums import NotificationChannel, NotificationRefType

logger = logging.getLogger(__name__)


# ─── Yaratish ─────────────────────────────────────────────────────────────────

async def create(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    title: str,
    body: str,
    ref_type: NotificationRefType | None = None,
    ref_id: uuid.UUID | None = None,
    tg_buttons: list[list[dict]] | None = None,
) -> Notification:
    """Ilova ichida bildirishnoma yaratadi va uni Telegramga yuborishni navbatga qo'yadi.

    Telegram xabari Celery orqali, alohida yuboriladi: Telegram API sekin javob
    bersa band qilish so'rovi sekinlashmasin. `tg_buttons` berilsa (masalan safar
    tasdig'i) xabarga inline tugmalar qo'shiladi.
    """
    notif = Notification(
        user_id=user_id,
        channel=NotificationChannel.inapp,
        title=title,
        body=body,
        ref_type=ref_type,
        ref_id=ref_id,
        is_sent=True,
        sent_at=datetime.utcnow(),
    )
    db.add(notif)
    await db.flush()   # id kerak — Celery taski shu bo'yicha topadi

    _queue_telegram(notif.id, tg_buttons)
    return notif


def _queue_telegram(notification_id: uuid.UUID, buttons: list[list[dict]] | None) -> None:
    """Telegram xabarini fon rejimida yuborishni boshlaydi.

    Celery orqali EMAS: Redis o'chib qolsa `apply_async` ulanishni kutib
    daqiqalab osilib qoladi va u bilan birga band qilish so'rovi ham osiladi
    (o'lchandi: ~109 soniya). Bildirishnoma tufayli asosiy oqim to'xtashi
    mumkin emas, shuning uchun yuborish shu jarayonning o'zida, alohida
    vazifa sifatida ketadi.

    Vazifa ichida kichik kutish bor — caller hali commit qilmagan bo'lishi
    mumkin. Tranzaksiya orqaga qaytsa, bildirishnoma topilmaydi va vazifa
    jim to'xtaydi.
    """
    try:
        import asyncio
        from app.services import telegram_service

        async def _run() -> None:
            try:
                await asyncio.sleep(2)          # commit tushishini kutamiz
                await telegram_service.deliver_notification(str(notification_id), buttons)
            except Exception as exc:
                logger.warning("Telegram xabari yuborilmadi: %s", exc)

        task = asyncio.create_task(_run())
        _PENDING_SENDS.add(task)                # yig'uvchi o'chirib yubormasin
        task.add_done_callback(_PENDING_SENDS.discard)
    except RuntimeError:
        # Ishlayotgan event loop yo'q (masalan skript ichidan chaqirilgan) —
        # bildirishnoma ilova ichida baribir yaratilgan, shu yetarli.
        logger.debug("Event loop yo'q — Telegram xabari o'tkazib yuborildi")


# asyncio faqat kuchsiz havola saqlaydi: vazifa tugamasdan yig'ilib ketmasin
_PENDING_SENDS: set = set()


# ─── O'qish ───────────────────────────────────────────────────────────────────

async def get_my_notifications(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 30,
    offset: int = 0,
) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def get_unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    count = await db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
    )
    return count or 0


async def mark_read(
    db: AsyncSession,
    notif_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Bitta bildirishnomani o'qilgan deb belgilash. False → topilmadi."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.user_id == user_id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        return False
    if not notif.is_read:
        notif.is_read = True
        notif.read_at = datetime.utcnow()
        await db.commit()
    return True


async def mark_all_read(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Hammani o'qilgan belgilash. O'zgartirilgan qatorlar sonini qaytaradi."""
    result = await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
        .values(is_read=True, read_at=datetime.utcnow())
        .returning(Notification.id)
    )
    ids = result.fetchall()
    await db.commit()
    return len(ids)
