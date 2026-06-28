"""
Test fixtures — barcha test fayllar uchun umumiy sozlamalar.

Ishlash tartibi:
  1. `safarim_test` DB yaratiladi (Docker PostgreSQL portiga ulanadi)
  2. Har bir test sessiyasi boshida jadvallar drop+create qilinadi
  3. Har bir test tugagach barcha jadvallar tozalanadi (CASCADE TRUNCATE)
  4. httpx.AsyncClient FastAPI app-ga to'g'ridan-to'g'ri ulanadi (real HTTP emas)
"""
import asyncio
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.models.driver import DriverProfile
from app.models.enums import AdminRole, DriverStatus
from app.core.security import create_access_token, hash_password

# Test foydalanuvchilari uchun umumiy parol hash'i (password_hash NOT NULL)
_TEST_PASSWORD_HASH = hash_password("Test1234!")

# ─── Test DB ─────────────────────────────────────────────────────────────────

TEST_DB_URL = "postgresql+asyncpg://safarim:safarim123@127.0.0.1:5433/safarim_test"

# NullPool — ulanishlar loop'lar aro ulashilmaydi (pytest-asyncio function loop bilan mos)
engine_test = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
TestingSession = async_sessionmaker(engine_test, expire_on_commit=False)


# ─── Har test uchun toza sxema (o'z function loop'ida) ────────────────────────
# Hamma narsa function-scope: fixture, test va engine bitta loopda ishlaydi.

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


# ─── DB session fixture ───────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db(setup_database) -> AsyncSession:
    async with TestingSession() as session:
        yield session


# ─── HTTP Client ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncClient:
    async def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as c:
        yield c
    app.dependency_overrides.clear()


# ─── Test foydalanuvchilar ────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def user(db: AsyncSession) -> User:
    """Oddiy yo'lovchi."""
    u = User(
        id=uuid.uuid4(),
        phone="+998901111111",
        full_name="Test Yo'lovchi",
        password_hash=_TEST_PASSWORD_HASH,
        is_phone_verified=True,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    """Super admin."""
    u = User(
        id=uuid.uuid4(),
        phone="+998900000001",
        full_name="Test Admin",
        password_hash=_TEST_PASSWORD_HASH,
        is_phone_verified=True,
        is_admin=True,
        admin_role=AdminRole.super_admin,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest_asyncio.fixture
async def driver_user(db: AsyncSession) -> tuple[User, DriverProfile]:
    """Tasdiqlangan haydovchi."""
    u = User(
        id=uuid.uuid4(),
        phone="+998902222222",
        full_name="Test Haydovchi",
        password_hash=_TEST_PASSWORD_HASH,
        is_phone_verified=True,
        is_driver=True,
    )
    db.add(u)
    await db.flush()

    dp = DriverProfile(
        user_id=u.id,
        license_image="test/license.jpg",
        vehicle_make="Nexia",
        vehicle_model="3",
        vehicle_year=2022,
        vehicle_color="Oq",
        vehicle_plate="01A001AA",
        vehicle_seats=4,
        status=DriverStatus.approved,
    )
    db.add(dp)
    await db.commit()
    await db.refresh(u)
    await db.refresh(dp)
    return u, dp


# ─── Yordamchi ────────────────────────────────────────────────────────────────

def auth_headers(user: User) -> dict:
    """Bearer token bilan header."""
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}
