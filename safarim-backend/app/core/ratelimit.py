"""Redis asosidagi oddiy rate limiter (sliding-bo'lmagan, fixed-window).

Auth endpointlarini (OTP yuborish, login) brute-force va SMS spam'dan himoya qiladi.
Redis tushib qolsa — fail-open (xizmat to'xtamasin, lekin limit ishlamaydi).
"""
import logging

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)


def _client_ip(request: Request) -> str:
    # Nginx orqasida bo'lsa X-Forwarded-For dagi birinchi IP
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _hit(bucket: str, limit: int, window_sec: int) -> None:
    """Bittagina urinishni hisoblaydi; limitdan oshsa 429 ko'taradi."""
    r = get_redis()
    key = f"rl:{bucket}"
    try:
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, window_sec)
    except Exception as exc:  # Redis bilan muammo — fail-open
        logger.warning("Rate limiter Redis xatosi (%s): %s", bucket, exc)
        return
    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Juda ko'p urinish. Iltimos, birozdan keyin qayta urinib ko'ring.",
        )


async def limit_send_otp(request: Request, phone: str) -> None:
    ip = _client_ip(request)
    await _hit(f"otp:ip:{ip}", settings.OTP_RATELIMIT_IP_PER_HOUR, 3600)
    await _hit(f"otp:phone:{phone}", settings.OTP_RATELIMIT_PHONE_PER_HOUR, 3600)


async def limit_login(request: Request) -> None:
    ip = _client_ip(request)
    await _hit(f"login:ip:{ip}", settings.LOGIN_RATELIMIT_PER_15MIN, 900)
