"""
Parolni tiklash: kod foydalanuvchining o'z Telegramiga boradi, so'ng
tizimga kirmasdan yangi parol o'rnatiladi.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import OtpPurpose
from app.models.otp import OtpCode
from app.models.user import User
from app.services import telegram_service

API = "/api/v1/auth"


@pytest.fixture
def tg_sent(monkeypatch) -> list[dict]:
    """Telegramga ketgan xabarlarni ushlab qoladi (tarmoqqa chiqmasdan)."""
    calls: list[dict] = []

    async def _fake_call(method: str, payload: dict):
        calls.append({"method": method, **payload})
        return {"ok": True}

    monkeypatch.setattr(telegram_service, "_call", _fake_call)
    return calls


async def _otp_for(db: AsyncSession, phone: str) -> str:
    otp = (await db.execute(
        select(OtpCode)
        .where(
            OtpCode.phone == phone,
            OtpCode.purpose == OtpPurpose.password_reset,
            OtpCode.is_used == False,  # noqa: E712
        )
        .order_by(OtpCode.created_at.desc())
    )).scalars().first()
    assert otp is not None, "OTP yaratilmadi"
    return otp.code


# ─── Kod yetkazish ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_otp_goes_to_users_own_telegram(
    client: AsyncClient, db: AsyncSession, user: User, tg_sent: list
):
    """Telegrami ulangan bo'lsa kod o'sha chatga boradi, adminga emas."""
    user.telegram_chat_id = "777001"
    await db.commit()

    resp = await client.post(
        f"{API}/send-otp", json={"phone": user.phone, "purpose": "password_reset"}
    )
    assert resp.status_code == 200
    assert resp.json()["channel"] == "telegram"

    code = await _otp_for(db, user.phone)
    assert tg_sent[-1]["chat_id"] == "777001"
    assert code in tg_sent[-1]["text"]


@pytest.mark.asyncio
async def test_unknown_phone_rejected(client: AsyncClient):
    """Ro'yxatdan o'tmagan raqamga parol tiklash kodi yuborilmaydi."""
    resp = await client.post(
        f"{API}/send-otp", json={"phone": "+998909998877", "purpose": "password_reset"}
    )
    assert resp.status_code == 404


# ─── Tiklash ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reset_password_success(
    client: AsyncClient, db: AsyncSession, user: User, tg_sent: list
):
    """To'g'ri kod bilan yangi parol o'rnatiladi va darrov kirish beriladi."""
    user.telegram_chat_id = "777002"
    await db.commit()

    await client.post(
        f"{API}/send-otp", json={"phone": user.phone, "purpose": "password_reset"}
    )
    code = await _otp_for(db, user.phone)

    resp = await client.post(f"{API}/reset-password", json={
        "phone": user.phone, "otp_code": code, "new_password": "YangiParol1",
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]

    # Yangi parol bilan kirish ishlaydi
    login = await client.post(
        f"{API}/login", json={"phone": user.phone, "password": "YangiParol1"}
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_wrong_code(
    client: AsyncClient, db: AsyncSession, user: User, tg_sent: list
):
    """Noto'g'ri kod bilan parol o'zgarmaydi."""
    old_hash = user.password_hash
    await client.post(
        f"{API}/send-otp", json={"phone": user.phone, "purpose": "password_reset"}
    )

    resp = await client.post(f"{API}/reset-password", json={
        "phone": user.phone, "otp_code": "000000", "new_password": "YangiParol1",
    })
    assert resp.status_code == 400

    await db.refresh(user)
    assert user.password_hash == old_hash


@pytest.mark.asyncio
async def test_reset_password_needs_code(client: AsyncClient, user: User):
    """Kod so'ralmagan bo'lsa tiklab bo'lmaydi."""
    resp = await client.post(f"{API}/reset-password", json={
        "phone": user.phone, "otp_code": "123456", "new_password": "YangiParol1",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_short_password(client: AsyncClient, user: User):
    """Qisqa parol qabul qilinmaydi."""
    resp = await client.post(f"{API}/reset-password", json={
        "phone": user.phone, "otp_code": "123456", "new_password": "123",
    })
    assert resp.status_code == 422
