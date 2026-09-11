"""Qidiruvda tuman bo'yicha filtr.

Qoida: ikkala tomonda ham «tuman ko'rsatilmagan» = «barcha tumanlar».
  - so'rovda tuman yo'q  → viloyatdagi hamma safar chiqadi;
  - e'londa tuman yo'q   → haydovchi viloyat bo'ylab ishlaydi, ya'ni istalgan
    tuman so'roviga mos keladi.
Aniq tuman aniq tumanga qarshi qo'yilganda esa faqat tengi chiqadi.
"""
import uuid
from datetime import date, time, timedelta

import pytest
from sqlalchemy import select

from app.models.location import Region, District
from app.models.trip import Trip, TripWaypoint
from app.models.enums import TripStatus, PaymentType, LuggageSize
from app.schemas.trip import TripSearchParams
from app.services import trip_service

FARGONA, TOSHKENT = 101, 102
BUVAYDA, MARGILON = 1001, 1002
CHILONZOR, YUNUSOBOD = 1003, 1004
TOMORROW = date.today() + timedelta(days=1)


async def _locations(db):
    db.add_all([
        Region(id=FARGONA, name_uz="Farg'ona viloyati", name_ru="Фергана", slug="fargona", order=1),
        Region(id=TOSHKENT, name_uz="Toshkent shahri", name_ru="Ташкент", slug="toshkent", order=2),
    ])
    await db.flush()
    db.add_all([
        District(id=BUVAYDA, region_id=FARGONA, name_uz="Buvayda", name_ru="Бувайда", slug="buvayda"),
        District(id=MARGILON, region_id=FARGONA, name_uz="Marg'ilon", name_ru="Маргилан", slug="margilon"),
        District(id=CHILONZOR, region_id=TOSHKENT, name_uz="Chilonzor", name_ru="Чиланзар", slug="chilonzor"),
        District(id=YUNUSOBOD, region_id=TOSHKENT, name_uz="Yunusobod", name_ru="Юнусабад", slug="yunusobod"),
    ])
    await db.commit()


async def _trip(db, driver, *, from_district=None, to_district=None) -> Trip:
    t = Trip(
        id=uuid.uuid4(),
        driver_id=driver.id,
        from_region_id=FARGONA,
        from_district_id=from_district,
        to_region_id=TOSHKENT,
        to_district_id=to_district,
        departure_date=TOMORROW,
        departure_time=time(8, 0),
        total_seats=4,
        available_seats=4,
        price_per_seat=130_000,
        payment_type=PaymentType.cash,
        luggage_size=LuggageSize.medium,
        status=TripStatus.active,
        share_token=str(uuid.uuid4())[:8],
    )
    db.add(t)
    await db.commit()
    return t


def _params(from_district=None, to_district=None) -> TripSearchParams:
    return TripSearchParams(
        from_region_id=FARGONA,
        to_region_id=TOSHKENT,
        from_district_id=from_district,
        to_district_id=to_district,
        departure_date=TOMORROW,
        seats=1,
    )


# ─── Jo'nash tomoni ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_aniq_tuman_ozining_soroviga_chiqadi(db, driver_user):
    driver, _ = driver_user
    await _locations(db)
    await _trip(db, driver, from_district=BUVAYDA)

    found = await trip_service.search_trips(db, _params(from_district=BUVAYDA))
    assert len(found) == 1


@pytest.mark.asyncio
async def test_aniq_tuman_barcha_tumanlar_soroviga_ham_chiqadi(db, driver_user):
    driver, _ = driver_user
    await _locations(db)
    await _trip(db, driver, from_district=BUVAYDA)

    found = await trip_service.search_trips(db, _params())
    assert len(found) == 1


@pytest.mark.asyncio
async def test_elonda_tuman_yoq_bolsa_har_qanday_tumanga_chiqadi(db, driver_user):
    """Haydovchi «viloyat bo'ylab» degan — eski e'lonlar ham shu holatda."""
    driver, _ = driver_user
    await _locations(db)
    await _trip(db, driver, from_district=None)

    found = await trip_service.search_trips(db, _params(from_district=BUVAYDA))
    assert len(found) == 1


@pytest.mark.asyncio
async def test_boshqa_tuman_chiqmaydi(db, driver_user):
    driver, _ = driver_user
    await _locations(db)
    await _trip(db, driver, from_district=BUVAYDA)

    found = await trip_service.search_trips(db, _params(from_district=MARGILON))
    assert found == []


# ─── Borish tomoni ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_borish_tumani_ham_filtrlanadi(db, driver_user):
    driver, _ = driver_user
    await _locations(db)
    await _trip(db, driver, from_district=BUVAYDA, to_district=CHILONZOR)

    assert len(await trip_service.search_trips(db, _params(to_district=CHILONZOR))) == 1
    assert await trip_service.search_trips(db, _params(to_district=YUNUSOBOD)) == []
    # «Barcha tumanlar» — shahar bo'ylab qidiruv
    assert len(await trip_service.search_trips(db, _params())) == 1


@pytest.mark.asyncio
async def test_borishda_tuman_korsatilmagan_elon_har_qanday_tumanga_chiqadi(db, driver_user):
    """«Toshkent shahri — barcha tumanlar»: istalgan tumanga olib boradi."""
    driver, _ = driver_user
    await _locations(db)
    await _trip(db, driver, from_district=BUVAYDA, to_district=None)

    found = await trip_service.search_trips(db, _params(to_district=YUNUSOBOD))
    assert len(found) == 1


# ─── Oraliq to'xtash ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_toxtash_nuqtasi_tumani_solishtiriladi(db, driver_user):
    """Boshqa viloyatdan kelib, Farg'onaning bir tumanida to'xtaydigan safar."""
    driver, _ = driver_user
    await _locations(db)
    db.add(Region(id=103, name_uz="Andijon viloyati", name_ru="Андижан", slug="andijon", order=3))
    await db.flush()

    t = Trip(
        id=uuid.uuid4(),
        driver_id=driver.id,
        from_region_id=103,
        to_region_id=TOSHKENT,
        departure_date=TOMORROW,
        departure_time=time(7, 0),
        total_seats=4,
        available_seats=4,
        price_per_seat=150_000,
        payment_type=PaymentType.cash,
        luggage_size=LuggageSize.medium,
        status=TripStatus.active,
        has_waypoints=True,
        share_token=str(uuid.uuid4())[:8],
    )
    db.add(t)
    await db.flush()
    db.add_all([
        TripWaypoint(id=uuid.uuid4(), trip_id=t.id, region_id=FARGONA,
                     district_id=MARGILON, order_index=1, price_from_start=120_000),
        TripWaypoint(id=uuid.uuid4(), trip_id=t.id, region_id=TOSHKENT,
                     district_id=None, order_index=2, price_from_start=150_000),
    ])
    await db.commit()

    # To'xtash nuqtasi Marg'ilonda — Buvayda so'roviga chiqmaydi
    assert await trip_service.search_trips(db, _params(from_district=BUVAYDA)) == []
    # O'z tumani bo'yicha chiqadi
    assert len(await trip_service.search_trips(db, _params(from_district=MARGILON))) == 1


# ─── Yaqin sanalar ham shu filtrga bo'ysunadi ────────────────────────────────

@pytest.mark.asyncio
async def test_yaqin_sanalar_tumanga_bogliq(db, driver_user):
    """Aks holda bo'sh natijada mos kelmaydigan sana taklif qilinardi."""
    driver, _ = driver_user
    await _locations(db)
    await _trip(db, driver, from_district=MARGILON)

    dates_all = await trip_service.nearest_dates(
        db, FARGONA, TOSHKENT, date.today(), 1
    )
    assert len(dates_all) == 1

    dates_buvayda = await trip_service.nearest_dates(
        db, FARGONA, TOSHKENT, date.today(), 1, from_district_id=BUVAYDA
    )
    assert dates_buvayda == []


# ─── Tasdiq belgisi ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_belgi_faqat_admin_tekshirganda(db, driver_user, admin_user):
    """«Tasdiqlangan» va «hujjati tekshirilgan» — ikki xil narsa.

    Hisob avtomatik ochilishi mumkin (pilot davri), belgi esa faqat admin
    guvohnomani ko'rgandan keyin beriladi.
    """
    driver, dp = driver_user
    await _locations(db)
    await _trip(db, driver, from_district=BUVAYDA)

    def _flag():
        return trip_service.serialize_trip(found[0]).driver.documents_verified

    # 1. Guvohnoma bor, lekin hech kim ko'rmagan → belgi yo'q
    found = await trip_service.search_trips(db, _params())
    assert _flag() is False

    # 2. Admin tekshirdi → belgi bor
    dp.verified_by = admin_user.id
    await db.commit()
    found = await trip_service.search_trips(db, _params())
    assert _flag() is True

    # 3. Guvohnoma yo'q, lekin tasdiqlangan → belgi baribir yo'q
    dp.license_image = None
    await db.commit()
    found = await trip_service.search_trips(db, _params())
    assert _flag() is False
