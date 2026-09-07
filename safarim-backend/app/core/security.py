from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


# `ver` — foydalanuvchining `token_version` i. Parol o'zgarganda (yoki hisob
# o'chirilganda) u bittaga oshadi va shu paytgacha berilgan BARCHA tokenlar
# yaroqsiz bo'ladi. Busiz: parolni almashtirish o'g'irlangan sessiyani
# to'xtatmasdi — refresh token yana 30 kun ishlayverardi.
def create_access_token(subject: str, version: int = 0) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire, "type": "access", "ver": version}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, version: int = 0) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": subject, "exp": expire, "type": "refresh", "ver": version}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


def calculate_commission(price: int) -> tuple[float, int]:
    # Bepul davr — komissiya umuman olinmaydi
    if settings.COMMISSION_FREE_MODE:
        return 0.0, 0
    if price <= settings.COMMISSION_THRESHOLD:
        rate = settings.COMMISSION_LOW_RATE
    else:
        rate = settings.COMMISSION_HIGH_RATE
    return rate, int(price * rate)
