import uuid as uuid_lib
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.review import Review
from app.models.booking import Booking
from app.models.driver import DriverProfile
from app.models.user import User
from app.models.admin import AdminAction
from app.models.enums import (
    BookingStatus, ReviewerType, AdminActionType, DriverStatus,
)
from app.schemas.review import ReviewCreate
from app.core.config import settings


def _load_options():
    return [
        selectinload(Review.reviewer),
        selectinload(Review.reviewee),
    ]


async def create_review(
    db: AsyncSession,
    booking_id: str,
    current_user: User,
    data: ReviewCreate,
) -> Review:
    # Bron mavjudmi?
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.trip))
        .where(Booking.id == uuid_lib.UUID(booking_id))
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Bron topilmadi")

    # Faqat tugallangan safarlar uchun baho berish mumkin
    if booking.status != BookingStatus.completed:
        raise HTTPException(status_code=400, detail="Faqat tugallangan safarlar uchun baho beriladi")

    is_passenger = booking.passenger_id == current_user.id
    is_driver = booking.trip.driver_id == current_user.id

    if not is_passenger and not is_driver:
        raise HTTPException(status_code=403, detail="Bu bron bilan bog'liq emassiz")

    # Kim kim haqida yozmoqda?
    if is_passenger:
        reviewer_type = ReviewerType.passenger
        reviewee_id = booking.trip.driver_id
    else:
        reviewer_type = ReviewerType.driver
        reviewee_id = booking.passenger_id

    # Allaqachon baho berganmi?
    existing = await db.execute(
        select(Review).where(
            Review.booking_id == booking.id,
            Review.reviewer_type == reviewer_type,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bu safar uchun baho allaqachon berilgan")

    deadline = datetime.utcnow() + timedelta(hours=settings.REVIEW_DEADLINE_HOURS)

    review = Review(
        booking_id=booking.id,
        reviewer_id=current_user.id,
        reviewee_id=reviewee_id,
        reviewer_type=reviewer_type,
        rating=data.rating,
        comment=data.comment,
        is_visible=False,
        review_deadline=deadline,
    )
    db.add(review)
    await db.flush()

    # Ikki tomon ham baho berdimi? → ikkalasini ham ko'rinadigan qil
    await _check_and_reveal(db, booking.id)

    await db.commit()
    await db.refresh(review)

    # Passenger bahosi ko'rinadigan bo'lsa → driver reytingini yangilash
    if reviewer_type == ReviewerType.passenger and review.is_visible:
        await _update_driver_rating(db, reviewee_id)

    await db.commit()

    result = await db.execute(
        select(Review).options(*_load_options()).where(Review.id == review.id)
    )
    return result.scalar_one()


async def _check_and_reveal(db: AsyncSession, booking_id: uuid_lib.UUID) -> None:
    """Ikki tomon ham baho bergan bo'lsa — ikkalasini ham ko'rsatish."""
    result = await db.execute(
        select(Review).where(Review.booking_id == booking_id)
    )
    reviews = result.scalars().all()

    types = {r.reviewer_type for r in reviews}
    if ReviewerType.passenger in types and ReviewerType.driver in types:
        for r in reviews:
            r.is_visible = True


async def _update_driver_rating(db: AsyncSession, driver_user_id: uuid_lib.UUID) -> None:
    """Haydovchi o'rtacha reytingini qayta hisoblash va tekshirish."""
    result = await db.execute(
        select(
            func.avg(Review.rating).label("avg"),
            func.count(Review.id).label("count"),
        ).where(
            Review.reviewee_id == driver_user_id,
            Review.reviewer_type == ReviewerType.passenger,
            Review.is_visible == True,
        )
    )
    row = result.one()
    avg_rating = float(row.avg or 0.0)
    count = int(row.count or 0)

    dp_result = await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == driver_user_id)
    )
    dp = dp_result.scalar_one_or_none()
    if not dp:
        return

    dp.rating_avg = round(avg_rating, 2)
    dp.rating_count = count

    # Reyting < 4.0 → ogohlantirish
    if avg_rating < settings.RATING_WARNING_THRESHOLD and count >= 3:
        dp.warning_count += 1

        # Reyting < 3.5 → bloklash
        if avg_rating < settings.RATING_BLOCK_THRESHOLD:
            user_result = await db.execute(
                select(User).where(User.id == driver_user_id)
            )
            driver_user = user_result.scalar_one_or_none()
            if driver_user and not driver_user.is_blocked:
                driver_user.is_blocked = True
                driver_user.block_reason = f"Reyting juda past: {avg_rating:.1f} (chegara: {settings.RATING_BLOCK_THRESHOLD})"

                db.add(AdminAction(
                    admin_id=driver_user_id,  # tizim tomonidan
                    action_type=AdminActionType.block_user,
                    target_user_id=driver_user_id,
                    reason=f"Avtomatik bloklash: reyting {avg_rating:.1f} < {settings.RATING_BLOCK_THRESHOLD}",
                ))


async def get_driver_reviews(db: AsyncSession, driver_user_id: str) -> dict:
    uid = uuid_lib.UUID(driver_user_id)

    dp_result = await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == uid)
    )
    dp = dp_result.scalar_one_or_none()
    if not dp:
        raise HTTPException(status_code=404, detail="Haydovchi topilmadi")

    result = await db.execute(
        select(Review)
        .options(*_load_options())
        .where(
            Review.reviewee_id == uid,
            Review.reviewer_type == ReviewerType.passenger,
            Review.is_visible == True,
        )
        .order_by(Review.created_at.desc())
    )
    reviews = result.scalars().all()

    return {
        "driver_id": uid,
        "rating_avg": dp.rating_avg,
        "rating_count": dp.rating_count,
        "total_trips": dp.total_trips,
        "reviews": reviews,
    }


async def get_my_given_reviews(db: AsyncSession, user: User) -> list[Review]:
    result = await db.execute(
        select(Review)
        .options(*_load_options())
        .where(Review.reviewer_id == user.id)
        .order_by(Review.created_at.desc())
    )
    return result.scalars().all()


async def reveal_expired_reviews(db: AsyncSession) -> int:
    """72 soat o'tgan, hali ko'rinmagan baholarni ochish — Celery task."""
    result = await db.execute(
        select(Review).where(
            Review.is_visible == False,
            Review.review_deadline < datetime.utcnow(),
        )
    )
    reviews = result.scalars().all()

    revealed_driver_ids = set()
    for review in reviews:
        review.is_visible = True
        if review.reviewer_type == ReviewerType.passenger:
            revealed_driver_ids.add(review.reviewee_id)

    await db.flush()

    # Ko'rinadigan bo'lgan passenger baholaridan driver reytingini yangilash
    for driver_id in revealed_driver_ids:
        await _update_driver_rating(db, driver_id)

    await db.commit()
    return len(reviews)
