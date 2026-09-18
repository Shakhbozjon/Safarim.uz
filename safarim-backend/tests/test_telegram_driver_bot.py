"""Haydovchi Telegram boti: safar e'lon qilish va bekor qilish.

Oqim: qachon → soat → narx → qaytish → tasdiq. Yo'nalish va o'rin soni
«doimiy yo'nalish» shablonidan olinadi, narx esa har safar so'raladi.

Tarmoqqa chiqilmaydi — `_call` monkeypatch qilinadi.
"""
import uuid
from datetime import date, time, timedelta

import pytest
from sqlalchemy import select

from app.models.enums import LuggageSize, PaymentType, TripStatus
from app.models.location import District, Region
from app.models.route import DriverRoute
from app.models.trip import Trip
from app.services import telegram_driver_bot as bot
from app.services import telegram_service

FARGONA, TOSHKENT = 401, 402
BUVAYDA = 4011
CHAT = 777000111
PRICE = 120000


@pytest.fixture
def sent(monkeypatch) -> list[dict]:
    calls: list[dict] = []

    async def _fake_call(method: str, payload: dict):
        calls.append({"method": method, **payload})
        return {"ok": True, "result": {"message_id": 500}}

    monkeypatch.setattr(telegram_service, "_call", _fake_call)
    return calls


def _texts(sent: list[dict]) -> str:
    return "\n".join(c.get("text", "") for c in sent)


def _buttons(sent: list[dict]) -> list[dict]:
    """Oxirgi xabardagi barcha inline tugmalar."""
    for call in reversed(sent):
        rows = (call.get("reply_markup") or {}).get("inline_keyboard")
        if rows:
            return [b for row in rows for b in row]
    return []


def _cq(data: str, message_id: int = 500) -> dict:
    return {"callback_query": {
        "id": "cb1",
        "data": data,
        "message": {"chat": {"id": CHAT, "type": "private"}, "message_id": message_id},
    }}


def _msg(text: str, reply_to: str | None = None) -> dict:
    message = {
        "chat": {"id": CHAT, "type": "private"},
        "from": {"id": 42},
        "text": text,
    }
    if reply_to is not None:
        message["reply_to_message"] = {"text": reply_to}
    return {"message": message}


async def _setup(db, driver_user, *, with_route=True, return_time=None) -> None:
    user, _dp = driver_user
    user.telegram_chat_id = str(CHAT)

    db.add_all([
        Region(id=FARGONA, name_uz="Farg'ona viloyati", name_ru="Фергана", slug="fargona-b", order=1),
        Region(id=TOSHKENT, name_uz="Toshkent shahri", name_ru="Ташкент", slug="toshkent-b", order=2),
    ])
    await db.flush()
    db.add(District(id=BUVAYDA, region_id=FARGONA, name_uz="Buvayda", name_ru="Бувайда", slug="buvayda-b"))

    if with_route:
        db.add(DriverRoute(
            id=uuid.uuid4(),
            driver_id=user.id,
            from_region_id=FARGONA,
            from_district_id=BUVAYDA,
            to_region_id=TOSHKENT,
            departure_time=time(8, 0),
            return_time=return_time,
            total_seats=4,
            price_per_seat=PRICE,
            payment_type=PaymentType.cash,
            luggage_size=LuggageSize.medium,
        ))
    await db.commit()


async def _open_trips(db, user) -> list[Trip]:
    rows = (await db.execute(select(Trip).where(Trip.driver_id == user.id))).scalars().all()
    return [t for t in rows if t.status in (TripStatus.active, TripStatus.full)]


# ─── Kirish huquqi ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_haydovchi_bolmagan_menyuni_ololmaydi(db, user, sent):
    """Oddiy yo'lovchi safar e'lon qila olmasin."""
    user.telegram_chat_id = str(CHAT)
    await db.commit()

    await telegram_service.handle_update(db, _msg(bot.MENU_PUBLISH))

    assert "tasdiqlangan haydovchilar uchun" in _texts(sent)
    assert _buttons(sent) == []


@pytest.mark.asyncio
async def test_start_haydovchiga_menyu_beradi(db, driver_user, sent):
    await _setup(db, driver_user)

    await telegram_service.handle_update(db, _msg("/start"))

    keyboards = [c.get("reply_markup", {}) for c in sent]
    assert any(bot.MENU_PUBLISH in str(k) for k in keyboards)


# ─── E'lon qilish oqimi ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_doimiy_yonalish_yoq_bolsa_belgilashni_taklif_qiladi(db, driver_user, sent):
    """Ilgari bu yerda «saytga kiring» deb yozilardi — endi shu yerda belgilanadi."""
    await _setup(db, driver_user, with_route=False)

    await telegram_service.handle_update(db, _msg(bot.MENU_PUBLISH))

    assert "doimiy yo'nalish" in _texts(sent)
    assert "uzsafar.uz" not in _texts(sent)
    assert [b["callback_data"] for b in _buttons(sent)] == ["rt:new"]


@pytest.mark.asyncio
async def test_birinchi_qadam_kun_soraydi(db, driver_user, sent):
    await _setup(db, driver_user)

    await telegram_service.handle_update(db, _msg(bot.MENU_PUBLISH))

    text = _texts(sent)
    assert "Buvayda" in text and "Toshkent shahri" in text
    btns = _buttons(sent)
    assert [b["callback_data"] for b in btns] == ["pb:t:0", "pb:t:1", "pb:t:2"]
    assert "Bugun" in btns[0]["text"] and "Ertaga" in btns[1]["text"]


@pytest.mark.asyncio
async def test_ikkinchi_qadam_odatdagi_vaqtni_belgilaydi(db, driver_user, sent):
    await _setup(db, driver_user)

    await telegram_service.handle_update(db, _cq("pb:t:1"))

    btns = _buttons(sent)
    marked = [b for b in btns if "✓" in b["text"]]
    assert len(marked) == 1, "shablondagi vaqt aynan bitta belgilansin"
    assert marked[0]["text"].startswith("08:00")
    assert marked[0]["callback_data"] == "pb:p:1:0800"


# ─── Narx ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_narx_soraladi_va_shablon_narxi_belgilanadi(db, driver_user, sent):
    await _setup(db, driver_user)

    await telegram_service.handle_update(db, _cq("pb:p:1:0800"))

    assert "qancha turadi" in _texts(sent)
    btns = _buttons(sent)
    marked = [b for b in btns if "✓" in b["text"]]
    assert len(marked) == 1
    assert marked[0]["callback_data"] == f"pb:r:1:0800:{PRICE}"
    # Shablon narxidan past va yuqori variantlar ham bo'lsin
    values = [int(b["callback_data"].split(":")[-1]) for b in btns
              if b["callback_data"].startswith("pb:r:")]
    assert min(values) < PRICE < max(values)
    assert any(b["callback_data"] == "pb:other:1:0800" for b in btns)


@pytest.mark.asyncio
async def test_qolda_yozilgan_narx_qabul_qilinadi(db, driver_user, sent):
    """«Boshqa narx» → force_reply; kontekst javob berilgan xabardan o'qiladi."""
    await _setup(db, driver_user)

    await telegram_service.handle_update(db, _cq("pb:other:1:0800"))
    prompt = sent[-1]
    assert prompt["reply_markup"]["force_reply"] is True
    sent.clear()

    await telegram_service.handle_update(db, _msg("155 000", reply_to=prompt["text"]))

    # Shablonda qaytish vaqti yo'q → to'g'ridan-to'g'ri tasdiq ekraniga
    assert "155 000" in _texts(sent)
    btns = _buttons(sent)
    assert btns[0]["callback_data"] == "pb:go:1:0800:155000:0:_", btns


@pytest.mark.asyncio
async def test_juda_kichik_narx_rad_etiladi(db, driver_user, sent):
    await _setup(db, driver_user)
    await telegram_service.handle_update(db, _cq("pb:other:1:0800"))
    prompt = sent[-1]
    sent.clear()

    await telegram_service.handle_update(db, _msg("500", reply_to=prompt["text"]))

    assert "kamida" in _texts(sent)
    assert _buttons(sent) == []


@pytest.mark.asyncio
async def test_raqamsiz_javob_rad_etiladi(db, driver_user, sent):
    await _setup(db, driver_user)
    await telegram_service.handle_update(db, _cq("pb:other:1:0800"))
    prompt = sent[-1]
    sent.clear()

    await telegram_service.handle_update(db, _msg("bilmadim", reply_to=prompt["text"]))

    assert "faqat raqam" in _texts(sent).lower()


# ─── Qaytish va tasdiq ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_qaytish_vaqti_yoq_bolsa_togri_tasdiqqa_otadi(db, driver_user, sent):
    """Ortiqcha bosish bo'lmasin: shablonda qaytish yo'q bo'lsa savol ham yo'q."""
    user, _ = driver_user
    await _setup(db, driver_user, return_time=None)

    await telegram_service.handle_update(db, _cq(f"pb:r:1:0800:{PRICE}"))

    assert "Tekshiring" in _texts(sent)
    btns = _buttons(sent)
    assert btns[0]["callback_data"] == f"pb:go:1:0800:{PRICE}:0:_"
    assert await _open_trips(db, user) == [], "tasdiqsiz e'lon qilinmasin"


@pytest.mark.asyncio
async def test_qaytish_vaqti_bor_bolsa_soraydi(db, driver_user, sent):
    await _setup(db, driver_user, return_time=time(16, 0))

    await telegram_service.handle_update(db, _cq(f"pb:r:1:0800:{PRICE}"))

    btns = _buttons(sent)
    assert [b["callback_data"] for b in btns] == [
        f"pb:c:1:0800:{PRICE}:1:_", f"pb:c:1:0800:{PRICE}:0:_",
    ]
    assert "16:00" in btns[0]["text"]


@pytest.mark.asyncio
async def test_tasdiq_ekranida_hammasi_korinadi(db, driver_user, sent):
    await _setup(db, driver_user, return_time=time(16, 0))

    await telegram_service.handle_update(db, _cq(f"pb:c:1:0800:155000:1"))

    text = _texts(sent)
    assert "Buvayda" in text and "Toshkent shahri" in text
    assert "Ertaga" in text and "08:00" in text
    assert "155 000" in text
    assert "16:00" in text          # qaytish
    codes = [b["callback_data"] for b in _buttons(sent)]
    assert codes == ["pb:qp:1:0800:155000", "pb:go:1:0800:155000:1:_", "pb:cancel"]


@pytest.mark.asyncio
async def test_bekor_tugmasi_elon_qilmaydi(db, driver_user, sent):
    user, _ = driver_user
    await _setup(db, driver_user)

    await telegram_service.handle_update(db, _cq("pb:cancel"))

    assert await _open_trips(db, user) == []
    assert _buttons(sent) == []


# ─── E'lon qilish ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tasdiqlangach_yozilgan_narx_bilan_elon_qilinadi(db, driver_user, sent):
    user, _ = driver_user
    await _setup(db, driver_user)

    await telegram_service.handle_update(db, _cq("pb:go:1:0800:155000:0"))

    trips = await _open_trips(db, user)
    assert len(trips) == 1
    assert trips[0].price_per_seat == 155000, "shablon narxi emas, yozilgani"
    assert "e'lon qilindi" in _texts(sent).lower()


@pytest.mark.asyncio
async def test_qaytish_bilan_ikki_safar_yaratiladi(db, driver_user, sent):
    user, _ = driver_user
    await _setup(db, driver_user, return_time=time(16, 0))

    await telegram_service.handle_update(db, _cq(f"pb:go:1:0800:{PRICE}:1"))

    trips = await _open_trips(db, user)
    assert len(trips) == 2
    # Qaytish — teskari yo'nalish
    assert {(t.from_region_id, t.to_region_id) for t in trips} == {
        (FARGONA, TOSHKENT), (TOSHKENT, FARGONA),
    }


@pytest.mark.asyncio
async def test_takroriy_safar_xatosi_korinadi(db, driver_user, sent):
    """Xato yutilmasin — haydovchi sababini o'qiy olsin."""
    user, _ = driver_user
    await _setup(db, driver_user)

    await telegram_service.handle_update(db, _cq(f"pb:go:1:0800:{PRICE}:0"))
    sent.clear()
    await telegram_service.handle_update(db, _cq(f"pb:go:1:0800:{PRICE}:0"))

    assert "allaqachon e'lon qilingan" in _texts(sent)
    assert len(await _open_trips(db, user)) == 1


# ─── Safarlarim va bekor qilish ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_safarlarim_royxati(db, driver_user, sent):
    await _setup(db, driver_user)
    await telegram_service.handle_update(db, _cq(f"pb:go:1:0800:{PRICE}:0"))
    sent.clear()

    await telegram_service.handle_update(db, _msg(bot.MENU_MY))

    btns = _buttons(sent)
    assert len(btns) == 1
    assert btns[0]["callback_data"].startswith("mt:v:")
    assert "Buvayda" in btns[0]["text"]


@pytest.mark.asyncio
async def test_bekor_qilish_tasdiq_soraydi_va_bajaradi(db, driver_user, sent):
    user, _ = driver_user
    await _setup(db, driver_user)
    await telegram_service.handle_update(db, _cq(f"pb:go:1:0800:{PRICE}:0"))
    trip = (await _open_trips(db, user))[0]
    sent.clear()

    await telegram_service.handle_update(db, _cq(f"mt:x:{trip.id}"))
    btns = _buttons(sent)
    assert [b["callback_data"] for b in btns] == [f"mt:xx:{trip.id}", f"mt:v:{trip.id}"]

    sent.clear()
    await telegram_service.handle_update(db, _cq(f"mt:xx:{trip.id}"))

    assert "bekor qilindi" in _texts(sent).lower()
    await db.refresh(trip)
    assert trip.status == TripStatus.cancelled


# ─── Telegram cheklovi ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_callback_data_64_baytdan_oshmaydi(db, driver_user, sent):
    """Holat `callback_data` ichida saqlanadi — Telegram chegarasi 64 bayt.

    Eng uzuni safar ID si bo'lgan tugma (`mt:xx:<uuid>`).
    """
    user, _ = driver_user
    await _setup(db, driver_user, return_time=time(16, 0))
    await telegram_service.handle_update(db, _cq(f"pb:go:1:0800:{PRICE}:1"))
    trip = (await _open_trips(db, user))[0]

    for update in (_msg(bot.MENU_PUBLISH), _cq("pb:t:1"), _cq("pb:p:1:0800"),
                   _cq(f"pb:r:1:0800:{PRICE}"), _cq(f"pb:c:1:0800:{PRICE}:1"),
                   _msg(bot.MENU_MY), _cq(f"mt:v:{trip.id}"),
                   _cq(f"mt:x:{trip.id}"), _cq(f"mt:s:{trip.id}")):
        sent.clear()
        await telegram_service.handle_update(db, update)
        for b in _buttons(sent):
            assert len(b["callback_data"].encode()) <= 64, b["callback_data"]


# ─── Safarni boshlash ────────────────────────────────────────────────────────

async def _book_one(db, passenger, trip) -> None:
    """Bitta tasdiqlangan yo'lovchi — «boshlash» aynan shunga bog'liq."""
    from app.schemas.booking import BookingCreate
    from app.models.enums import PaymentMethod
    from app.services import booking_service

    await booking_service.create_booking(db, passenger, BookingCreate(
        trip_id=trip.id, seats_count=1,
        payment_method=PaymentMethod.cash, pickup_address="Buvayda markazi",
    ))


@pytest.mark.asyncio
async def test_yolovchisiz_safarda_boshlash_tugmasi_yoq(db, driver_user, sent):
    user, _ = driver_user
    await _setup(db, driver_user)
    await telegram_service.handle_update(db, _cq(f"pb:go:1:0800:{PRICE}:0"))
    trip = (await _open_trips(db, user))[0]
    sent.clear()

    await telegram_service.handle_update(db, _cq(f"mt:v:{trip.id}"))

    codes = [b["callback_data"] for b in _buttons(sent)]
    assert f"mt:s:{trip.id}" not in codes
    assert f"mt:x:{trip.id}" in codes
    assert "boshlab bo'lmaydi" in _texts(sent)


@pytest.mark.asyncio
async def test_yolovchi_bor_safarda_boshlash_tugmasi_chiqadi(db, user, driver_user, sent):
    driver, _ = driver_user
    await _setup(db, driver_user)
    await telegram_service.handle_update(db, _cq(f"pb:go:1:0800:{PRICE}:0"))
    trip = (await _open_trips(db, driver))[0]
    await _book_one(db, user, trip)
    sent.clear()

    await telegram_service.handle_update(db, _cq(f"mt:v:{trip.id}"))

    text = _texts(sent)
    assert "1 ta yo'lovchi" in text
    codes = [b["callback_data"] for b in _buttons(sent)]
    assert codes[0] == f"mt:s:{trip.id}"


@pytest.mark.asyncio
async def test_boshlashdan_oldin_ogohlantiradi_va_bajaradi(db, user, driver_user, sent):
    driver, _ = driver_user
    await _setup(db, driver_user)
    await telegram_service.handle_update(db, _cq(f"pb:go:1:0800:{PRICE}:0"))
    trip = (await _open_trips(db, driver))[0]
    await _book_one(db, user, trip)
    sent.clear()

    await telegram_service.handle_update(db, _cq(f"mt:s:{trip.id}"))
    # Saytdagi tasdiq oynasi bilan bir xil ogohlantirish
    assert "qidiruvdan olib tashlanadi" in _texts(sent)
    codes = [b["callback_data"] for b in _buttons(sent)]
    assert codes == [f"mt:ss:{trip.id}", f"mt:v:{trip.id}"]

    sent.clear()
    await telegram_service.handle_update(db, _cq(f"mt:ss:{trip.id}"))

    assert "boshlandi" in _texts(sent).lower()
    await db.refresh(trip)
    assert trip.status == TripStatus.started


@pytest.mark.asyncio
async def test_boshlangan_safarda_amallar_yopiladi(db, user, driver_user, sent):
    """Yo'lga chiqqan safarni bekor qilib ham, qayta boshlab ham bo'lmaydi."""
    driver, _ = driver_user
    await _setup(db, driver_user)
    await telegram_service.handle_update(db, _cq(f"pb:go:1:0800:{PRICE}:0"))
    trip = (await _open_trips(db, driver))[0]
    await _book_one(db, user, trip)
    await telegram_service.handle_update(db, _cq(f"mt:ss:{trip.id}"))
    sent.clear()

    await telegram_service.handle_update(db, _cq(f"mt:v:{trip.id}"))

    assert "Yo'ldasiz" in _texts(sent)
    codes = [b["callback_data"] for b in _buttons(sent)]
    assert codes == ["mt:list"]


@pytest.mark.asyncio
async def test_boshlash_xatosi_korinadi(db, driver_user, sent):
    """Yo'lovchisiz boshlashga urinilsa sabab ko'rsatiladi (tugma o'tkazib yuborilgan holat)."""
    driver, _ = driver_user
    await _setup(db, driver_user)
    await telegram_service.handle_update(db, _cq(f"pb:go:1:0800:{PRICE}:0"))
    trip = (await _open_trips(db, driver))[0]
    sent.clear()

    await telegram_service.handle_update(db, _cq(f"mt:ss:{trip.id}"))

    assert "yo'lovchi yo'q" in _texts(sent).lower()
    await db.refresh(trip)
    assert trip.status == TripStatus.active


# ─── Qaytish narxi ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tasdiqda_qaytish_safari_toliq_korinadi(db, driver_user, sent):
    """Qaytish yo'nalishi, SANASI va narxi ham ko'rsatilsin — u ham e'lon qilinadi."""
    await _setup(db, driver_user, return_time=time(16, 0))

    await telegram_service.handle_update(db, _cq("pb:c:1:0800:155000:1:_"))

    text = _texts(sent)
    assert "Qaytish safari" in text
    assert "Toshkent shahri → Buvayda" in text, "teskari yo'nalish ko'rsatilsin"
    assert text.count("155 000") == 2, "qaytish narxi ham yozilsin"


@pytest.mark.asyncio
async def test_qaytish_ertaga_tushsa_sanasi_korinadi(db, driver_user, sent):
    """Qaytish vaqti borishdan kichik → ertangi kun. Haydovchi buni bilsin."""
    await _setup(db, driver_user, return_time=time(6, 0))

    await telegram_service.handle_update(db, _cq("pb:c:0:1800:150000:1:_"))

    text = _texts(sent)
    # Borish bugun, qaytish esa ertaga
    assert "Bugun" in text and "Ertaga" in text


@pytest.mark.asyncio
async def test_qaytish_narxini_ozgartirish_mumkin(db, driver_user, sent):
    await _setup(db, driver_user, return_time=time(16, 0))

    await telegram_service.handle_update(db, _cq("pb:qp:1:0800:150000"))
    btns = _buttons(sent)
    marked = [b for b in btns if "✓" in b["text"]]
    assert marked[0]["callback_data"] == "pb:c:1:0800:150000:1:150000"
    assert any(b["callback_data"] == "pb:qo:1:0800:150000" for b in btns)

    sent.clear()
    await telegram_service.handle_update(db, _cq("pb:c:1:0800:150000:1:130000"))

    text = _texts(sent)
    assert "150 000" in text and "130 000" in text
    codes = [b["callback_data"] for b in _buttons(sent)]
    assert "pb:go:1:0800:150000:1:130000" in codes


@pytest.mark.asyncio
async def test_qolda_yozilgan_qaytish_narxi(db, driver_user, sent):
    await _setup(db, driver_user, return_time=time(16, 0))

    await telegram_service.handle_update(db, _cq("pb:qo:1:0800:150000"))
    prompt = sent[-1]
    assert prompt["reply_markup"]["force_reply"] is True
    sent.clear()

    await telegram_service.handle_update(db, _msg("135 000", reply_to=prompt["text"]))

    assert "135 000" in _texts(sent)
    codes = [b["callback_data"] for b in _buttons(sent)]
    assert "pb:go:1:0800:150000:1:135000" in codes


@pytest.mark.asyncio
async def test_qaytish_narxi_safarga_yetib_boradi(db, driver_user, sent):
    """Tanlangan qaytish narxi haqiqatan qaytish safariga yoziladi."""
    user, _ = driver_user
    await _setup(db, driver_user, return_time=time(16, 0))

    await telegram_service.handle_update(db, _cq("pb:go:1:0800:150000:1:130000"))

    trips = await _open_trips(db, user)
    assert len(trips) == 2
    forward = next(t for t in trips if t.from_region_id == FARGONA)
    backward = next(t for t in trips if t.from_region_id == TOSHKENT)
    assert forward.price_per_seat == 150000
    assert backward.price_per_seat == 130000


@pytest.mark.asyncio
async def test_qaytish_narxi_berilmasa_borish_narxi_qolladi(db, driver_user, sent):
    user, _ = driver_user
    await _setup(db, driver_user, return_time=time(16, 0))

    await telegram_service.handle_update(db, _cq("pb:go:1:0800:150000:1:_"))

    trips = await _open_trips(db, user)
    assert {t.price_per_seat for t in trips} == {150000}
