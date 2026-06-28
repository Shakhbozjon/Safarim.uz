"""
Auth API testlari: OTP, /me, token.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from tests.conftest import auth_headers


# ─── /me ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_me_no_token(client: AsyncClient):
    """/me — token yo'q → 403."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_me_invalid_token(client: AsyncClient):
    """/me — noto'g'ri token → 401/403."""
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer bu-token-yolg'on"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_returns_user(client: AsyncClient, user: User):
    """/me — to'g'ri token → foydalanuvchi ma'lumoti."""
    resp = await client.get("/api/v1/auth/me", headers=auth_headers(user))
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(user.id)
    assert data["phone"] == user.phone
    assert data["full_name"] == user.full_name
    assert data["is_admin"] is False
    assert data["is_driver"] is False


@pytest.mark.asyncio
async def test_me_admin_flag(client: AsyncClient, admin_user: User):
    """Admin user — is_admin True ko'rinadi."""
    resp = await client.get("/api/v1/auth/me", headers=auth_headers(admin_user))
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_admin"] is True
    assert data["admin_role"] == "super_admin"


@pytest.mark.asyncio
async def test_me_driver_flag(client: AsyncClient, driver_user: tuple):
    """Haydovchi — is_driver True ko'rinadi."""
    u, _dp = driver_user
    resp = await client.get("/api/v1/auth/me", headers=auth_headers(u))
    assert resp.status_code == 200
    assert resp.json()["is_driver"] is True


# ─── OTP ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_otp_new_phone(client: AsyncClient):
    """Yangi telefon raqamga OTP yuborish (register — login mavjud user talab qiladi)."""
    resp = await client.post(
        "/api/v1/auth/send-otp",
        json={"phone": "+998901234567", "purpose": "register"},
    )
    assert resp.status_code == 200
    assert "expires_in" in resp.json()


@pytest.mark.asyncio
async def test_send_otp_invalid_phone(client: AsyncClient):
    """Noto'g'ri format → 422."""
    resp = await client.post(
        "/api/v1/auth/send-otp",
        json={"phone": "12345", "purpose": "login"},
    )
    assert resp.status_code == 422


# ─── Bloklangan foydalanuvchi ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_blocked_user_denied(
    client: AsyncClient, db: AsyncSession, user: User
):
    """Bloklangan foydalanuvchi API-ga kira olmaydi."""
    user.is_blocked = True
    await db.commit()

    resp = await client.get("/api/v1/auth/me", headers=auth_headers(user))
    assert resp.status_code == 403
