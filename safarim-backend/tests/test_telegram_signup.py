"""Botda ro'yxatdan o'tish (yo'lovchi va haydovchi) va «Saytga kirish» havolasi.

Tarmoqqa chiqilmaydi — `_call` monkeypatch qilinadi.
"""
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.driver import DriverProfile
from app.models.enums import DriverStatus
from app.models.telegram import TelegramLoginToken, TelegramSignup
from app.models.user import User
from app.services import telegram_service
from tests.conftest import _TEST_PASSWORD_HASH

CHAT = 555000111
SENDER = 4242
PHONE = "+998931234567"


@pytest.fixture
def sent(monkeypatch) -> list[dict]:
    calls: list[dict] = []

    async def _fake_call(method: str, payload: dict, token=None):
        calls.append({"method": method, **payload})
        return {"ok": True, "result": {"message_id": 500}}

    monkeypatch.setattr(telegram_service, "_call", _fake_call)
    return calls


@pytest.fixture(autouse=True)
def _auto_approve(monkeypatch):
    monkeypatch.setattr(settings, "AUTO_APPROVE_DRIVERS", True)


def _texts(sent) -> str:
    return "\n".join(c.get("text", "") for c in sent)


def _callbacks(sent) -> list[str]:
    out = []
    for c in sent:
        for row in (c.get("reply_markup") or {}).get("inline_keyboard", []):
            out += [b.get("callback_data", "") for b in row]
    return out


def _urls(sent) -> list[str]:
    out = []
    for c in sent:
        for row in (c.get("reply_markup") or {}).get("inline_keyboard", []):
            out += [b["url"] for b in row if "url" in b]
    return out


def _msg(text: str) -> dict:
    return {"message": {"chat": {"id": CHAT, "type": "private"},
                        "from": {"id": SENDER, "first_name": "Akmal", "last_name": "Karimov"},
                        "text": text}}


def _contact(phone: str, owner: int = SENDER) -> dict:
    return {"message": {"chat": {"id": CHAT, "type": "private"},
                        "from": {"id": SENDER, "first_name": "Akmal"},
                        "contact": {"phone_number": phone, "user_id": owner}}}


def _cq(data: str) -> dict:
    return {"callback_query": {
        "id": "cb", "data": data,
        "from": {"id": SENDER, "first_name": "Akmal", "last_name": "Karimov"},
        "message": {"chat": {"id": CHAT, "type": "private"}, "message_id": 500},
    }}


async def _go(db, *updates):
    for u in updates:
        await telegram_service.handle_update(db, u)


async def _user_by_phone(db, phone=PHONE) -> User | None:
    return (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()


# ─── Boshlash ────────────────────────────────────────────────────────────────

async def test_start_notanish_odamga_royxat_tugmalari(db, sent):
    await _go(db, _msg("/start"))
    assert {"rg:p", "rg:d"} <= set(_callbacks(sent))
    assert "tasdiqlash boti" not in _texts(sent)


# ─── Yo'lovchi ───────────────────────────────────────────────────────────────

async def test_yolovchi_telegram_ismi_bilan_royxatdan_otadi(db, sent):
    await _go(db, _cq("rg:p"), _contact(PHONE), _cq("rg:nm"))

    user = await _user_by_phone(db)
    assert user is not None
    assert user.full_name == "Akmal Karimov"
    assert user.is_phone_verified is True
    assert user.telegram_chat_id == str(CHAT)
    assert user.is_driver is False
    assert await db.get(TelegramSignup, str(CHAT)) is None   # qoralama o'chirildi
    assert "rg:login" in _callbacks(sent)


async def test_yolovchi_ismini_ozi_yozadi(db, sent):
    await _go(db, _cq("rg:p"), _contact(PHONE), _msg("Dilnoza Rahimova"))
    user = await _user_by_phone(db)
    assert user.full_name == "Dilnoza Rahimova"


async def test_yaroqsiz_ism_qayta_soraladi(db, sent):
    await _go(db, _cq("rg:p"), _contact(PHONE), _msg("<b>x</b>"))
    assert await _user_by_phone(db) is None
    assert "Ismni to'g'ri yozing" in _texts(sent)


async def test_raqam_saytda_bor_bolsa_yangi_hisob_ochilmaydi(db, sent):
    db.add(User(id=uuid.uuid4(), phone=PHONE, full_name="Saytdagi Ali",
                password_hash=_TEST_PASSWORD_HASH, is_phone_verified=False))
    await db.commit()

    await _go(db, _cq("rg:p"), _contact(PHONE))

    users = (await db.execute(select(User).where(User.phone == PHONE))).scalars().all()
    assert len(users) == 1
    assert users[0].full_name == "Saytdagi Ali"
    assert users[0].is_phone_verified is True
    assert users[0].telegram_chat_id == str(CHAT)
    # Eski parol saqlanadi — saytdagi kirish buzilmaydi
    assert users[0].password_hash == _TEST_PASSWORD_HASH


async def test_ozbekiston_raqami_bolmasa_rad(db, sent):
    await _go(db, _cq("rg:p"), _contact("+79161234567"))
    assert await _user_by_phone(db, "+79161234567") is None
    assert "+998" in _texts(sent)


async def test_begona_kontakt_qabul_qilinmaydi(db, sent):
    await _go(db, _cq("rg:p"), _contact(PHONE, owner=999))
    assert await _user_by_phone(db) is None


async def test_kontakt_orniga_matn_yozsa_tugma_eslatiladi(db, sent):
    await _go(db, _cq("rg:p"))
    sent.clear()
    await _go(db, _msg("+998931234567"))
    assert await _user_by_phone(db) is None
    assert "Raqamni ulashish" in _texts(sent)


# ─── Haydovchi ───────────────────────────────────────────────────────────────

async def _driver_until_plate(db):
    await _go(db, _cq("rg:d"), _contact(PHONE), _cq("rg:nm"),
              _cq("rg:mk:0"), _cq("rg:md:0"), _cq("rg:cl:0"))


async def test_haydovchi_toliq_royxatdan_otadi(db, sent):
    await _driver_until_plate(db)
    await _go(db, _msg("01 a 123 bc"), _cq("rg:st:4"))

    user = await _user_by_phone(db)
    assert user.is_driver is True
    dp = (await db.execute(select(DriverProfile).where(DriverProfile.user_id == user.id))).scalar_one()
    assert (dp.vehicle_make, dp.vehicle_model, dp.vehicle_color, dp.vehicle_plate, dp.vehicle_seats) \
        == ("Chevrolet", "Cobalt", "Oq", "01A123BC", 4)
    assert dp.status == DriverStatus.approved
    assert dp.verified_by is None              # hujjat tekshirilmagan — belgi yo'q
    assert await db.get(TelegramSignup, str(CHAT)) is None
    assert "Tabriklaymiz" in _texts(sent)


async def test_haydovchi_boshqa_marka_va_modelni_yozadi(db, sent):
    await _go(db, _cq("rg:d"), _contact(PHONE), _cq("rg:nm"),
              _cq("rg:mk:o"), _msg("Lada"), _msg("Vesta"), _cq("rg:cl:o"), _msg("Sariq"),
              _msg("01A777AA"), _cq("rg:st:4"))
    user = await _user_by_phone(db)
    dp = (await db.execute(select(DriverProfile).where(DriverProfile.user_id == user.id))).scalar_one()
    assert (dp.vehicle_make, dp.vehicle_model, dp.vehicle_color) == ("Lada", "Vesta", "Sariq")


async def test_notogri_davlat_raqami_qayta_soraladi(db, sent):
    await _driver_until_plate(db)
    sent.clear()
    await _go(db, _msg("salom"))
    assert "❌" in _texts(sent)
    draft = await db.get(TelegramSignup, str(CHAT))
    assert draft.step == "plate"


async def test_band_davlat_raqami_rad_etiladi(db, sent, driver_user):
    other, other_dp = driver_user          # plate 01A001AA
    await _driver_until_plate(db)
    sent.clear()
    await _go(db, _msg(other_dp.vehicle_plate))
    assert "boshqa haydovchida" in _texts(sent)
    draft = await db.get(TelegramSignup, str(CHAT))
    assert draft.step == "plate"


async def test_ulangan_yolovchi_haydovchi_bolsa_raqam_soralmaydi(db, sent):
    await _go(db, _cq("rg:p"), _contact(PHONE), _cq("rg:nm"))
    sent.clear()
    await _go(db, _cq("rg:d"))
    draft = await db.get(TelegramSignup, str(CHAT))
    assert draft.step == "make"
    assert "Raqamni ulashish" not in _texts(sent)


async def test_deep_link_haydovchi(db, sent):
    await _go(db, _msg("/start haydovchi"))
    draft = await db.get(TelegramSignup, str(CHAT))
    assert draft.role == "driver" and draft.step == "contact"


async def test_eskirgan_tugma_xato_bermaydi(db, sent):
    await _go(db, _cq("rg:st:4"))
    assert "ishlamaydi" in _texts(sent)


async def test_tasdiqlangan_haydovchiga_start_menyu_beradi(db, sent, driver_user):
    user, _ = driver_user
    user.telegram_chat_id = str(CHAT)
    await db.commit()
    await _go(db, _msg("/start"))
    assert "rg:p" not in _callbacks(sent)   # ro'yxat emas, ish menyusi


# ─── Saytga kirish ───────────────────────────────────────────────────────────

async def _login_token(db, sent) -> str:
    await _go(db, _cq("rg:p"), _contact(PHONE), _cq("rg:nm"))
    sent.clear()
    await _go(db, _cq("rg:login"))
    url = _urls(sent)[0]
    assert "/auth/telegram?t=" in url
    return url.split("t=", 1)[1]


async def test_saytga_kirish_havolasi_ishlaydi_va_bir_martalik(client, db, sent):
    token = await _login_token(db, sent)

    r = await client.post("/api/v1/auth/telegram-login", json={"token": token})
    assert r.status_code == 200
    me = await client.get("/api/v1/auth/me",
                          headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.json()["phone"] == PHONE

    again = await client.post("/api/v1/auth/telegram-login", json={"token": token})
    assert again.status_code == 400


async def test_eskirgan_kirish_havolasi_ishlamaydi(client, db, sent):
    token = await _login_token(db, sent)
    row = (await db.execute(select(TelegramLoginToken).where(TelegramLoginToken.token == token))).scalar_one()
    row.expires_at = datetime.utcnow() - timedelta(seconds=1)
    await db.commit()
    r = await client.post("/api/v1/auth/telegram-login", json={"token": token})
    assert r.status_code == 400


async def test_yangi_havola_eskisini_bekor_qiladi(client, db, sent):
    first = await _login_token(db, sent)
    await _go(db, _cq("rg:login"))
    r = await client.post("/api/v1/auth/telegram-login", json={"token": first})
    assert r.status_code == 400


async def test_soxta_token_ishlamaydi(client):
    r = await client.post("/api/v1/auth/telegram-login", json={"token": "yoq-bunday"})
    assert r.status_code == 400


async def test_bloklangan_foydalanuvchi_kira_olmaydi(client, db, sent):
    token = await _login_token(db, sent)
    user = await _user_by_phone(db)
    user.is_blocked = True
    await db.commit()
    r = await client.post("/api/v1/auth/telegram-login", json={"token": token})
    assert r.status_code == 400
