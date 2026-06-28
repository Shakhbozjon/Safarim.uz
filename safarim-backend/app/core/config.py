from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Safarim.uz"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    # CORS — vergul bilan ajratilgan domenlar (prod: https://safarim.uz,https://www.safarim.uz)
    CORS_ORIGINS: str = "http://localhost:3000"

    # Rate limiting (Redis orqali)
    OTP_RATELIMIT_PHONE_PER_HOUR: int = 5    # bitta raqamga soatiga necha OTP
    OTP_RATELIMIT_IP_PER_HOUR: int = 15      # bitta IP dan soatiga necha OTP
    LOGIN_RATELIMIT_PER_15MIN: int = 10      # bitta IP dan 15 daqiqada necha login urinishi

    # Monitoring — Sentry (bo'sh bo'lsa o'chiq)
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # OTP
    OTP_EXPIRE_MINUTES: int = 5
    OTP_MAX_ATTEMPTS: int = 3

    # Pilot rejim — SMS'siz sinov: OTP javobda qaytariladi (faqat yopiq pilot uchun!)
    PILOT_MODE: bool = False

    # Guvohnoma rasmi OCR tekshiruvi (tesseract o'rnatilgan bo'lsa True qiling)
    LICENSE_OCR_ENABLED: bool = False

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET_DOCUMENTS: str = "documents"
    MINIO_BUCKET_PHOTOS: str = "photos"
    MINIO_SECURE: bool = False
    # Brauzer ko'radigan public MinIO manzili (bo'sh bo'lsa MINIO_ENDPOINT ishlatiladi).
    # Prod'da: server_ip:9000 yoki cdn.safarim.uz — presigned URL shu host uchun imzolanadi.
    MINIO_PUBLIC_ENDPOINT: str = ""
    MINIO_PUBLIC_SECURE: bool = False

    # SMS - Eskiz.uz
    ESKIZ_EMAIL: str = ""
    ESKIZ_PASSWORD: str = ""
    ESKIZ_BASE_URL: str = "https://notify.eskiz.uz/api"

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ADMIN_CHAT_ID: str = ""  # OTP loglar keladigan chat ID

    # Click
    CLICK_SERVICE_ID: str = ""
    CLICK_MERCHANT_ID: str = ""
    CLICK_SECRET_KEY: str = ""

    # Payme
    PAYME_ID: str = ""
    PAYME_KEY: str = ""

    # Haydovchi hamyoni
    WALLET_MIN_BALANCE: int = -50_000    # Bu miqdordan past tushsa haydovchi bloklanadi
    WALLET_TOPUP_MIN:   int = 10_000     # Minimal to'ldirish miqdori

    # Komissiya
    COMMISSION_LOW_RATE: float = 0.02
    COMMISSION_HIGH_RATE: float = 0.05
    COMMISSION_THRESHOLD: int = 200_000

    # Reyting chegaralari
    RATING_WARNING_THRESHOLD: float = 4.0
    RATING_BLOCK_THRESHOLD: float = 3.5

    # Baho muddati (soat)
    REVIEW_DEADLINE_HOURS: int = 72

    # ── Ikki tomonlama safar tasdiqi ────────────────────────────────────────
    CONFIRMATION_GRACE_HOURS: int = 3       # jo'nashdan keyin shu soatdan so'ng tasdiq so'raladi
    CONFIRMATION_WINDOW_HOURS: int = 48     # tasdiq so'rovidan keyin avtomatik hal qilinguncha
    # Soxta belgilash jarimasi
    FAKE_CONFIRMATION_BLOCK_THRESHOLD: int = 3  # shuncha soxtalikda jarima pauzasi
    FAKE_CONFIRMATION_PAUSE_DAYS: int = 5       # jarima pauzasi davomiyligi
    FAKE_CONFIRMATION_RESET_MONTHS: int = 6     # hisoblagich shu oydan keyin nolga tushadi (yangi loyiha — yumshoq)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()


# ─── Prod xavfsizlik tekshiruvi ──────────────────────────────────────────────
_INSECURE_DEFAULTS = {"change-me-in-production"}


def validate_production_security() -> None:
    """Prod (DEBUG=False) da xavfsiz bo'lmagan default qiymatlar bilan ishga
    tushishni bloklaydi. Dev (DEBUG=True) da hech narsa qilmaydi."""
    if settings.DEBUG:
        return
    problems = []
    if settings.SECRET_KEY in _INSECURE_DEFAULTS:
        problems.append("SECRET_KEY")
    if settings.JWT_SECRET_KEY in _INSECURE_DEFAULTS:
        problems.append("JWT_SECRET_KEY")
    if "*" in settings.cors_origins_list:
        problems.append("CORS_ORIGINS (\"*\" prod uchun xavfli)")
    if problems:
        raise RuntimeError(
            "Xavfsiz bo'lmagan konfiguratsiya bilan prod'da ishga tushib bo'lmaydi: "
            + ", ".join(problems)
            + ". .env da to'g'ri qiymatlar bering "
            "(masalan: python -c \"import secrets; print(secrets.token_urlsafe(48))\")."
        )
