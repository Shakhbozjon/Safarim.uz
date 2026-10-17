"""Telegram Mini App — foydalanuvchini Telegram imzosi bo'yicha tanish.

Mini App ochilganda Telegram sahifaga `initData` beradi: foydalanuvchi
ma'lumoti va shu ma'lumotning BOT TOKENI bilan qo'yilgan HMAC imzosi.
Imzoni faqat bot tokeni egasi (ya'ni biz) tekshira oladi, shuning uchun
sahifaning o'zi «men falonchiman» deb aldab bo'lmaydi.

Tekshiruv tartibi Telegram hujjatidagidek:
  secret = HMAC_SHA256(key="WebAppData", msg=bot_token)
  hash   = hex(HMAC_SHA256(key=secret, msg=data_check_string))
bu yerda data_check_string — `hash` dan boshqa barcha maydonlar, kalit
bo'yicha saralangan, `kalit=qiymat` ko'rinishida, `\\n` bilan ulangan.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

# Eski initData'ni qayta ishlatib bo'lmasin. Mini App odatda bir necha
# daqiqa ochiq turadi; sutka — Telegram hujjatidagi odatiy chegara.
MAX_AGE_SECONDS = 24 * 3600


def verify_init_data(init_data: str, bot_token: str, now: float | None = None) -> dict | None:
    """Imzo to'g'ri va eskirmagan bo'lsa — Telegram foydalanuvchisi (dict), aks holda None."""
    if not init_data or not bot_token or len(init_data) > 4096:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError:
        return None

    received = pairs.pop("hash", None)
    if not received:
        return None

    check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    # Baytlar bilan — qiymat mijozdan keladi, ASCII bo'lmasa str'da TypeError bo'lardi
    if not hmac.compare_digest(expected.encode(), received.encode()):
        return None

    try:
        auth_date = int(pairs.get("auth_date", "0"))
    except ValueError:
        return None
    if (now or time.time()) - auth_date > MAX_AGE_SECONDS:
        return None

    try:
        user = json.loads(pairs.get("user") or "")
    except ValueError:
        return None
    if not isinstance(user, dict) or not isinstance(user.get("id"), int):
        return None
    user["_start_param"] = pairs.get("start_param") or ""
    return user
