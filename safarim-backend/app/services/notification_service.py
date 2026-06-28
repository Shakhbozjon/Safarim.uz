"""
Notification service — in-app bildirishnomalar yaratish va o'qish.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.models.notification import Notification
from app.models.enums import NotificationChannel, NotificationRefType


# ─── Yaratish ─────────────────────────────────────────────────────────────────

async def create(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    title: str,
    body: str,
    ref_type: NotificationRefType | None = None,
    ref_id: uuid.UUID | None = None,
) -> Notification:
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
    # flush qilmaymiz — caller commit qiladi
    return notif


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
