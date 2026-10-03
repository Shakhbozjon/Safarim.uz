"""Qidiruv natijasi sahifalab beriladi, filtrlar serverda qo'llanadi.

Ilgari `/trips/search` shu sana va yo'nalishdagi HAMMA safarni qaytarardi.
Vaqt, reyting va yuk filtrlari esa brauzerda, kelgan ro'yxat ustida
qo'llanardi — sahifalashdan keyin ular faqat birinchi sahifani ko'rgan
bo'lardi. Endi uchalasi ham serverda, umumiy son `X-Total-Count` da.
"""
import uuid
from datetime import time, timedelta

from app.core.timeutils import now_tashkent_naive
from app.models.enums import LuggageSize, PaymentType, TripStatus
from app.models.location import Region
from app.models.trip import Trip

FARGONA, TOSHKENT = 801, 802
TOMORROW = (now_tashkent_naive() + timedelta(days=1)).date()


async def _regions(db):
    db.add_all([
        Region(id=FARGONA, name_uz="Farg'ona viloyati", name_ru="Фергана", slug="fargona-s", order=1),
        Region(id=TOSHKENT, name_uz="Toshkent shahri", name_ru="Ташкент", slug="toshkent-s", order=2),
    ])
    await db.commit()


def _trip(driver, at: time, luggage=LuggageSize.medium) -> Trip:
    return Trip(
        id=uuid.uuid4(),
        driver_id=driver.id,
        from_region_id=FARGONA,
        to_region_id=TOSHKENT,
        departure_date=TOMORROW,
        departure_time=at,
        total_seats=4,
        available_seats=4,
        price_per_seat=120_000,
        payment_type=PaymentType.cash,
        luggage_size=luggage,
        status=TripStatus.active,
    )


def _url(**extra) -> str:
    q = f"from_region_id={FARGONA}&to_region_id={TOSHKENT}&departure_date={TOMORROW}"
    return "/api/v1/trips/search?" + "&".join([q] + [f"{k}={v}" for k, v in extra.items()])


async def _many(db, driver, n: int) -> list[Trip]:
    trips = [_trip(driver, time(5 + i // 4, (i % 4) * 15)) for i in range(n)]
    db.add_all(trips)
    await db.commit()
    return trips


async def test_sahifalar_takrorlanmaydi_va_hammasi_chiqadi(client, db, driver_user):
    driver, _ = driver_user
    await _regions(db)
    trips = await _many(db, driver, 25)

    p1 = await client.get(_url(limit=10, offset=0))
    p2 = await client.get(_url(limit=10, offset=10))
    p3 = await client.get(_url(limit=10, offset=20))
    assert p1.headers["X-Total-Count"] == "25"
    assert p3.headers["X-Total-Count"] == "25"
    ids = [t["id"] for p in (p1, p2, p3) for t in p.json()]
    assert len(ids) == 25
    assert set(ids) == {str(t.id) for t in trips}
    # Tartib sahifalar bo'ylab ham saqlanadi — jo'nash vaqti bo'yicha
    times = [t["departure_time"] for p in (p1, p2, p3) for t in p.json()]
    assert times == sorted(times)


async def test_sukut_boyicha_20_ta(client, db, driver_user):
    driver, _ = driver_user
    await _regions(db)
    await _many(db, driver, 23)

    r = await client.get(_url())
    assert len(r.json()) == 20
    assert r.headers["X-Total-Count"] == "23"


async def test_kichik_natijada_son_togri(client, db, driver_user):
    driver, _ = driver_user
    await _regions(db)
    await _many(db, driver, 3)
    r = await client.get(_url())
    assert len(r.json()) == 3
    assert r.headers["X-Total-Count"] == "3"


async def test_limit_chegarasi(client, db):
    r = await client.get(_url(limit=500))
    assert r.status_code == 422


async def test_vaqt_filtri_serverda(client, db, driver_user):
    driver, _ = driver_user
    await _regions(db)
    db.add_all([
        _trip(driver, time(6, 0)),
        _trip(driver, time(11, 59, 30)),   # «12:00 gacha» ichida
        _trip(driver, time(12, 0)),        # chegara — kiradi
        _trip(driver, time(12, 1)),
        _trip(driver, time(18, 0)),
    ])
    await db.commit()

    r = await client.get(_url(departure_from="06:00", departure_to="12:00"))
    assert [t["departure_time"][:5] for t in r.json()] == ["06:00", "11:59", "12:00"]
    assert r.headers["X-Total-Count"] == "3"


async def test_reyting_filtri_serverda(client, db, driver_user):
    driver, dp = driver_user
    await _regions(db)
    db.add(_trip(driver, time(9, 0)))
    await db.commit()

    # Baholanmagan haydovchi «4+» filtriga tushmaydi
    assert (await client.get(_url(min_rating=4))).json() == []
    dp.rating_avg = 4.6
    dp.rating_count = 5
    await db.commit()
    assert len((await client.get(_url(min_rating=4))).json()) == 1


async def test_katta_yuk_filtri_serverda(client, db, driver_user):
    driver, _ = driver_user
    await _regions(db)
    db.add_all([_trip(driver, time(8, 0)), _trip(driver, time(9, 0), LuggageSize.large)])
    await db.commit()

    r = await client.get(_url(large_luggage="true"))
    assert [t["luggage_size"] for t in r.json()] == ["large"]
    assert r.headers["X-Total-Count"] == "1"
