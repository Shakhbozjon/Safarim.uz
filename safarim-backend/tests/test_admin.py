"""
Admin API testlari: haydovchi tasdiqlash/rad etish, statistika, bloklash.
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.driver import DriverProfile
from app.models.enums import DriverStatus
from tests.conftest import auth_headers, _TEST_PASSWORD_HASH


# ─── Yordamchi: pending haydovchi yaratish ───────────────────────────────────

async def _make_pending_driver(
    db: AsyncSession, phone: str = "+998907777777", plate: str = "01D111DD"
) -> tuple[User, DriverProfile]:
    u = User(
        id=uuid.uuid4(),
        phone=phone,
        full_name="Ariza Haydovchi",
        password_hash=_TEST_PASSWORD_HASH,
        is_phone_verified=True,
        is_driver=True,
    )
    db.add(u)
    await db.flush()

    dp = DriverProfile(
        user_id=u.id,
        license_image="docs/lic.jpg",
        vehicle_make="Spark",
        vehicle_model="Lite",
        vehicle_year=2021,
        vehicle_color="Kumush",
        vehicle_plate=plate,
        vehicle_seats=4,
        status=DriverStatus.pending,
    )
    db.add(dp)
    await db.commit()
    await db.refresh(u)
    await db.refresh(dp)
    return u, dp


# ─── Ruxsat tekshiruvi ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_endpoint_requires_admin(client: AsyncClient, user: User):
    """Oddiy user admin API-ga kira olmaydi."""
    resp = await client.get(
        "/api/v1/admin/drivers/pending", headers=auth_headers(user)
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_stats_requires_admin(client: AsyncClient, user: User):
    resp = await client.get("/api/v1/admin/stats", headers=auth_headers(user))
    assert resp.status_code == 403


# ─── Statistika ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stats_returns_fields(client: AsyncClient, admin_user: User):
    """Statistika to'g'ri maydonlarni qaytaradi."""
    resp = await client.get(
        "/api/v1/admin/stats", headers=auth_headers(admin_user)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data
    assert "total_drivers" in data
    assert "pending_drivers" in data
    assert "total_trips" in data
    assert "total_bookings" in data
    assert "completed_bookings" in data


@pytest.mark.asyncio
async def test_stats_counts_correctly(
    client: AsyncClient, db: AsyncSession, admin_user: User
):
    """Pending driver qo'shganda statistika yangilanadi."""
    await _make_pending_driver(db)

    resp = await client.get(
        "/api/v1/admin/stats", headers=auth_headers(admin_user)
    )
    data = resp.json()
    assert data["pending_drivers"] >= 1


# ─── Pending drivers ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pending_drivers_empty(client: AsyncClient, admin_user: User):
    """Ariza yo'q → bo'sh ro'yxat."""
    resp = await client.get(
        "/api/v1/admin/drivers/pending", headers=auth_headers(admin_user)
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_pending_drivers_shows_pending_only(
    client: AsyncClient, db: AsyncSession, admin_user: User, driver_user: tuple
):
    """Tasdiqlangan haydovchi pending ro'yxatda ko'rinmaydi."""
    await _make_pending_driver(db)  # bir pending

    resp = await client.get(
        "/api/v1/admin/drivers/pending", headers=auth_headers(admin_user)
    )
    items = resp.json()
    assert len(items) == 1  # faqat pending
    assert items[0]["status"] == "pending"


# ─── Approve ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_approve_driver(
    client: AsyncClient, db: AsyncSession, admin_user: User
):
    """Admin haydovchini tasdiqlaydi."""
    _u, dp = await _make_pending_driver(db)

    resp = await client.post(
        f"/api/v1/admin/drivers/{dp.id}/approve",
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_approve_removes_from_pending(
    client: AsyncClient, db: AsyncSession, admin_user: User
):
    """Tasdiqlangandan keyin pending ro'yxatdan chiqadi."""
    _u, dp = await _make_pending_driver(db)

    await client.post(
        f"/api/v1/admin/drivers/{dp.id}/approve",
        headers=auth_headers(admin_user),
    )

    resp = await client.get(
        "/api/v1/admin/drivers/pending", headers=auth_headers(admin_user)
    )
    assert resp.json() == []


@pytest.mark.asyncio
async def test_approve_nonexistent_driver(
    client: AsyncClient, admin_user: User
):
    """Mavjud bo'lmagan ID → 404."""
    resp = await client.post(
        f"/api/v1/admin/drivers/{uuid.uuid4()}/approve",
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 404


# ─── Reject ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reject_driver(
    client: AsyncClient, db: AsyncSession, admin_user: User
):
    """Admin haydovchini rad etadi."""
    _u, dp = await _make_pending_driver(db)

    resp = await client.post(
        f"/api/v1/admin/drivers/{dp.id}/reject",
        json={"reason": "Guvohnoma aniq emas"},
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["rejection_reason"] == "Guvohnoma aniq emas"


@pytest.mark.asyncio
async def test_reject_without_reason_fails(
    client: AsyncClient, db: AsyncSession, admin_user: User
):
    """Sabab ko'rsatilmasa → 422."""
    _u, dp = await _make_pending_driver(db, plate="01E222EE")

    resp = await client.post(
        f"/api/v1/admin/drivers/{dp.id}/reject",
        json={},
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 422


# ─── Foydalanuvchi bloklash ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_block_user(
    client: AsyncClient, db: AsyncSession, admin_user: User, user: User
):
    """Admin foydalanuvchini bloklaydi."""
    resp = await client.post(
        f"/api/v1/admin/users/{user.id}/block",
        params={"reason": "Shartlar buzildi"},
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200
    assert "bloklandi" in resp.json()["message"]

    # Bloklangan user /me-ga kira olmaydi
    resp = await client.get("/api/v1/auth/me", headers=auth_headers(user))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unblock_user(
    client: AsyncClient, db: AsyncSession, admin_user: User, user: User
):
    """Admin foydalanuvchini blokdan chiqaradi."""
    # Avval bloklash
    user.is_blocked = True
    await db.commit()

    resp = await client.post(
        f"/api/v1/admin/users/{user.id}/unblock",
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200

    # Endi kira oladi
    resp = await client.get("/api/v1/auth/me", headers=auth_headers(user))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_cannot_block_admin(
    client: AsyncClient, db: AsyncSession, admin_user: User
):
    """Admin boshqa adminni bloklolmaydi."""
    another_admin = User(
        id=uuid.uuid4(),
        phone="+998900000002",
        full_name="Admin 2",
        password_hash=_TEST_PASSWORD_HASH,
        is_phone_verified=True,
        is_admin=True,
    )
    db.add(another_admin)
    await db.commit()

    resp = await client.post(
        f"/api/v1/admin/users/{another_admin.id}/block",
        params={"reason": "test"},
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 403
