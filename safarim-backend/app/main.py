import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings, validate_production_security
from app.api.v1.router import api_router

logger = logging.getLogger(__name__)

# Prod'da xavfsiz bo'lmagan default qiymatlar bilan ishga tushishni bloklaydi
validate_production_security()

# Sentry — xato kuzatuvi (DSN berilgan bo'lsa)
if settings.SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        environment="production" if not settings.DEBUG else "development",
    )

# Prod'da API hujjatlari yopiladi: ochiq Swagger butun endpoint xaritasini,
# sxemalarni va maydon nomlarini begonaga tayyor holda beradi.
_docs_open = settings.DEBUG
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs" if _docs_open else None,
    redoc_url="/api/redoc" if _docs_open else None,
    openapi_url="/api/openapi.json" if _docs_open else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Xavfsizlik sarlavhalari ─────────────────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # HSTS faqat prod'da (HTTPS ortida)
    if not settings.DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ─── Noto'g'ri ID → 500 emas, 400 ────────────────────────────────────────────
# Manzildagi ID lar ko'p joyda `uuid.UUID(...)` bilan o'giriladi. Xato yozilgan
# ID (masalan havolani qo'lda tahrirlash) `ValueError` berib, javob 500 bo'lardi:
# bu foydalanuvchiga "serverda nosozlik" deb ko'rinadi va xato kuzatuvini
# keraksiz yozuvlar bilan to'ldiradi. Faqat UUID xatosini 400 ga aylantiramiz,
# qolgan `ValueError` esa haqiqiy bug — o'sha holicha 500 bo'lib qoladi.
@app.exception_handler(ValueError)
async def invalid_uuid_handler(request: Request, exc: ValueError):
    text = str(exc)
    if "badly formed hexadecimal UUID string" in text or "is not a valid UUID" in text:
        return JSONResponse(status_code=400, content={"detail": "Noto'g'ri ID"})
    logger.exception("Kutilmagan ValueError: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Serverda xatolik"})


app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
