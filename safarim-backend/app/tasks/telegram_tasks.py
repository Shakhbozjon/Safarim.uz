"""Telegram guruhlari bilan bog'liq fon vazifalari.

`purge_feed_replies` — guruhdagi «botdan bering» javoblarini vaqti kelganda
o'chiradi (`telegram_feed_nudge`). Har 2 daqiqada celery beat chaqiradi.
"""
import logging

from app.tasks.celery_app import celery_app
from app.tasks.runner import run_task

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.telegram_tasks.purge_feed_replies")
def purge_feed_replies() -> dict:
    return run_task(_run_purge)


async def _run_purge() -> dict:
    import redis.asyncio as aioredis

    from app.core.config import settings
    from app.services.telegram_feed_nudge import purge_due_replies

    # Umumiy `get_redis()` mijozi emas: u boshqa event loop'ga bog'lanib qolardi
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        deleted = await purge_due_replies(client)
    finally:
        await client.aclose()
    if deleted:
        logger.info("purge_feed_replies: guruhdan %s ta javob o'chirildi", deleted)
    return {"deleted": deleted}
