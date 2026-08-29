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


# ─── Telegrami ulanmagan foydalanuvchi: bot orqali tiklash ────────────────────

@pytest.fixture
def bot_configured(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "uzsafar_test_bot")


def _start(token: str, chat_id: int) -> dict:
    """Havola bosilganda Telegram yuboradigan `/start <token>` yangilanishi."""
    return {"message": {"chat": {"id": chat_id}, "from": {"id": 42},
                        "text": f"/start {token}"}}


def _contact(phone: str, chat_id: int, sender_id: int = 42) -> dict:
    return {
        "message": {
            "chat": {"id": chat_id},
            "from": {"id": sender_id},
            "contact": {"phone_number": phone, "user_id": sender_id},
        }
    }


@pytest.mark.asyncio
async def test_reset_link_unknown_phone(client: AsyncClient, bot_configured):
    """Ro'yxatdan o'tmagan raqamga havola berilmaydi."""
    resp = await client.post(
        f"{API}/telegram-reset-link", json={"phone": "+998909998877"}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reset_link_returns_bot_url(
    client: AsyncClient, user: User, bot_configured
):
    """Mavjud raqamga bot havolasi qaytadi."""
    resp = await client.post(f"{API}/telegram-reset-link", json={"phone": user.phone})
    assert resp.status_code == 200, resp.text
    assert resp.json()["url"].startswith("https://t.me/uzsafar_test_bot?start=")


@pytest.mark.asyncio
async def test_bot_sends_code_when_contact_matches(
    client: AsyncClient, db: AsyncSession, user: User, tg_sent: list, bot_configured
):
    """Kontakt hisobdagi raqamga mos → chat bog'lanadi va kod o'sha chatga ketadi."""
    resp = await client.post(f"{API}/telegram-reset-link", json={"phone": user.phone})
    assert resp.status_code == 200
    token = resp.json()["url"].split("start=")[1]

    # Havolani bosish → bot tokenni chatga bog'laydi, so'ng kontakt ulashiladi
    await telegram_service.handle_update(db, _start(token, 888001))
    await telegram_service.handle_update(db, _contact(user.phone, 888001))

    await db.refresh(user)
    assert user.telegram_chat_id == "888001"

    code = await _otp_for(db, user.phone)
    texts = [c["text"] for c in tg_sent if str(c.get("chat_id")) == "888001"]
    assert any(code in t for t in texts), "Kod chatga yuborilmadi"

    # Kod bilan parolni tiklash ishlaydi
    done = await client.post(f"{API}/reset-password", json={
        "phone": user.phone, "otp_code": code, "new_password": "YangiParol1",
    })
    assert done.status_code == 200, done.text


@pytest.mark.asyncio
async def test_bot_refuses_when_contact_differs(
    client: AsyncClient, db: AsyncSession, user: User, tg_sent: list, bot_configured
):
    """Boshqa odamning raqami ulashilsa — kod yuborilmaydi, chat bog'lanmaydi."""
    resp = await client.post(f"{API}/telegram-reset-link", json={"phone": user.phone})
    token = resp.json()["url"].split("start=")[1]

    await telegram_service.handle_update(db, _start(token, 888002))
    await telegram_service.handle_update(db, _contact("+998907654321", 888002))

    await db.refresh(user)
    assert user.telegram_chat_id is None

    otp = (await db.execute(
        select(OtpCode).where(
            OtpCode.phone == user.phone,
            OtpCode.purpose == OtpPurpose.password_reset,
        )
    )).scalars().first()
    assert otp is None, "Mos kelmagan kontakt uchun kod yaratilmasligi kerak"


# ─── Tizimga kirgan holda parol o'zgartirish (OTP'siz) ───────────────────────

@pytest.mark.asyncio
async def test_change_password_with_current(client: AsyncClient, user: User):
    """Joriy parol to'g'ri bo'lsa yangi parol o'rnatiladi."""
    from tests.conftest import auth_headers

    resp = await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "Test1234!", "new_password": "BoshqaParol9"},
        headers=auth_headers(user),
    )
    assert resp.status_code == 200, resp.text

    login = await client.post(
        f"{API}/login", json={"phone": user.phone, "password": "BoshqaParol9"}
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current(client: AsyncClient, user: User):
    """Joriy parol noto'g'ri bo'lsa rad etiladi — eski parol saqlanadi."""
    from tests.conftest import auth_headers

    resp = await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "YolgonParol", "new_password": "BoshqaParol9"},
        headers=auth_headers(user),
    )
    assert resp.status_code == 400

    login = await client.post(
        f"{API}/login", json={"phone": user.phone, "password": "Test1234!"}
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_change_password_same_as_current(client: AsyncClient, user: User):
    """Yangi parol eskisi bilan bir xil bo'lsa qabul qilinmaydi."""
    from tests.conftest import auth_headers

    resp = await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "Test1234!", "new_password": "Test1234!"},
        headers=auth_headers(user),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_change_password_needs_auth(client: AsyncClient):
    """Tokensiz o'zgartirib bo'lmaydi."""
    resp = await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "Test1234!", "new_password": "BoshqaParol9"},
    )
    assert resp.status_code in (401, 403)
