"""Admin paneldagi ro'yxatlar: qidiruv va filtrlar.

Qidiruv BAZADA bajarilishi kerak. Ilgari foydalanuvchilar sahifasida u
frontendda edi va faqat ochilgan 20 qatorni filtrlardi — 5-sahifadagi odamni
topib bo'lmasdi. Haydovchilar sahifasida esa faqat "kutayotgan" ro'yxat bor
edi, tasdiqlangan haydovchi umuman ko'rinmasdi.
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.driver import DriverProfile
from app.models.enums import DriverStatus
from app.models.user import User

from tests.conftest import auth_headers

API = "/api/v1/admin"


async def _user(db: AsyncSession, name: str, phone: str, **kw) -> User:
    u = User(
        id=uuid.uuid4(), phone=phone, full_name=name,
        password_hash="x", is_phone_verified=True, **kw,
    )
    db.add(u)
    await db.commit()
    return u


async def _driver(db: AsyncSession, user: User, plate: str, status: DriverStatus) -> DriverProfile:
    dp = DriverProfile(
        id=uuid.uuid4(), user_id=user.id, license_image="documents/x.jpg",
        vehicle_make="Chevrolet", vehicle_model="Cobalt", vehicle_year=2020,
        vehicle_color="Oq", vehicle_plate=plate, vehicle_seats=4, status=status,
    )
    user.is_driver = True
    db.add(dp)
    await db.commit()
    return dp


# ─── Foydalanuvchilar ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_search_finds_beyond_first_page(client: AsyncClient, db, admin_user: User):
    """Qidiruv butun bazani ko'radi, faqat birinchi sahifani emas."""
    for i in range(25):
        await _user(db, f"Oddiy Foydalanuvchi {i}", f"+99893100{i:04d}")
    await _user(db, "Zafar Izlanuvchi", "+998905550001")

    r = await client.get(f"{API}/users", params={"q": "izlanuvchi"}, headers=auth_headers(admin_user))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["users"][0]["full_name"] == "Zafar Izlanuvchi"


@pytest.mark.asyncio
async def test_user_search_is_case_insensitive_and_matches_phone(client: AsyncClient, db, admin_user: User):
    await _user(db, "Kamola Ergashev", "+998911234567")

    by_name = await client.get(f"{API}/users", params={"q": "KAMOLA"}, headers=auth_headers(admin_user))
    assert by_name.json()["total"] == 1

    by_phone = await client.get(f"{API}/users", params={"q": "9112345"}, headers=auth_headers(admin_user))
    assert by_phone.json()["total"] == 1


@pytest.mark.asyncio
async def test_user_filters(client: AsyncClient, db, admin_user: User, driver_user):
    driver, _ = driver_user
    await _user(db, "Bloklangan Odam", "+998907770001", is_blocked=True)

    drivers = await client.get(f"{API}/users", params={"role": "driver"}, headers=auth_headers(admin_user))
    assert drivers.json()["total"] == 1
    assert drivers.json()["users"][0]["id"] == str(driver.id)

    blocked = await client.get(f"{API}/users", params={"status": "blocked"}, headers=auth_headers(admin_user))
    assert blocked.json()["total"] == 1
    assert blocked.json()["users"][0]["full_name"] == "Bloklangan Odam"

    admins = await client.get(f"{API}/users", params={"role": "admin"}, headers=auth_headers(admin_user))
    assert admins.json()["total"] == 1


# ─── Haydovchilar ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_driver_list_by_status(client: AsyncClient, db, admin_user: User):
    a = await _user(db, "Tasdiqlangan Haydovchi", "+998901000001")
    b = await _user(db, "Kutayotgan Haydovchi", "+998901000002")
    await _driver(db, a, "01A111BC", DriverStatus.approved)
    await _driver(db, b, "01A222BC", DriverStatus.pending)

    approved = await client.get(f"{API}/drivers", params={"status": "approved"}, headers=auth_headers(admin_user))
    assert [d["vehicle_plate"] for d in approved.json()] == ["01A111BC"]

    pending = await client.get(f"{API}/drivers", params={"status": "pending"}, headers=auth_headers(admin_user))
    assert [d["vehicle_plate"] for d in pending.json()] == ["01A222BC"]

    all_ = await client.get(f"{API}/drivers", params={"status": "all"}, headers=auth_headers(admin_user))
    assert len(all_.json()) == 2


@pytest.mark.asyncio
async def test_driver_list_search_and_phone_field(client: AsyncClient, db, admin_user: User):
    u = await _user(db, "Sardor Yo'ldoshev", "+998935554433")
    await _driver(db, u, "30BB777AA", DriverStatus.approved)

    by_plate = await client.get(f"{API}/drivers", params={"status": "all", "q": "30bb"}, headers=auth_headers(admin_user))
    assert len(by_plate.json()) == 1

    by_name = await client.get(f"{API}/drivers", params={"status": "all", "q": "sardor"}, headers=auth_headers(admin_user))
    row = by_name.json()[0]
    # Admin haydovchiga qo'ng'iroq qila olishi uchun telefon javobda bo'lishi shart
    assert row["user"]["phone"] == "+998935554433"


@pytest.mark.asyncio
async def test_driver_list_requires_admin(client: AsyncClient, user: User):
    r = await client.get(f"{API}/drivers", params={"status": "all"}, headers=auth_headers(user))
    assert r.status_code == 403


# ─── Tekshiruv navbati ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hujjat_tekshirilmaganlar_navbati(client: AsyncClient, db, admin_user: User):
    """Avtomatik tasdiqlashda "kutayotganlar" bo'shab qoladi — adminning
    haqiqiy navbati "hujjat yuklagan, hali ko'rilmagan" ro'yxati."""
    u1 = await _user(db, "Navbatdagi Haydovchi", "+998905550101")
    await _driver(db, u1, "01A111AA", DriverStatus.approved)          # hujjatli, tekshirilmagan

    u2 = await _user(db, "Tekshirilgan Haydovchi", "+998905550102")
    dp2 = await _driver(db, u2, "01A222AA", DriverStatus.approved)
    dp2.verified_by = admin_user.id                                   # admin ko'rgan
    await db.commit()

    u3 = await _user(db, "Hujjatsiz Haydovchi", "+998905550103")
    dp3 = await _driver(db, u3, "01A333AA", DriverStatus.approved)
    dp3.license_image = None                                          # ko'radigan hujjat yo'q
    await db.commit()

    u4 = await _user(db, "Rad Etilgan Haydovchi", "+998905550104")
    await _driver(db, u4, "01A444AA", DriverStatus.rejected)          # navbatga tushmasin

    r = await client.get(
        f"{API}/drivers",
        params={"status": "all", "needs_review": "true"},
        headers=auth_headers(admin_user),
    )
    assert r.status_code == 200, r.text
    plates = [d["vehicle_plate"] for d in r.json()]
    assert plates == ["01A111AA"]


@pytest.mark.asyncio
async def test_bitta_haydovchini_ochish(client: AsyncClient, db, admin_user: User):
    """Sahifa ilgari haydovchini faqat "kutayotganlar" ro'yxatidan qidirardi."""
    u = await _user(db, "Tasdiqlangan Haydovchi", "+998905550105")
    dp = await _driver(db, u, "01A555AA", DriverStatus.approved)

    r = await client.get(f"{API}/drivers/{dp.id}", headers=auth_headers(admin_user))
    assert r.status_code == 200, r.text
    assert r.json()["vehicle_plate"] == "01A555AA"
    assert r.json()["documents_verified"] is False

    assert (await client.get(
        f"{API}/drivers/{uuid.uuid4()}", headers=auth_headers(admin_user)
    )).status_code == 404
    # Buzuq id 500 emas, 404 berishi kerak
    assert (await client.get(
        f"{API}/drivers/bu-uuid-emas", headers=auth_headers(admin_user)
    )).status_code == 404
