"""Guruhdagi haydovchi e'loniga «botdan bering» javobi.

Tarmoqqa chiqilmaydi: `_call` va Redis soxtalari bilan almashtiriladi.
"""
import time

import pytest

from app.core.config import settings
from app.models.driver import DriverProfile
from app.models.enums import DriverStatus
from app.models.user import User
from app.services import telegram_feed_nudge as nudge
from app.services import telegram_service
from tests.conftest import _TEST_PASSWORD_HASH

GROUP = "-1001112223334"
OTHER_GROUP = "-1009998887776"
SECRET = "feed-secret"
SENDER = 777001

DRIVER_AD = "Toshkentdan Samarqandga ertaga 8:00 da ketaman, 3 ta joy bor. +998 90 123 45 67"


class FakeRedis:
    def __init__(self):
        self.kv: dict = {}
        self.z: dict = {}

    async def incr(self, key):
        self.kv[key] = int(self.kv.get(key, 0)) + 1
        return self.kv[key]

    async def expire(self, key, sec):
        return True

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.kv:
            return None
        self.kv[key] = value
        return True

    async def zadd(self, key, mapping):
        self.z.setdefault(key, {}).update(mapping)

    async def zrangebyscore(self, key, lo, hi, start=0, num=None, withscores=False):
        items = sorted(((m, s) for m, s in self.z.get(key, {}).items() if s <= hi), key=lambda x: x[1])
        return items[start:start + num] if num else items

    async def zrem(self, key, member):
        self.z.get(key, {}).pop(member, None)


class BrokenRedis:
    async def incr(self, key):
        raise ConnectionError("redis yo'q")


@pytest.fixture
def redis(monkeypatch) -> FakeRedis:
    r = FakeRedis()
    monkeypatch.setattr(nudge, "get_redis", lambda: r)
    return r


@pytest.fixture
def sent(monkeypatch) -> list[dict]:
    calls: list[dict] = []

    async def _fake_call(method, payload, token=None):
        calls.append({"method": method, "token": token, **payload})
        return {"ok": True, "result": {"message_id": 9000 + len(calls)}}

    monkeypatch.setattr(telegram_service, "_call", _fake_call)
    return calls


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_FEED_NUDGE_ENABLED", True)
    monkeypatch.setattr(settings, "TELEGRAM_FEED_BOT_TOKEN", "feed-token")
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "uzsafar_uz_bot")
    monkeypatch.setattr(settings, "TELEGRAM_TRIPS_CHAT_IDS", f"{GROUP},{OTHER_GROUP}")
    monkeypatch.setattr(settings, "TELEGRAM_FEED_WEBHOOK_SECRET", SECRET)


def _update(text=DRIVER_AD, sender=SENDER, chat=GROUP, **extra) -> dict:
    msg = {
        "message_id": 321,
        "chat": {"id": int(chat), "type": "supergroup"},
        "from": {"id": sender, "is_bot": False, "first_name": "Bahodir"},
        "text": text,
    }
    msg.update(extra)
    return {"message": msg}


async def _post(client, update, secret=SECRET):
    r = await client.post(
        "/api/v1/telegram/feed-webhook", json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
    )
    await telegram_service.flush_pending(5)
    return r


# ─── Aniqlash ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    DRIVER_AD,
    "Andijon - Toshkent. Bugun 14:00 chiqaman, bo‘sh joy bor. Cobalt",
    "Farg'ona → Toshkent yo'lovchi olaman 2 joy 90 123 45 67",
    "ТОШКЕНТ - НАМАНГАН жой бор, кетаман соат 6да",
    "Ташкент Самарканд есть места, выезжаю в 7:00",
    "Qarshi Toshkent pochta olaman",
    "Yo`lovchi kerak Buxoroga 2 kishilik joy, tel 991234567 ketaman",
])
def test_driver_ads_detected(text):
    assert nudge.looks_like_driver_ad(text)


@pytest.mark.parametrize("text", [
    "Toshkentdan Samarqandga mashina kerak, 2 kishimiz",
    "Ertaga Namanganga kim ketyapti? Joy bormi",
    "Toshkentga ketaman, taksi kerak +998901234567",
    "Нужна машина Ташкент Самарканд",
    "Assalomu alaykum hammaga",
    "Rahmat aka",
    "ketaman",                         # juda qisqa
    "Bugun havo yaxshi, Toshkentda yomg'ir yo'q",  # haydovchi iborasi yo'q
    "Ketaman ketaman ketaman ketaman ketaman",     # shahar ham, raqam ham yo'q
])
def test_non_driver_messages_ignored(text):
    assert not nudge.looks_like_driver_ad(text)


# ─── Webhook ─────────────────────────────────────────────────────────────────

async def test_driver_ad_gets_reply_with_bot_link(client, redis, sent):
    r = await _post(client, _update())
    assert r.status_code == 200

    assert len(sent) == 1
    msg = sent[0]
    assert msg["method"] == "sendMessage"
    assert msg["token"] == "feed-token"                    # lenta boti, asosiy emas
    assert msg["chat_id"] == GROUP
    assert msg["reply_parameters"]["message_id"] == 321
    assert msg["disable_notification"] is True
    assert "Bahodir" in msg["text"]
    url = msg["reply_markup"]["inline_keyboard"][0][0]["url"]
    assert url == "https://t.me/uzsafar_uz_bot?start=haydovchi"

    # O'chirish navbatiga ~10 daqiqaga qo'yildi
    queue = redis.z[nudge.DELETE_QUEUE_KEY]
    (member, due), = queue.items()
    assert member == f"{GROUP}:{9001}"
    assert 9 * 60 < due - time.time() <= 10 * 60


async def test_wrong_secret_rejected(client, redis, sent):
    r = await _post(client, _update(), secret="wrong")
    assert r.status_code == 403
    assert sent == []


async def test_empty_secret_rejects_everything(client, redis, sent, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_FEED_WEBHOOK_SECRET", "")
    r = await _post(client, _update(), secret="")
    assert r.status_code == 403
    assert sent == []


async def test_disabled_by_default_flag(client, redis, sent, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_FEED_NUDGE_ENABLED", False)
    r = await _post(client, _update())
    assert r.status_code == 200
    assert sent == []


async def test_without_separate_feed_bot_does_nothing(client, redis, sent, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_FEED_BOT_TOKEN", "")
    await _post(client, _update())
    assert sent == []


async def test_once_per_day_per_person(client, redis, sent):
    await _post(client, _update())
    await _post(client, _update())
    await _post(client, _update(chat=OTHER_GROUP))   # boshqa guruhda ham
    assert len(sent) == 1


async def test_different_drivers_each_get_one(client, redis, sent):
    await _post(client, _update(sender=1))
    await _post(client, _update(sender=2))
    assert len(sent) == 2


async def test_group_hourly_cap(client, redis, sent):
    for i in range(nudge.GROUP_LIMIT_PER_HOUR + 5):
        await _post(client, _update(sender=1000 + i))
    assert len(sent) == nudge.GROUP_LIMIT_PER_HOUR


async def test_redis_down_means_silence(client, sent, monkeypatch):
    monkeypatch.setattr(nudge, "get_redis", lambda: BrokenRedis())
    r = await _post(client, _update())
    assert r.status_code == 200
    assert sent == []


async def test_unknown_group_ignored(client, redis, sent):
    await _post(client, _update(chat="-1005555555555"))
    assert sent == []


async def test_private_chat_ignored(client, redis, sent):
    upd = _update()
    upd["message"]["chat"] = {"id": SENDER, "type": "private"}
    await _post(client, upd)
    assert sent == []


@pytest.mark.parametrize("extra", [
    {"sender_chat": {"id": -100, "type": "channel"}},
    {"forward_origin": {"type": "user"}},
    {"forward_date": 1700000000},
    {"via_bot": {"id": 1, "is_bot": True}},
    {"reply_to_message": {"message_id": 100}},
])
async def test_non_plain_posts_ignored(client, redis, sent, extra):
    await _post(client, _update(**extra))
    assert sent == []


async def test_bot_messages_ignored(client, redis, sent):
    upd = _update()
    upd["message"]["from"]["is_bot"] = True
    await _post(client, upd)
    assert sent == []


async def test_topic_group_reply_goes_to_same_topic(client, redis, sent):
    await _post(client, _update(
        is_topic_message=True, message_thread_id=55,
        reply_to_message={"message_id": 55},
    ))
    assert len(sent) == 1
    assert sent[0]["message_thread_id"] == 55


async def test_photo_caption_checked(client, redis, sent):
    upd = _update()
    del upd["message"]["text"]
    upd["message"]["caption"] = DRIVER_AD
    await _post(client, upd)
    assert len(sent) == 1


async def test_edited_message_ignored(client, redis, sent):
    await _post(client, {"edited_message": _update()["message"]})
    assert sent == []


async def test_passenger_ad_ignored(client, redis, sent):
    await _post(client, _update(text="Toshkentdan Samarqandga mashina kerak, ertaga ketaman"))
    assert sent == []
    assert redis.kv == {}            # cheklov ham sarflanmadi


async def _make_user(db, chat_id, *, driver_status=None, is_admin=False, phone="+998931110000"):
    u = User(phone=phone, full_name="Test Haydovchi", password_hash=_TEST_PASSWORD_HASH,
             telegram_chat_id=str(chat_id), is_admin=is_admin, is_phone_verified=True)
    db.add(u)
    await db.flush()
    if driver_status is not None:
        db.add(DriverProfile(
            user_id=u.id, vehicle_make="Chevrolet",
            vehicle_model="Cobalt", vehicle_color="Oq", vehicle_plate="01A111AA",
            vehicle_seats=4, status=driver_status,
        ))
    await db.commit()
    return u


@pytest.mark.parametrize("status", [DriverStatus.approved, DriverStatus.pending])
async def test_existing_uzsafar_driver_not_nudged(client, db, redis, sent, status):
    await _make_user(db, SENDER, driver_status=status)
    await _post(client, _update())
    assert sent == []


async def test_admin_not_nudged(client, db, redis, sent):
    await _make_user(db, SENDER, is_admin=True)
    await _post(client, _update())
    assert sent == []


async def test_registered_passenger_is_nudged(client, db, redis, sent):
    await _make_user(db, SENDER)
    await _post(client, _update())
    assert len(sent) == 1


async def test_name_is_escaped(client, redis, sent):
    upd = _update()
    upd["message"]["from"]["first_name"] = "<b>Ali</b>"
    await _post(client, upd)
    assert "<b>Ali</b>" not in sent[0]["text"]
    assert "&lt;b&gt;Ali" in sent[0]["text"]


async def test_handler_error_still_returns_200(client, redis, sent, monkeypatch):
    async def _boom(db, update):
        raise RuntimeError("xato")
    monkeypatch.setattr(nudge, "handle_group_update", _boom)
    r = await _post(client, _update())
    assert r.status_code == 200


# ─── O'chirish ───────────────────────────────────────────────────────────────

async def test_purge_deletes_only_due_replies(redis, sent):
    now = time.time()
    redis.z[nudge.DELETE_QUEUE_KEY] = {
        f"{GROUP}:1": now - 5,          # vaqti keldi
        f"{GROUP}:2": now + 300,        # hali erta
    }
    deleted = await nudge.purge_due_replies(redis)
    assert deleted == 1
    assert [(c["method"], c["message_id"], c["token"]) for c in sent] == [("deleteMessage", 1, "feed-token")]
    assert list(redis.z[nudge.DELETE_QUEUE_KEY]) == [f"{GROUP}:2"]


async def test_purge_retries_then_gives_up(redis, monkeypatch):
    async def _fail(method, payload, token=None):
        return None
    monkeypatch.setattr(telegram_service, "_call", _fail)
    now = time.time()
    redis.z[nudge.DELETE_QUEUE_KEY] = {f"{GROUP}:1": now - 60, f"{GROUP}:2": now - 2 * 3600}
    assert await nudge.purge_due_replies(redis) == 0
    # Yangisi keyinroq qayta urinish uchun qoladi, eskisi tashlanadi
    assert list(redis.z[nudge.DELETE_QUEUE_KEY]) == [f"{GROUP}:1"]
