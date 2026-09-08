"""Xatolarni kuzatish (Sentry).

Nega alohida modul: ilgari Sentry faqat `main.py` da, ya'ni **API jarayonida**
yoqilardi. Celery worker'i esa uni umuman ishga tushirmasdi — natijada
`expire_old_trips` har 20 daqiqada xato bilan tugib turgan (2026-09-08),
lekin bu hech qayerda ko'rinmagan, faqat `docker compose logs` ichida
yotgan. Endi ikkala jarayon ham shu bitta funksiyani chaqiradi.

`SENTRY_DSN` bo'sh bo'lsa hech narsa qilinmaydi — lokal ishlashga xalaqit
bermaydi.
"""
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def init_sentry(component: str) -> bool:
    """Sentry'ni yoqadi. `component` — "api" yoki "worker" (xatolar ajratilsin).

    Qaytaradi: yoqilgan bo'lsa True.
    """
    if not settings.SENTRY_DSN:
        return False

    try:
        import sentry_sdk
    except ImportError:  # kutubxona o'rnatilmagan bo'lsa jarayon to'xtamasin
        logger.warning("sentry-sdk o'rnatilmagan — xato kuzatuvi o'chiq")
        return False

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        environment="development" if settings.DEBUG else "production",
        # ⚠️ Shaxsiy ma'lumot yuborilmasin: bu saytda telefon raqamlar bor va
        # ular xato hisobotiga tushib qolishi kerak emas.
        send_default_pii=False,
        max_request_body_size="never",
    )
    sentry_sdk.set_tag("component", component)
    logger.info("Sentry yoqildi (%s)", component)
    return True
