"""Ochiq (autentifikatsiyasiz) sozlamalar.

Bosh sahifa komissiya raqamini shu yerdan oladi. Aks holda raqam frontendда
qotib qolardi: `.env.production` da `COMMISSION_FREE_MODE` o'chirilganda sayt
hamon «komissiya yo'q» deb turaverardi.

Bu yerga faqat sir bo'lmagan, hamma ko'rishi mumkin bo'lgan qiymatlar
qo'shilsin.
"""
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("", summary="Ochiq sozlamalar")
async def public_config() -> dict:
    return {"commission_free": settings.COMMISSION_FREE_MODE}
