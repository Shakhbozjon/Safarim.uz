"""Bir kunda bir yo'nalishda ikkinchi safar — ogohlantirish bilan.

User jonli saytda ko'rdi (2026-09-18): botdan Farg'ona → Toshkent 10:00 ga
e'lon qilgan, keyin o'sha kunga yana 11:00 ga e'lon qilgan va bot hech narsa
demay qabul qilgan. Haydovchi bir kunda Farg'onadan Toshkentga ikki marta
bora olmaydi — bu deyarli har doim tasodifiy takror.

To'sib qo'yilmaydi: qisqa yo'lda (Farg'ona → Qo'qon) ikki reys haqiqatan
bo'ladi. Shuning uchun 409 va tasdiq — kodda tanlangan boshqa shunga o'xshash
holatlar kabi.
"""
import uuid
from datetime import date, time, timedelta

import pytest
from fastapi import HTTPException

from app.models.enums import LuggageSize, PaymentType, TripStatus
from app.models.location import Region
from app.models.trip import Trip
from app.schemas.trip import TripCreate
from app.services import trip_service

FARGONA, TOSHKENT, SAMARQAND = 901, 902, 903
TOMORROW = date.today() + timedelta(days=1)


async def _regions(db) -> None:
    db.add_all([
        Region(id=FARGONA, name_uz="Farg'ona viloyati", name_ru="Фергана", slug="f-sd", order=1),
        Region(id=TOSHKENT, name_uz="Toshkent shahri", name_ru="Ташкент", slug="t-sd", order=2),
        Region(id=SAMARQAND, name_uz="Samarqand viloyati", name_ru="Самарканд", slug="s-sd", order=3),
    ])
    await db.commit()


def _payload(hhmm: str, *, frm=FARGONA, to=TOSHKENT, confirm=False) -> TripCreate:
    return TripCreate(
        from_region_id=frm,
        to_region_id=to,
        departure_date=TOMORROW,
        departure_time=hhmm,
        total_seats=4,
        price_per_seat=150000,
        payment_type=PaymentType.cash,
        luggage_size=LuggageSize.medium,
        confirm_day_conflict=confirm,
    )


async def _existing(db, driver, hhmm: str, *, frm=FARGONA, to=TOSHKENT) -> Trip:
    trip = Trip(
        id=uuid.uuid4(), driver_id=driver.id,
        from_region_id=frm, to_region_id=to,
        departure_date=TOMORROW,
        departure_time=time(int(hhmm[:2]), int(hhmm[3:])),
        total_seats=4, available_seats=4, price_per_seat=130000,
        payment_type=PaymentType.cash, luggage_size=LuggageSize.medium,
        status=TripStatus.active,
    )
    db.add(trip)
    await db.commit()
    return trip


@pytest.mark.asyncio
async def test_ayni_yonalishda_ikkinchi_safar_ogohlantiradi(db, driver_user):
    driver, _dp = driver_user
    await _regions(db)
    await _existing(db, driver, "10:00")

    with pytest.raises(HTTPException) as err:
        await trip_service.create_trip(db, driver, _payload("11:00"))

    assert err.value.status_code == 409
    detail = str(err.value.detail)
    assert "10:00" in detail, "mavjud safar vaqti aytilsin"
    assert "shu yo'nalishda" in detail


@pytest.mark.asyncio
async def test_tasdiqlansa_otadi(db, driver_user):
    """Qisqa yo'lda ikki reys haqiqiy — to'sib qo'yilmaydi."""
    driver, _dp = driver_user
    await _regions(db)
    await _existing(db, driver, "10:00")

    trip = await trip_service.create_trip(db, driver, _payload("11:00", confirm=True))

    assert trip.departure_time == time(11, 0)


@pytest.mark.asyncio
async def test_qaytish_yonalishi_ogohlantirmaydi(db, driver_user):
    """B→A — odatdagi qaytish safari, bu normal."""
    driver, _dp = driver_user
    await _regions(db)
    await _existing(db, driver, "10:00")

    trip = await trip_service.create_trip(
        db, driver, _payload("18:00", frm=TOSHKENT, to=FARGONA))

    assert trip.from_region_id == TOSHKENT


@pytest.mark.asyncio
async def test_zanjir_yonalish_ogohlantirmaydi(db, driver_user):
    """A→B dan keyin B→C — haydovchi o'sha yerda, ulgurishi mumkin."""
    driver, _dp = driver_user
    await _regions(db)
    await _existing(db, driver, "10:00")            # Farg'ona → Toshkent

    trip = await trip_service.create_trip(
        db, driver, _payload("18:00", frm=TOSHKENT, to=SAMARQAND))

    assert trip.to_region_id == SAMARQAND


@pytest.mark.asyncio
async def test_bir_xil_vaqt_hamon_qattiq_tosiladi(db, driver_user):
    """Aynan dublikat — tasdiq bilan ham o'tmasin."""
    driver, _dp = driver_user
    await _regions(db)
    await _existing(db, driver, "10:00")

    with pytest.raises(HTTPException) as err:
        await trip_service.create_trip(db, driver, _payload("10:00", confirm=True))

    assert err.value.status_code == 400
    assert "allaqachon e'lon qilingan" in str(err.value.detail)


@pytest.mark.asyncio
async def test_boshqa_kunga_ogohlantirish_yoq(db, driver_user):
    driver, _dp = driver_user
    await _regions(db)
    await _existing(db, driver, "10:00")

    data = _payload("11:00")
    data.departure_date = TOMORROW + timedelta(days=1)

    trip = await trip_service.create_trip(db, driver, data)

    assert trip.departure_date == TOMORROW + timedelta(days=1)
