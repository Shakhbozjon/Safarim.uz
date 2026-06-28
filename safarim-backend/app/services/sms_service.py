import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class EskizSMSService:

    async def _get_token(self) -> str:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{settings.ESKIZ_BASE_URL}/auth/login",
                data={"email": settings.ESKIZ_EMAIL, "password": settings.ESKIZ_PASSWORD},
                timeout=10,
            )
            r.raise_for_status()
            return r.json()["data"]["token"]

    async def _send_via_telegram(self, phone: str, message: str) -> bool:
        """Telegram bot orqali OTP yuborish (bepul fallback)."""
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_ADMIN_CHAT_ID:
            return False
        try:
            text = f"📱 <b>OTP so'rovi</b>\nTelefon: <code>{phone}</code>\n\n{message}"
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": settings.TELEGRAM_ADMIN_CHAT_ID,
                        "text": text,
                        "parse_mode": "HTML",
                    },
                    timeout=10,
                )
                return r.status_code == 200
        except Exception as e:
            logger.error("TELEGRAM SMS ERROR: %s", e)
            return False

    async def notify_admin(self, message: str) -> bool:
        """Admin chatiga to'g'ridan-to'g'ri xabar yuborish (OTP emas)."""
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_ADMIN_CHAT_ID:
            logger.info("ADMIN NOTIFY (no Telegram): %s", message)
            return False
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": settings.TELEGRAM_ADMIN_CHAT_ID,
                        "text": message,
                        "parse_mode": "HTML",
                    },
                    timeout=10,
                )
                return r.status_code == 200
        except Exception as e:
            logger.error("ADMIN NOTIFY ERROR: %s", e)
            return False

    async def send(self, phone: str, message: str) -> bool:
        # Dev rejim: faqat konsolga chiqar
        if settings.DEBUG or not settings.ESKIZ_EMAIL:
            logger.info("SMS DEV | %s | %s", phone, message)
            # Telegram ham ulangan bo'lsa, u orqali ham yubor
            await self._send_via_telegram(phone, message)
            return True

        # Production: avval Eskiz, xato bo'lsa Telegram fallback
        try:
            token = await self._get_token()
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"{settings.ESKIZ_BASE_URL}/message/sms/send",
                    json={
                        "mobile_phone": phone.replace("+", ""),
                        "message": message,
                        "from": "4546",
                    },
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
                if r.status_code == 200:
                    return True
        except Exception as e:
            logger.error("SMS ERROR: %s", e)

        # Eskiz ishlamasa → Telegram fallback
        return await self._send_via_telegram(phone, message)


sms_service = EskizSMSService()
