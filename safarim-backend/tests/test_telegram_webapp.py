"""Telegram Mini App: initData imzosini tekshirish va avtomatik kirish."""
import hashlib
import hmac
import json
import time
import uuid
from urllib.parse import urlencode

from app.core.config import settings
from app.models.user import User
from app.services.telegram_webapp import verify_init_data
from tests.conftest import _TEST_PASSWORD_HASH

BOT_TOKEN = "123456:TEST-TOKEN"
TG_ID = 700100200


def _init_data(user_id=TG_ID, auth_date=None, token=BOT_TOKEN, start_param=None, tamper=None) -> str:
    fields = {
        "auth_date": str(int(auth_date if auth_date is not None else time.time())),
        "query_id": "AAH",
        "user": json.dumps({"id": user_id, "first_name": "Ali"}, separators=(",", ":")),
    }
    if start_param:
        fields["start_param"] = start_param
    check = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if tamper:
        fields.update(tamper)
    return urlencode(fields)


# ─── Imzo ────────────────────────────────────────────────────────────────────

def test_togri_imzo_qabul_qilinadi():
    user = verify_init_data(_init_data(), BOT_TOKEN)
    assert user["id"] == TG_ID


def test_boshqa_bot_tokeni_bilan_imzolangan_rad():
    assert verify_init_data(_init_data(token="999:OTHER"), BOT_TOKEN) is None


def test_ozgartirilgan_foydalanuvchi_rad():
    """Imzo saqlanib, user ID boshqasiga almashtirilsa — begona hisobga kirib bo'lmasin."""
    forged = _init_data(tamper={"user": json.dumps({"id": 1, "first_name": "X"})})
    assert verify_init_data(forged, BOT_TOKEN) is None


def test_eskirgan_initdata_rad():
    old = _init_data(auth_date=time.time() - 2 * 24 * 3600)
    assert verify_init_data(old, BOT_TOKEN) is None


def test_hashsiz_va_axlat_rad():
    for bad in ("", "abc", "user=%7B%7D", "hash=00&user=x&auth_date=1"):
        assert verify_init_data(bad, BOT_TOKEN) is None


def test_bosh_bot_tokeni_bilan_hech_narsa_otmaydi():
    assert verify_init_data(_init_data(), "") is None


# ─── Endpoint ────────────────────────────────────────────────────────────────

async def test_royxatdagi_foydalanuvchi_avtomatik_kiradi(client, db, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    db.add(User(id=uuid.uuid4(), phone="+998935550001", full_name="Ali",
                password_hash=_TEST_PASSWORD_HASH, is_phone_verified=True,
                telegram_chat_id=str(TG_ID)))
    await db.commit()

    r = await client.post("/api/v1/auth/telegram-webapp",
                          json={"init_data": _init_data(start_param="trip_abc")})
    body = r.json()
    assert r.status_code == 200 and body["registered"] is True
    assert body["start_param"] == "trip_abc"
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.json()["phone"] == "+998935550001"


async def test_royxatda_yoq_bolsa_botga_yonaltiradi(client, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "uzsafar_uz_bot")
    r = await client.post("/api/v1/auth/telegram-webapp", json={"init_data": _init_data()})
    assert r.json() == {"registered": False, "bot_username": "uzsafar_uz_bot"}


async def test_soxta_initdata_401(client, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    r = await client.post("/api/v1/auth/telegram-webapp",
                          json={"init_data": _init_data(token="999:OTHER")})
    assert r.status_code == 401


async def test_bloklangan_foydalanuvchi_kirmaydi(client, db, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    db.add(User(id=uuid.uuid4(), phone="+998935550002", full_name="B",
                password_hash=_TEST_PASSWORD_HASH, telegram_chat_id=str(TG_ID), is_blocked=True))
    await db.commit()
    r = await client.post("/api/v1/auth/telegram-webapp", json={"init_data": _init_data()})
    assert r.json()["registered"] is False and "access_token" not in r.json()
