"""Guruhda e'lon tashlagan haydovchiga «botdan bering» degan javob.

Lenta boti (@UzsafarElonlar_bot) guruhlarda admin — shuning uchun guruhdagi
barcha xabarlarni ko'radi. Haydovchi e'loniga o'xshagan xabar kelsa, uning
ostiga qisqa javob va «Bot orqali e'lon berish» tugmasi yoziladi.

Guruhni bezovta qilmaslik uchun qoidalar (hammasi birga ishlaydi):
  * sukut bo'yicha O'CHIQ — `TELEGRAM_FEED_NUDGE_ENABLED=true` qo'yilmaguncha
    hech narsa yozilmaydi;
  * faqat sozlangan e'lon guruhlarida (`trips_chat_ids`);
  * bitta odamga kuniga 1 marta;
  * bitta guruhga soatiga ko'pi bilan `GROUP_LIMIT_PER_HOUR` ta;
  * UzSafar'dagi haydovchiga (ariza bergan ham) va adminga yozilmaydi;
  * javob `DELETE_AFTER_SEC` dan keyin o'chiriladi (Celery beat);
  * Redis ishlamasa — yozilmaydi (cheklov ishlamay qolib spam bo'lgandan,
    bir kun jim turgan yaxshi).

Aniqlash ataylab ehtiyotkor: yo'lovchi e'loni («mashina kerak», «kim
ketyapti») haydovchiniki deb olinmasin. Shubhali xabarda jim turiladi.
"""
from __future__ import annotations

import logging
import re
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis_client import get_redis
from app.models.driver import DriverProfile
from app.models.user import User
from app.services import telegram_service as tg

logger = logging.getLogger(__name__)

USER_COOLDOWN_SEC = 24 * 3600
GROUP_LIMIT_PER_HOUR = 20
DELETE_AFTER_SEC = 10 * 60
# O'chirib bo'lmagan javob (tarmoq xatosi va h.k.) shuncha vaqt qayta
# urinib turiladi, keyin navbatdan tashlanadi.
_RETRY_FOR_SEC = 3600

DELETE_QUEUE_KEY = "feednudge:delete"

# ─── Aniqlash ────────────────────────────────────────────────────────────────

# Apostrof har xil yoziladi (o', o‘, oʻ, o`) yoki umuman yozilmaydi —
# hammasini olib tashlab solishtiramiz: «yo'lovchi» → «yolovchi».
_APOSTROPHES = re.compile(r"['’‘ʻʼ`´ʹ]")
_SPACES = re.compile(r"\s+")

# Shahar/viloyat nomining boshi: «toshkentdan», «toshkentga» ham mos keladi
_PLACES = (
    # lotin
    "toshkent", "tashkent", "samarqand", "samarkand", "buxoro", "bukhara",
    "fargona", "fergana", "andijon", "andijan", "namangan", "qoqon", "kokand",
    "margilon", "jizzax", "jizzak", "navoiy", "navoi", "qarshi", "karshi",
    "termiz", "termez", "urganch", "urgench", "xiva", "nukus", "guliston",
    "sirdaryo", "xorazm", "surxondaryo", "qashqadaryo", "qoraqalpog",
    "chirchiq", "olmaliq", "angren", "zarafshon", "denov", "shahrisabz",
    "kosonsoy", "chust", "yangiyer", "bekobod", "uchqorgon", "rishton",
    # kirill (o'zbek va rus)
    "тошкент", "ташкент", "самарқанд", "самарканд", "бухоро", "бухара",
    "фарғона", "фаргона", "фергана", "андижон", "андижан", "наманган",
    "қўқон", "кўкон", "коканд", "марғилон", "маргилан", "жиззах", "джизак",
    "навоий", "навои", "қарши", "карши", "термиз", "термез", "урганч",
    "ургенч", "хива", "нукус", "гулистон", "гулистан", "сирдарё", "хоразм",
    "сурхондарё", "қашқадарё", "қорақалпоғ", "чирчиқ", "чирчик", "олмалиқ",
    "алмалык", "ангрен", "зарафшон", "денов", "шаҳрисабз", "шахрисабз",
)

# Haydovchi yozadigan iboralar (apostrofsiz)
_DRIVER_WORDS = (
    "joy bor", "joylar bor", "joyim bor", "bosh joy", "orin bor", "joy qoldi",
    "yolovchi olaman", "yolovchi olamiz", "yolovchi kerak", "yolovchilar kerak",
    "yolovchi bormi", "pochta olaman", "pochta olamiz", "pochta ham olaman",
    "ketaman", "ketamiz", "ketyapman", "ketyapmiz", "ketvomman", "ketvommiz",
    "jonayman", "jonaymiz", "chiqaman", "chiqamiz",
    "жой бор", "жойлар бор", "бўш жой", "буш жой", "ўрин бор",
    "йўловчи оламан", "йўловчи керак", "йуловчи керак", "йўловчи борми",
    "почта оламан", "кетаман", "кетамиз", "кетяпман", "жўнайман", "чиқаман",
    "есть места", "есть место", "свободные места", "свободное место",
    "возьму пассаж", "беру пассаж", "возьму попут", "беру попут", "выезжаю",
)

# Yo'lovchi yozadigan iboralar — bittasi bo'lsa ham javob yozilmaydi
_PASSENGER_WORDS = (
    "mashina kerak", "moshina kerak", "mashina bormi", "moshina bormi",
    "taksi kerak", "haydovchi kerak", "joy bormi", "kim bor", "kim ketyapti",
    "kim ketadi", "ketadigan bormi", "ketadiganlar bormi", "boradigan bormi",
    "olib ketadigan", "kishi bor", "kishimiz", "odam bor", "odammiz",
    "машина керак", "мошина керак", "машина борми", "такси керак",
    "ҳайдовчи керак", "хайдовчи керак", "жой борми", "ким бор", "ким кетяпти",
    "кетадиган борми", "олиб кетадиган", "киши бор", "кишимиз",
    "нужна машина", "нужен водитель", "нужно такси", "ищу машину",
    "ищу водителя", "кто едет", "есть кто",
)

_PHONE = re.compile(r"(?:\+?998[\s\-]?)?\(?\d{2}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")


def _normalize(text: str) -> str:
    return _SPACES.sub(" ", _APOSTROPHES.sub("", (text or "").lower()))


def looks_like_driver_ad(text: str) -> bool:
    """Xabar haydovchi e'loniga o'xshaydimi.

    Kerak: haydovchi iborasi + (shahar nomi yoki telefon raqami) va birorta
    ham yo'lovchi iborasi bo'lmasligi.
    """
    if not text or not (15 <= len(text) <= 2000):
        return False
    t = _normalize(text)
    if any(w in t for w in _PASSENGER_WORDS):
        return False
    if not any(w in t for w in _DRIVER_WORDS):
        return False
    return any(p in t for p in _PLACES) or bool(_PHONE.search(text))


# ─── Guruh xabarini qayta ishlash ────────────────────────────────────────────

def is_enabled() -> bool:
    return bool(
        settings.TELEGRAM_FEED_NUDGE_ENABLED
        and settings.TELEGRAM_FEED_BOT_TOKEN
        and settings.TELEGRAM_BOT_USERNAME
        and tg.trips_chat_ids()
    )


def _is_plain_post(message: dict) -> bool:
    """Odam o'zi yozgan oddiy xabar: bot, kanal, uzatilgan yoki javob emas."""
    sender = message.get("from") or {}
    if not sender.get("id") or sender.get("is_bot"):
        return False
    # Anonim admin yoki kanal nomidan yozilgan
    if message.get("sender_chat"):
        return False
    # Uzatilgan xabar — muallif boshqa odam bo'lishi mumkin
    if message.get("forward_origin") or message.get("forward_date") or message.get("via_bot"):
        return False
    reply = message.get("reply_to_message")
    if reply:
        # Mavzuli guruhda har xabar mavzu boshiga «javob» bo'lib keladi
        is_topic_root = (
            message.get("is_topic_message")
            and reply.get("message_id") == message.get("message_thread_id")
        )
        if not is_topic_root:
            return False
    return True


async def _is_known_driver_or_admin(db: AsyncSession, tg_user_id: int) -> bool:
    """UzSafar'da haydovchi (ariza bergan ham) yoki admin — unga yozilmaydi."""
    row = (await db.execute(
        select(User.is_admin, DriverProfile.id)
        .outerjoin(DriverProfile, DriverProfile.user_id == User.id)
        .where(User.telegram_chat_id == str(tg_user_id))
    )).first()
    if row is None:
        return False
    is_admin, driver_profile_id = row
    return bool(is_admin) or driver_profile_id is not None


async def _take_slot(chat_id: str, tg_user_id: int) -> bool:
    """Cheklovlardan o'tadimi. Redis xatosida — yo'q (yozilmaydi)."""
    r = get_redis()
    try:
        hour = int(time.time() // 3600)
        group_key = f"feednudge:g:{chat_id}:{hour}"
        count = await r.incr(group_key)
        if count == 1:
            await r.expire(group_key, 3600)
        if count > GROUP_LIMIT_PER_HOUR:
            return False
        # Kuniga bir marta: kalit faqat yo'q bo'lsa qo'yiladi
        return bool(await r.set(f"feednudge:u:{tg_user_id}", "1", nx=True, ex=USER_COOLDOWN_SEC))
    except Exception as exc:
        logger.warning("Guruh javobi: Redis xatosi, yozilmadi: %s", exc)
        return False


def _reply_text(first_name: str) -> str:
    name = tg._esc((first_name or "").strip()[:32])
    hello = f"👋 {name}, " if name else "👋 "
    return (
        f"{hello}bu e'lonni <b>UzSafar</b> boti orqali bersangiz, u shu guruhga ham, "
        "uzsafar.uz saytiga ham tushadi — yo'lovchi qo'ng'iroqsiz o'zi joy band qiladi.\n"
        "Ro'yxatdan o'tish bir daqiqa, bepul."
    )


def _reply_payload(message: dict) -> dict:
    chat_id = str(message["chat"]["id"])
    payload: dict = {
        "chat_id": chat_id,
        "text": _reply_text((message.get("from") or {}).get("first_name", "")),
        "parse_mode": "HTML",
        "disable_notification": True,
        "link_preview_options": {"is_disabled": True},
        "reply_parameters": {
            "message_id": message["message_id"],
            "allow_sending_without_reply": True,
        },
        "reply_markup": {"inline_keyboard": [[{
            "text": "🚗 Bot orqali e'lon berish",
            "url": f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start=haydovchi",
        }]]},
    }
    if message.get("is_topic_message") and message.get("message_thread_id"):
        payload["message_thread_id"] = message["message_thread_id"]
    return payload


async def _send_reply(payload: dict) -> None:
    data = await tg._call("sendMessage", payload, token=settings.TELEGRAM_FEED_BOT_TOKEN)
    if not (data and data.get("ok")):
        return
    message_id = (data.get("result") or {}).get("message_id")
    if not message_id:
        return
    try:
        await get_redis().zadd(
            DELETE_QUEUE_KEY,
            {f"{payload['chat_id']}:{message_id}": time.time() + DELETE_AFTER_SEC},
        )
    except Exception as exc:
        logger.warning("Guruh javobi o'chirish navbatiga qo'yilmadi: %s", exc)


async def handle_group_update(db: AsyncSession, update: dict) -> bool:
    """Lenta boti webhook'idan kelgan yangilanish. Javob navbatga qo'yilsa True."""
    if not is_enabled():
        return False
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    if chat.get("type") not in ("group", "supergroup"):
        return False
    if str(chat.get("id")) not in tg.trips_chat_ids():
        return False
    if not message.get("message_id") or not _is_plain_post(message):
        return False
    if not looks_like_driver_ad(message.get("text") or message.get("caption") or ""):
        return False

    tg_user_id = int(message["from"]["id"])
    if await _is_known_driver_or_admin(db, tg_user_id):
        return False
    if not await _take_slot(str(chat["id"]), tg_user_id):
        return False

    # Telegramga murojaat webhook javobini kechiktirmasin
    payload = _reply_payload(message)
    tg._queue(lambda: _send_reply(payload), delay=0)
    return True


# ─── Eskirgan javoblarni o'chirish (Celery beat) ─────────────────────────────

async def purge_due_replies(redis_client) -> int:
    """Vaqti kelgan javoblarni guruhdan o'chiradi, nechtasi o'chganini qaytaradi.

    Redis mijozi tashqaridan beriladi: Celery har vazifada yangi event loop
    ochadi, umumiy mijoz esa eski loop'ga bog'langan bo'lardi.
    """
    if not settings.TELEGRAM_FEED_BOT_TOKEN:
        return 0
    now = time.time()
    due = await redis_client.zrangebyscore(DELETE_QUEUE_KEY, "-inf", now, start=0, num=100, withscores=True)
    deleted = 0
    for member, score in due:
        member = member.decode() if isinstance(member, bytes) else member
        chat_id, _, message_id = member.rpartition(":")
        if not chat_id or not message_id.isdigit():
            await redis_client.zrem(DELETE_QUEUE_KEY, member)
            continue
        data = await tg._call("deleteMessage", {
            "chat_id": chat_id, "message_id": int(message_id),
        }, token=settings.TELEGRAM_FEED_BOT_TOKEN)
        if data and data.get("ok"):
            deleted += 1
            await redis_client.zrem(DELETE_QUEUE_KEY, member)
        elif now - float(score) > _RETRY_FOR_SEC:
            # Bir soat urinildi: xabarni kimdir allaqachon o'chirgan yoki bot
            # guruhdan chiqarilgan — navbatni band qilib turmasin
            await redis_client.zrem(DELETE_QUEUE_KEY, member)
    return deleted
