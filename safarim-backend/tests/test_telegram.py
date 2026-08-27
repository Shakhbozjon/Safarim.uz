"""
Telegram bot oqimi: raqamni tasdiqlash va raqamni almashtirish.

Bot tarmoqqa chiqmasligi uchun `_call` monkeypatch qilinadi — yuborilgan
xabarlar ro'yxatga yig'iladi va matnini tekshirish mumkin.
"""
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TelegramLinkPurpose
from app.models.telegram import TelegramLinkToken
from app.models.user import User
from app.services import telegram_service


CHAT = 555000111


@pytest.fixture
def sent(monkeypatch) -> list[dict]:
    """Telegramga ketadigan chaqiruvlarni ushlab qoladi."""
    calls: list[dict] = []

    async def _fake_call(method: str, payload: dict):
        calls.append({"method": method, **payload})
        return {"ok": True}

    monkeypatch.setattr(telegram_service, "_call", _fake_call)
    return calls


async def _token(
    db: AsyncSession,
    user: User,
    purpose: TelegramLinkPurpose,
    chat_id: int = CHAT,
) -> TelegramLinkToken:
    """`/start <token>` bosqichi o'tgan havola: chat allaqachon bog'langan."""
    link = TelegramLinkToken(
        id=uuid.uuid4(),
        token=uuid.uuid4().hex,
        user_id=user.id,
        chat_id=str(chat_id),
        purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    )
    db.add(link)
    await db.commit()
    return link


def _contact_update(phone: str, chat_id: int = CHAT, sender_id: int = 42) -> dict:
    """Foydalanuvchi «Raqamni ulashish» tugmasini bosgandagi yangilanish."""
    return {
        "message": {
            "chat": {"id": chat_id},
            "from": {"id": sender_id},
            "contact": {"phone_number": phone, "user_id": sender_id},
        }
    }


# ─── Tasdiqlash (eski xatti-harakat saqlanishi) ──────────────────────────────

@pytest.mark.asyncio
async def test_verify_matching_phone(db: AsyncSession, user: User, sent: list):
    """Raqam hisobdagiga mos → tasdiqlanadi."""
    user.is_phone_verified = False
    await _token(db, user, TelegramLinkPurpose.verify)

    await telegram_service.handle_update(db, _contact_update(user.phone))

    await db.refresh(user)
    assert user.is_phone_verified is True
    assert user.telegram_chat_id == str(CHAT)


@pytest.mark.asyncio
async def test_verify_rejects_other_phone(db: AsyncSession, user: User, sent: list):
    """Boshqa raqam yuborilsa tasdiqlanmaydi va raqam ham o'zgarmaydi."""
    user.is_phone_verified = False
    original = user.phone
    await _token(db, user, TelegramLinkPurpose.verify)

    await telegram_service.handle_update(db, _contact_update("+998909999999"))

    await db.refresh(user)
    assert user.is_phone_verified is False
    assert user.phone == original


# ─── Raqamni almashtirish ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_change_phone_sets_new_number(db: AsyncSession, user: User, sent: list):
    """Almashtirishda raqam solishtirilmaydi — o'rnatiladi."""
    new_phone = "+998907654321"
    await _token(db, user, TelegramLinkPurpose.change_phone)

    await telegram_service.handle_update(db, _contact_update(new_phone))

    await db.refresh(user)
    assert user.phone == new_phone
    assert user.is_phone_verified is True
    assert user.telegram_chat_id == str(CHAT)
    assert "o'zgartirildi" in sent[-1]["text"]


@pytest.mark.asyncio
async def test_change_phone_refuses_taken_number(
    db: AsyncSession, user: User, driver_user: tuple, sent: list
):
    """Raqam boshqa hisobda bo'lsa almashtirilmaydi."""
    driver, _dp = driver_user
    original = user.phone
    await _token(db, user, TelegramLinkPurpose.change_phone)

    await telegram_service.handle_update(db, _contact_update(driver.phone))

    await db.refresh(user)
    assert user.phone == original
    assert "boshqa hisobga biriktirilgan" in sent[-1]["text"]


@pytest.mark.asyncio
async def test_change_phone_rejects_someone_elses_contact(
    db: AsyncSession, user: User, sent: list
):
    """Begona odamning kontakt kartasi qabul qilinmaydi.

    Telegram faqat o'z raqamida `contact.user_id` ni jo'natuvchiga teng qiladi;
    boshqa raqamni yuborish orqali hisobni o'g'irlab bo'lmasin.
    """
    original = user.phone
    await _token(db, user, TelegramLinkPurpose.change_phone)

    update = _contact_update("+998907654321")
    update["message"]["contact"]["user_id"] = 999  # jo'natuvchi emas

    await telegram_service.handle_update(db, update)

    await db.refresh(user)
    assert user.phone == original


@pytest.mark.asyncio
async def test_change_phone_unbinds_previous_account(
    db: AsyncSession, user: User, driver_user: tuple, sent: list
):
    """Bir chat faqat bitta hisobga bog'lanadi.

    Aks holda tasdiq tugmasi bosilganda chat bo'yicha ikki foydalanuvchi
    topilardi va `_handle_callback` yiqilardi.
    """
    driver, _dp = driver_user
    driver.telegram_chat_id = str(CHAT)
    await db.commit()

    await _token(db, user, TelegramLinkPurpose.change_phone)
    await telegram_service.handle_update(db, _contact_update("+998907654321"))

    await db.refresh(user)
    await db.refresh(driver)
    assert user.telegram_chat_id == str(CHAT)
    assert driver.telegram_chat_id is None


@pytest.mark.asyncio
async def test_change_phone_same_number_just_verifies(
    db: AsyncSession, user: User, sent: list
):
    """O'sha raqamning o'zi yuborilsa — xato emas, shunchaki tasdiqlanadi."""
    user.is_phone_verified = False
    await _token(db, user, TelegramLinkPurpose.change_phone)

    await telegram_service.handle_update(db, _contact_update(user.phone))

    await db.refresh(user)
    assert user.phone == "+998901111111"
    assert user.is_phone_verified is True
