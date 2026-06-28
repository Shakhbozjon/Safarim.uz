"""Safar hayot-sikli tasklari.

`expire_old_trips` — vaqti o'tgan, yo'lovchi yig'ilmagan safarlarni avtomatik
`expired` holatiga o'tkazadi (jazosiz arxiv). Asosiy mantiq
`trip_service.expire_due_trips` da — bu yerda faqat celery beat ulagichi
(har 20 daqiqada). Eslatma: dashboard ham `get_my_trips` orqali lazy expiry
qiladi, shuning uchun Celery ishlamasa ham haydovchi paneli o'zini tozalaydi.
"""
import asyncio
import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.trip_tasks.expire_old_trips")
def expire_old_trips() -> dict:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


async def _run() -> dict:
    from app.db.session import AsyncSessionLocal
    from app.services.trip_service import expire_due_trips

    async with AsyncSessionLocal() as db:
        expired = await expire_due_trips(db)

    logger.info("expire_old_trips: %s ta safar expired qilindi", expired)
    return {"expired": expired}


@celery_app.task(name="app.tasks.trip_tasks.process_confirmations")
def process_confirmations() -> dict:
    """Safar tasdiqi oqimi: oyna ochish + 48 soat o'tganlarni avtomatik hal qilish."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_confirmations())
    finally:
        loop.close()


async def _run_confirmations() -> dict:
    from app.db.session import AsyncSessionLocal
    from app.services.booking_service import request_due_confirmations, resolve_due_confirmations

    async with AsyncSessionLocal() as db:
        opened = await request_due_confirmations(db)
    async with AsyncSessionLocal() as db:
        resolved = await resolve_due_confirmations(db)

    logger.info("process_confirmations: %s oyna ochildi, %s avtomatik hal qilindi", opened, resolved)
    return {"opened": opened, "resolved": resolved}
