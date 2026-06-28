"""
Notifications testlari: yaratish, o'qish, unread count.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.enums import NotificationRefType
from app.services import notification_service
from tests.conftest import auth_headers


# ─── Bo'sh holat ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notifications_empty(client: AsyncClient, user: User):
    """Yangi foydalanuvchida bildirishnoma yo'q."""
    resp = await client.get("/api/v1/notifications", headers=auth_headers(user))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_unread_count_zero(client: AsyncClient, user: User):
    """Yangi foydalanuvchida unread count = 0."""
    resp = await client.get(
        "/api/v1/notifications/unread-count", headers=auth_headers(user)
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


# ─── Yaratish va o'qish ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notification_appears_in_list(
    client: AsyncClient, db: AsyncSession, user: User
):
    """Yaratilgan bildirishnoma ro'yxatda ko'rinadi."""
    await notification_service.create(
        db,
        user_id=user.id,
        title="Salom!",
        body="Bu test xabar.",
        ref_type=NotificationRefType.system,
    )
    await db.commit()

    resp = await client.get("/api/v1/notifications", headers=auth_headers(user))
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["title"] == "Salom!"
    assert items[0]["is_read"] is False


@pytest.mark.asyncio
async def test_unread_count_increments(
    client: AsyncClient, db: AsyncSession, user: User
):
    """Har bir yangi bildirishnoma unread count-ni oshiradi."""
    for i in range(3):
        await notification_service.create(
            db, user_id=user.id, title=f"Xabar {i}", body="..."
        )
    await db.commit()

    resp = await client.get(
        "/api/v1/notifications/unread-count", headers=auth_headers(user)
    )
    assert resp.json()["count"] == 3


@pytest.mark.asyncio
async def test_mark_one_read(client: AsyncClient, db: AsyncSession, user: User):
    """Bitta bildirishnomani o'qildi belgilash."""
    await notification_service.create(
        db, user_id=user.id, title="Test", body="Test"
    )
    await notification_service.create(
        db, user_id=user.id, title="Test 2", body="Test 2"
    )
    await db.commit()

    # Ro'yxatdan birinchisini olish
    resp = await client.get("/api/v1/notifications", headers=auth_headers(user))
    first_id = resp.json()[0]["id"]

    # O'qildi belgilash
    resp = await client.put(
        f"/api/v1/notifications/{first_id}/read", headers=auth_headers(user)
    )
    assert resp.status_code == 200

    # Unread count = 1 (bittasi o'qildi)
    resp = await client.get(
        "/api/v1/notifications/unread-count", headers=auth_headers(user)
    )
    assert resp.json()["count"] == 1


@pytest.mark.asyncio
async def test_mark_all_read(client: AsyncClient, db: AsyncSession, user: User):
    """Barcha bildirishnomalarni o'qildi belgilash."""
    for i in range(4):
        await notification_service.create(
            db, user_id=user.id, title=f"Xabar {i}", body="..."
        )
    await db.commit()

    resp = await client.put(
        "/api/v1/notifications/read-all", headers=auth_headers(user)
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] == 4

    resp = await client.get(
        "/api/v1/notifications/unread-count", headers=auth_headers(user)
    )
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_read_nonexistent_notification(client: AsyncClient, user: User):
    """Mavjud bo'lmagan ID → 404."""
    import uuid
    fake_id = uuid.uuid4()
    resp = await client.put(
        f"/api/v1/notifications/{fake_id}/read", headers=auth_headers(user)
    )
    assert resp.status_code == 404


# ─── Boshqa foydalanuvchi ko'ra olmaydi ──────────────────────────────────────

@pytest.mark.asyncio
async def test_other_user_cannot_read(
    client: AsyncClient, db: AsyncSession, user: User, admin_user: User
):
    """User A ning bildirishnomasi User B ko'ra olmaydi."""
    await notification_service.create(
        db, user_id=user.id, title="Maxfiy", body="..."
    )
    await db.commit()

    # admin_user o'z ro'yxatini ko'radi — bo'sh bo'lishi kerak
    resp = await client.get(
        "/api/v1/notifications", headers=auth_headers(admin_user)
    )
    assert resp.json() == []


# ─── Unauthenticated ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notifications_requires_auth(client: AsyncClient):
    """Token yo'q → 403."""
    resp = await client.get("/api/v1/notifications")
    assert resp.status_code == 403
