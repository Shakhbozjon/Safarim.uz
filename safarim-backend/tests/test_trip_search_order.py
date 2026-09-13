"""Qidiruv natijalarining tartibi.

Asosiy mezon — jo'nash vaqti (yoki narx). TENG bo'lganda:
  1) hujjat darajasi: tekshirilgan → yuklagan → yuklamagan
  2) qaysi safar avval e'lon qilingan

Hujjat darajasi ataylab ikkinchi o'rinda: u vaqtdan ustun bo'lsa, yo'lovchi
ertalabki safarni qidirib kechqurungisini tepada ko'rardi.
"""
import uuid
from datetime import date, datetime, time, timedelta

import pytest

from app.models.driver import DriverProfile
from app.models.enums import DriverStatus, LuggageSize, PaymentType, TripStatus
from app.models.location import Region
from app.models.trip import Trip
from app.models.user import User
from app.schemas.trip import TripSearchParams
from app.services import trip_service
from tests.conftest import _TEST_PASSWORD_HASH

FARGONA, TOSHKENT = 201, 202
TOMORROW = date.today() + timedelta(days=1)


async def _locations(db):
    db.add_all([
        Region(id=FARGONA, name_uz="Farg'ona viloyati", name_ru="Фергана", slug="fargona-o", order=1),
        Region(id=TOSHKENT, name_uz="Toshkent shahri", name_ru="Ташкент", slug="toshkent-o", order=2),
    ])
    await db.commit()


async def _driver(db, suffix: str, *, license_img=None, verified=False) -> User:
    """Berilgan hujjat holatidagi haydovchi."""
    u = User(
        id=uuid.uuid4(),
        phone=f"+99890555{suffix}",
        full_name=f"Haydovchi {suffix}",
        password_hash=_TEST_PASSWORD_HASH,
        is_phone_verified=True,
        is_driver=True,
    )
    db.add(u)
    await db.flush()
    db.add(DriverProfile(
        user_id=u.id,
        license_image=license_img,
        vehicle_make="Chevrolet",
        vehicle_model="Cobalt",
        vehicle_color="Oq",
        vehicle_plate=f"01A{suffix}BC",
        vehicle_seats=4,
        status=DriverStatus.approved,
        verified_by=u.id if verified else None,
        verified_at=datetime.utcnow() if verified else None,
    ))
    await db.commit()
    return u


async def _trip(db, driver, *, created_at=None, price=130_000, at=time(8, 0)) -> Trip:
    t = Trip(
        id=uuid.uuid4(),
        driver_id=driver.id,
        from_region_id=FARGONA,
        to_region_id=TOSHKENT,
        departure_date=TOMORROW,
        departure_time=at,
        total_seats=4,
        available_seats=4,
        price_per_seat=price,
        payment_type=PaymentType.cash,
        luggage_size=LuggageSize.medium,
        status=TripStatus.active,
        share_token=str(uuid.uuid4())[:8],
    )
    if created_at is not None:
        t.created_at = created_at
    db.add(t)
    await db.commit()
    return t


def _params(sort="time_asc") -> TripSearchParams:
    return TripSearchParams(
        from_region_id=FARGONA,
        to_region_id=TOSHKENT,
        departure_date=TOMORROW,
        seats=1,
        sort=sort,
    )


@pytest.mark.asyncio
async def test_hujjat_yuklagan_yuklamaganidan_yuqorida(db):
    """Asosiy qoida: hujjat yuklash ko'rinadigan foyda bersin."""
    await _locations(db)
    base = datetime(2026, 1, 1, 10, 0)

    # Hujjatsiz haydovchi AVVAL e'lon qildi — baribir pastda qolishi kerak
    yoq = await _driver(db, "01")
    await _trip(db, yoq, created_at=base)

    yuklagan = await _driver(db, "02", license_img="licenses/a.jpg")
    await _trip(db, yuklagan, created_at=base + timedelta(hours=1))

    tekshirilgan = await _driver(db, "03", license_img="licenses/b.jpg", verified=True)
    await _trip(db, tekshirilgan, created_at=base + timedelta(hours=2))

    found = await trip_service.search_trips(db, _params())
    assert [t.driver_id for t in found] == [
        tekshirilgan.id, yuklagan.id, yoq.id
    ]


@pytest.mark.asyncio
async def test_teng_hujjatda_avval_elon_qilgan_yuqorida(db):
    """Hujjat darajasi teng bo'lsa — navbat: kim erta e'lon qilgan bo'lsa."""
    await _locations(db)
    base = datetime(2026, 1, 1, 10, 0)

    birinchi = await _driver(db, "04", license_img="licenses/c.jpg")
    await _trip(db, birinchi, created_at=base)

    ikkinchi = await _driver(db, "05", license_img="licenses/d.jpg")
    await _trip(db, ikkinchi, created_at=base + timedelta(hours=3))

    found = await trip_service.search_trips(db, _params())
    assert [t.driver_id for t in found] == [birinchi.id, ikkinchi.id]


@pytest.mark.asyncio
async def test_vaqt_hujjatdan_ustun(db):
    """⚠️ Hujjat darajasi jo'nash vaqtini BOSIB O'TMAYDI.

    Aks holda yo'lovchi ertalabki safar qidirib, kechqurungisini tepada
    ko'rardi — bu qidiruvni buzadi.
    """
    await _locations(db)

    kech_tekshirilgan = await _driver(db, "06", license_img="licenses/e.jpg", verified=True)
    await _trip(db, kech_tekshirilgan, at=time(20, 0))

    erta_hujjatsiz = await _driver(db, "07")
    await _trip(db, erta_hujjatsiz, at=time(7, 0))

    found = await trip_service.search_trips(db, _params())
    assert [t.driver_id for t in found] == [erta_hujjatsiz.id, kech_tekshirilgan.id]


@pytest.mark.asyncio
async def test_narx_boyicha_saralashda_ham_ishlaydi(db):
    """Narx bo'yicha saralashda ham teng narxlar shu tartibda ajratiladi."""
    await _locations(db)
    base = datetime(2026, 1, 1, 10, 0)

    yoq = await _driver(db, "08")
    await _trip(db, yoq, price=100_000, created_at=base)

    tekshirilgan = await _driver(db, "09", license_img="licenses/f.jpg", verified=True)
    await _trip(db, tekshirilgan, price=100_000, created_at=base + timedelta(hours=1))

    found = await trip_service.search_trips(db, _params(sort="price_asc"))
    assert [t.driver_id for t in found] == [tekshirilgan.id, yoq.id]


@pytest.mark.asyncio
async def test_tartib_bir_xil_qaytadi(db):
    """Ilgari teng vaqtli safarlar tartibi so'rovdan so'rovga o'zgarardi."""
    await _locations(db)
    base = datetime(2026, 1, 1, 10, 0)
    for i in range(5):
        d = await _driver(db, f"1{i}", license_img="licenses/g.jpg" if i % 2 else None)
        await _trip(db, d, created_at=base + timedelta(minutes=i))

    birinchi = [t.id for t in await trip_service.search_trips(db, _params())]
    for _ in range(3):
        assert [t.id for t in await trip_service.search_trips(db, _params())] == birinchi
