import asyncio
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.notification_tasks.send_sms")
def send_sms(phone: str, message: str) -> dict:
    from app.services.sms_service import sms_service
    return asyncio.get_event_loop().run_until_complete(
        sms_service.send(phone, message)
    )


@celery_app.task(name="app.tasks.notification_tasks.send_telegram")
def send_telegram(chat_id: str, message: str) -> dict:
    # Sprint 7 da implementatsiya qilinadi
    return {"status": "queued", "chat_id": chat_id}


@celery_app.task(name="app.tasks.notification_tasks.send_email")
def send_email(to: str, subject: str, body: str) -> dict:
    # Sprint 7 da implementatsiya qilinadi
    return {"status": "queued", "to": to}


@celery_app.task(name="app.tasks.notification_tasks.check_review_deadlines")
def check_review_deadlines() -> dict:
    """
    Har soatda ishga tushadi.
    72 soat o'tgan, hali ko'rinmagan baholarni ochadi
    va haydovchi reytingini yangilaydi.
    """
    async def _run():
        from app.db.session import AsyncSessionLocal
        from app.services.review_service import reveal_expired_reviews
        async with AsyncSessionLocal() as db:
            count = await reveal_expired_reviews(db)
            return count

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        count = loop.run_until_complete(_run())
        return {"revealed": count}
    finally:
        loop.close()


@celery_app.task(name="app.tasks.notification_tasks.notify_booking_created")
def notify_booking_created(booking_id: str) -> dict:
    """
    Joy band qilinganda:
    - Haydovchiga SMS: "Yangi bron: ..."
    - Yo'lovchiga SMS: "Broningiz tasdiqlandi: ..."
    Sprint 7 da to'liq implementatsiya.
    """
    return {"status": "queued", "booking_id": booking_id}


@celery_app.task(name="app.tasks.notification_tasks.notify_booking_cancelled")
def notify_booking_cancelled(booking_id: str, cancelled_by: str) -> dict:
    """Bekor qilinganda ikki tomonga SMS."""
    return {"status": "queued", "booking_id": booking_id}
