"""Doimiy yo'nalishni Telegram botdan belgilash.

Bu oqim e'lon qilishning shartidir: yo'nalish bo'lmasa bot safar qo'ya
olmaydi. Ilgari uni faqat saytdan belgilash mumkin edi.

Tarmoqqa chiqilmaydi — `_call` monkeypatch qilinadi.
"""
import uuid
from datetime import time

import pytest
from sqlalchemy import select

from app.models.enums import LuggageSize, PaymentType
from app.models.location import District, Region
from app.models.route import DriverRoute
from app.services import telegram_driver_bot as bot
from app.services import telegram_route_setup as rt
from app.services import telegram_service

FARGONA, TOSHKENT, SAMARQAND = 801, 802, 803
BUVAYDA, QOQON = 8011, 8012
CHILONZOR = 8021
CHAT = 555777999


@pytest.fixture
def sent(monkeypatch) -> list[dict]:
    calls: list[dict] = []

    async def _fake_call(method: str, payload: dict):
        calls.append({"method": method, **payload})
        return {"ok": True, "result": {"message_id": 900}}

    monkeypatch.setattr(telegram_service, "_call", _fake_call)
    return calls


def _texts(sent) -> str:
    return "\n".join(c.get("text", "") for c in sent)


def _buttons(sent) -> list[dict]:
    for call in reversed(sent):
        rows = (call.get("reply_markup") or {}).get("inline_keyboard")
        if rows:
            return [b for row in rows for b in row]
    return []


def _codes(sent) -> list[str]:
    return [b["callback_data"] for b in _buttons(sent)]


def _cq(data: str) -> dict:
    return {"callback_query": {
        "id": "cb1", "data": data,
        "message": {"chat": {"id": CHAT, "type": "private"}, "message_id": 900},
    }}


def _msg(text: str, reply_to: str | None = None) -> dict:
    message = {"chat": {"id": CHAT, "type": "private"}, "from": {"id": 7}, "text": text}
    if reply_to is not None:
        message["reply_to_message"] = {"text": reply_to}
    return {"message": message}


async def _setup(db, driver_user) -> None:
    user, _dp = driver_user
    user.telegram_chat_id = str(CHAT)
    db.add_all([
        Region(id=FARGONA, name_uz="Farg'ona viloyati", name_ru="Фергана", slug="f-r", order=1),
        Region(id=TOSHKENT, name_uz="Toshkent shahri", name_ru="Ташкент", slug="t-r", order=2),
        Region(id=SAMARQAND, name_uz="Samarqand viloyati", name_ru="Самарканд", slug="s-r", order=3),
    ])
    await db.flush()
    db.add_all([
        District(id=BUVAYDA, region_id=FARGONA, name_uz="Buvayda", name_ru="Бувайда", slug="d-b"),
        District(id=QOQON, region_id=FARGONA, name_uz="Qo'qon shahri", name_ru="Коканд", slug="d-q"),
        District(id=CHILONZOR, region_id=TOSHKENT, name_uz="Chilonzor", name_ru="Чиланзар", slug="d-c"),
    ])
    await db.commit()


async def _route(db, user) -> DriverRoute | None:
    return (await db.execute(
        select(DriverRoute).where(DriverRoute.driver_id == user.id)
    )).scalar_one_or_none()


# ─── Kirish nuqtalari ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_yonalish_yoq_bolsa_menyu_belgilashni_taklif_qiladi(db, driver_user, sent):
    await _setup(db, driver_user)

    await telegram_service.handle_update(db, _msg(bot.MENU_ROUTE))

    assert "belgilanmagan" in _texts(sent)
    assert _codes(sent) == ["rt:new"]


@pytest.mark.asyncio
async def test_mavjud_yonalish_korsatiladi(db, driver_user, sent):
    user, _ = driver_user
    await _setup(db, driver_user)
    db.add(DriverRoute(
        id=uuid.uuid4(), driver_id=user.id,
        from_region_id=FARGONA, from_district_id=BUVAYDA,
        to_region_id=TOSHKENT, departure_time=time(8, 0), return_time=time(16, 0),
        total_seats=4, price_per_seat=150000,
        payment_type=PaymentType.cash, luggage_size=LuggageSize.medium,
    ))
    await db.commit()

    await telegram_service.handle_update(db, _msg(bot.MENU_ROUTE))

    text = _texts(sent)
    assert "Buvayda" in text and "Toshkent shahri" in text
    assert "150 000" in text and "08:00" in text and "16:00" in text
    assert "rt:new" in _codes(sent)


# ─── Qadamlar ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_viloyatlar_royxati(db, driver_user, sent):
    await _setup(db, driver_user)

    await telegram_service.handle_update(db, _cq("rt:new"))

    codes = _codes(sent)
    assert f"rt:fd:{FARGONA}" in codes and f"rt:fd:{TOSHKENT}" in codes


@pytest.mark.asyncio
async def test_tumanlar_va_butun_viloyat(db, driver_user, sent):
    await _setup(db, driver_user)

    await telegram_service.handle_update(db, _cq(f"rt:fd:{FARGONA}"))

    codes = _codes(sent)
    assert f"rt:tr:{FARGONA}:{BUVAYDA}" in codes
    assert f"rt:tr:{FARGONA}:{QOQON}" in codes
    assert f"rt:tr:{FARGONA}:_" in codes, "butun viloyat varianti bo'lsin"
    # Boshqa viloyat tumani aralashmasin
    assert f"rt:tr:{FARGONA}:{CHILONZOR}" not in codes


@pytest.mark.asyncio
async def test_ozidan_oziga_safar_taklif_qilinmaydi(db, driver_user, sent):
    """Jo'nash viloyati «qayerga» ro'yxatida turmasin."""
    await _setup(db, driver_user)

    await telegram_service.handle_update(db, _cq(f"rt:tr:{FARGONA}:{BUVAYDA}"))

    codes = _codes(sent)
    assert not any(c.endswith(f":{FARGONA}") for c in codes)
    assert f"rt:td:{FARGONA}:{BUVAYDA}:{TOSHKENT}" in codes


@pytest.mark.asyncio
async def test_orin_soni_mashinaga_qarab_cheklanadi(db, driver_user, sent):
    """4 o'rinli mashinada 5 ta variant chiqmasin."""
    await _setup(db, driver_user)

    await telegram_service.handle_update(
        db, _cq(f"rt:st:{FARGONA}:{BUVAYDA}:{TOSHKENT}:_"))

    codes = _codes(sent)
    assert len(codes) == 4                       # conftest: vehicle_seats = 4
    assert codes[-1].endswith(":4")


@pytest.mark.asyncio
async def test_narx_variantlari_va_qolda_yozish(db, driver_user, sent):
    await _setup(db, driver_user)

    await telegram_service.handle_update(
        db, _cq(f"rt:pr:{FARGONA}:{BUVAYDA}:{TOSHKENT}:_:4"))

    codes = _codes(sent)
    assert any(c.startswith("rt:dt:") for c in codes)
    assert f"rt:po:{FARGONA}:{BUVAYDA}:{TOSHKENT}:_:4" in codes


@pytest.mark.asyncio
async def test_vaqtni_otkazib_yuborish_mumkin(db, driver_user, sent):
    await _setup(db, driver_user)

    await telegram_service.handle_update(
        db, _cq(f"rt:dt:{FARGONA}:{BUVAYDA}:{TOSHKENT}:_:4:150000"))
    assert any(c.endswith(":_") for c in _codes(sent)), "«aniq vaqtim yo'q» bo'lsin"

    sent.clear()
    await telegram_service.handle_update(
        db, _cq(f"rt:rt:{FARGONA}:{BUVAYDA}:{TOSHKENT}:_:4:150000:_"))
    assert any(c.endswith(":_") for c in _codes(sent)), "«qaytish yo'q» bo'lsin"


# ─── Saqlash ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tasdiqdan_keyin_saqlanadi(db, driver_user, sent):
    user, _ = driver_user
    await _setup(db, driver_user)
    state = f"{FARGONA}:{BUVAYDA}:{TOSHKENT}:_:4:150000:0800:1600"

    await telegram_service.handle_update(db, _cq(f"rt:ok:{state}"))
    text = _texts(sent)
    assert "Buvayda" in text and "150 000" in text and "08:00" in text
    assert _codes(sent)[0] == f"rt:go:{state}"
    assert await _route(db, user) is None, "tasdiqsiz saqlanmasin"

    sent.clear()
    await telegram_service.handle_update(db, _cq(f"rt:go:{state}"))

    route = await _route(db, user)
    assert route is not None
    assert (route.from_region_id, route.from_district_id) == (FARGONA, BUVAYDA)
    assert (route.to_region_id, route.to_district_id) == (TOSHKENT, None)
    assert route.total_seats == 4
    assert route.price_per_seat == 150000
    assert route.departure_time == time(8, 0)
    assert route.return_time == time(16, 0)
    # Saqlagach darrov e'lon qilishga o'tish taklif qilinadi
    assert "pb:day" in _codes(sent)


@pytest.mark.asyncio
async def test_mavjud_yonalish_ustiga_yoziladi(db, driver_user, sent):
    """Haydovchida bitta yo'nalish — ikkinchisi qo'shilib ketmasin."""
    user, _ = driver_user
    await _setup(db, driver_user)
    await telegram_service.handle_update(
        db, _cq(f"rt:go:{FARGONA}:{BUVAYDA}:{TOSHKENT}:_:4:150000:0800:1600"))

    await telegram_service.handle_update(
        db, _cq(f"rt:go:{FARGONA}:{QOQON}:{SAMARQAND}:_:3:90000:_:_"))

    routes = (await db.execute(
        select(DriverRoute).where(DriverRoute.driver_id == user.id)
    )).scalars().all()
    assert len(routes) == 1
    assert routes[0].from_district_id == QOQON
    assert routes[0].to_region_id == SAMARQAND
    assert routes[0].departure_time is None


@pytest.mark.asyncio
async def test_bir_xil_yonalish_rad_etiladi(db, driver_user, sent):
    """Qoida `route_service` da — bot uni takrorlamaydi, xatoni ko'rsatadi."""
    user, _ = driver_user
    await _setup(db, driver_user)

    await telegram_service.handle_update(
        db, _cq(f"rt:go:{FARGONA}:{BUVAYDA}:{FARGONA}:{BUVAYDA}:4:150000:_:_"))

    assert "bir xil" in _texts(sent)
    assert await _route(db, user) is None


@pytest.mark.asyncio
async def test_qolda_yozilgan_narx_qabul_qilinadi(db, driver_user, sent):
    await _setup(db, driver_user)

    await telegram_service.handle_update(
        db, _cq(f"rt:po:{FARGONA}:{BUVAYDA}:{TOSHKENT}:_:4"))
    prompt = sent[-1]
    assert prompt["reply_markup"]["force_reply"] is True
    sent.clear()

    await telegram_service.handle_update(db, _msg("155 000", reply_to=prompt["text"]))

    # Narxdan keyin jo'nash vaqti so'raladi, narx esa holatda saqlanadi
    codes = _codes(sent)
    assert any(":155000:" in c for c in codes), codes


# ─── Telegram cheklovi ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_callback_data_64_baytdan_oshmaydi(db, driver_user, sent):
    await _setup(db, driver_user)
    steps = [
        "rt:new",
        f"rt:fd:{FARGONA}",
        f"rt:tr:{FARGONA}:{BUVAYDA}",
        f"rt:td:{FARGONA}:{BUVAYDA}:{TOSHKENT}",
        f"rt:st:{FARGONA}:{BUVAYDA}:{TOSHKENT}:{CHILONZOR}",
        f"rt:pr:{FARGONA}:{BUVAYDA}:{TOSHKENT}:{CHILONZOR}:4",
        f"rt:dt:{FARGONA}:{BUVAYDA}:{TOSHKENT}:{CHILONZOR}:4:150000",
        f"rt:rt:{FARGONA}:{BUVAYDA}:{TOSHKENT}:{CHILONZOR}:4:150000:0800",
        f"rt:ok:{FARGONA}:{BUVAYDA}:{TOSHKENT}:{CHILONZOR}:4:150000:0800:1600",
    ]
    for step in steps:
        sent.clear()
        await telegram_service.handle_update(db, _cq(step))
        for b in _buttons(sent):
            assert len(b["callback_data"].encode()) <= 64, b["callback_data"]
