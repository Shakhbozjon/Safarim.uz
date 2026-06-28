import uuid as uuid_lib
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.message import Message
from app.models.booking import Booking
from app.models.trip import Trip
from app.models.user import User
from app.models.enums import BookingStatus


def _load_options():
    return [selectinload(Message.sender)]


async def _get_booking_and_check_access(
    db: AsyncSession, booking_id: str, user: User
) -> tuple[Booking, str]:
    """
    Bronni topadi va foydalanuvchi haydovchi yoki yo'lovchiligini tekshiradi.
    Returns: (booking, role) — role: 'driver' yoki 'passenger'
    """
    try:
        uid = uuid_lib.UUID(booking_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Noto'g'ri ID")

    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.trip))
        .where(Booking.id == uid)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Bron topilmadi")

    is_passenger = booking.passenger_id == user.id
    is_driver = booking.trip.driver_id == user.id

    if not is_passenger and not is_driver:
        raise HTTPException(status_code=403, detail="Bu bron bilan bog'liq emassiz")

    # Faqat tasdiqlangan yoki tugallangan bronlarda chat ochiq
    allowed = [BookingStatus.confirmed, BookingStatus.completed]
    if booking.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Chat faqat tasdiqlangan bronlar uchun ochiq. Bron tasdiqlanguncha kuting.",
        )

    role = "passenger" if is_passenger else "driver"
    return booking, role


async def send_message(
    db: AsyncSession,
    booking_id: str,
    user: User,
    content: str,
) -> Message:
    booking, _ = await _get_booking_and_check_access(db, booking_id, user)

    if not content.strip():
        raise HTTPException(status_code=400, detail="Xabar bo'sh bo'lishi mumkin emas")
    if len(content) > 1000:
        raise HTTPException(status_code=400, detail="Xabar 1000 ta belgidan oshmasligi kerak")

    message = Message(
        booking_id=booking.id,
        sender_id=user.id,
        content=content.strip(),
    )
    db.add(message)
    await db.commit()

    result = await db.execute(
        select(Message).options(*_load_options()).where(Message.id == message.id)
    )
    return result.scalar_one()


async def get_chat_history(
    db: AsyncSession,
    booking_id: str,
    user: User,
    limit: int = 50,
    before_id: str | None = None,
) -> list[Message]:
    await _get_booking_and_check_access(db, booking_id, user)

    uid = uuid_lib.UUID(booking_id)
    query = (
        select(Message)
        .options(*_load_options())
        .where(Message.booking_id == uid)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )

    # Pagination: before_id dan oldingi xabarlar
    if before_id:
        try:
            before_uid = uuid_lib.UUID(before_id)
            before_result = await db.execute(
                select(Message.created_at).where(Message.id == before_uid)
            )
            before_time = before_result.scalar_one_or_none()
            if before_time:
                query = query.where(Message.created_at < before_time)
        except ValueError:
            pass

    result = await db.execute(query)
    messages = result.scalars().all()
    return list(reversed(messages))  # Eskidan yangiga tartib


async def mark_as_read(
    db: AsyncSession,
    booking_id: str,
    user: User,
) -> int:
    """Foydalanuvchiga yuborilgan o'qilmagan xabarlarni o'qilgan deb belgilash."""
    await _get_booking_and_check_access(db, booking_id, user)

    uid = uuid_lib.UUID(booking_id)
    result = await db.execute(
        select(Message).where(
            Message.booking_id == uid,
            Message.sender_id != user.id,  # boshqa tomoning xabarlari
            Message.is_read == False,
        )
    )
    messages = result.scalars().all()

    now = datetime.utcnow()
    for msg in messages:
        msg.is_read = True
        msg.read_at = now

    await db.commit()
    return len(messages)


async def get_unread_count(db: AsyncSession, user: User) -> list[dict]:
    """Foydalanuvchining barcha bronlarida o'qilmagan xabarlar soni."""
    from sqlalchemy import func

    result = await db.execute(
        select(
            Message.booking_id,
            func.count(Message.id).label("unread"),
        )
        .join(Booking, Booking.id == Message.booking_id)
        .where(
            Message.is_read == False,
            Message.sender_id != user.id,
        )
        .group_by(Message.booking_id)
    )

    return [
        {"booking_id": row.booking_id, "unread_count": row.unread}
        for row in result.all()
    ]
