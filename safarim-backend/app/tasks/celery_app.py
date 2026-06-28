from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "safarim",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.notification_tasks", "app.tasks.trip_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tashkent",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "check-review-deadlines": {
        "task": "app.tasks.notification_tasks.check_review_deadlines",
        "schedule": 3600.0,  # har soatda
    },
    "expire-old-trips": {
        "task": "app.tasks.trip_tasks.expire_old_trips",
        "schedule": 1200.0,  # har 20 daqiqada
    },
    "process-confirmations": {
        "task": "app.tasks.trip_tasks.process_confirmations",
        "schedule": 1200.0,  # har 20 daqiqada — tasdiq oynalari + avtomatik hal
    },
}
