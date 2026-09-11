"""Avtomatik tasdiqlash (pilot davri).

Haydovchi va yo'lovchi kam bo'lgan bosqichda ariza darrov ochiladi — haydovchi
admin tugmasini kutib o'tirmaydi. Lekin bu «tekshirildi» degani emas:
`status=approved` → safar e'lon qila oladi, `verified_by` → admin hujjatni
ko'zi bilan ko'rgan. Belgi faqat ikkinchisida beriladi.
"""
import io
from datetime import date, timedelta

import pytest
from PIL import Image
from sqlalchemy import select

from app.core.config import settings
from app.models.admin import AdminAction
from app.models.driver import DriverProfile
from app.models.enums import DriverStatus
from app.models.location import Region
from app.models.notification import Notification
from app.models.wallet import DriverWallet
from app.services.storage_service import storage_service
from tests.conftest import auth_headers

API = "/api/v1"

CAR = {
    "vehicle_make": "Chevrolet",
    "vehicle_model": "Cobalt",
    "vehicle_color": "Oq",
    "vehicle_plate": "40A777BB",
    "vehicle_seats": "4",
}


def _jpeg() -> bytes:
    img = Image.new("RGB", (800, 500))
    px = img.load()
    for x in range(800):
        for y in range(500):
            px[x, y] = ((x * 7) % 256, (y * 5) % 256, (x + y) % 256)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _no_minio(monkeypatch):
    async def _fake_upload(file, bucket, folder=""):
        await file.read()
        await file.seek(0)
        return f"{folder}/test.jpg"
    monkeypatch.setattr(storage_service, "upload", _fake_upload)


@pytest.fixture
def auto_on(monkeypatch):
    monkeypatch.setattr(settings, "AUTO_APPROVE_DRIVERS", True)


async def _profile(db, user) -> DriverProfile:
    return (await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == user.id)
    )).scalar_one()


# ─── Bayroq ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bayroq_ochiq_bolsa_pending_qoladi(client, db, user):
    """Sukut holat buzilmasin — bayroqsiz hammasi avvalgidek."""
    r = await client.post(f"{API}/drivers/apply", data=CAR, headers=auth_headers(user))
    assert r.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_avtomatik_ochiladi_lekin_tekshirilmagan(client, db, user, auto_on):
    r = await client.post(f"{API}/drivers/apply", data=CAR, headers=auth_headers(user))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"

    dp = await _profile(db, user)
    assert dp.verified_by is None
    assert dp.verified_at is None
    assert dp.documents_verified is False


@pytest.mark.asyncio
async def test_hamyon_yaratiladi(client, db, user, auto_on):
    await client.post(f"{API}/drivers/apply", data=CAR, headers=auth_headers(user))
    wallet = (await db.execute(
        select(DriverWallet).where(DriverWallet.driver_id == user.id)
    )).scalar_one_or_none()
    assert wallet is not None


@pytest.mark.asyncio
async def test_admin_jurnali_bosh_va_xabar_tekshiruv_demaydi(client, db, user, auto_on):
    """Hech qanday admin harakat qilmadi — jurnal yolg'on gapirmasin."""
    await client.post(f"{API}/drivers/apply", data=CAR, headers=auth_headers(user))

    actions = (await db.execute(select(AdminAction))).scalars().all()
    assert actions == []

    notif = (await db.execute(
        select(Notification).where(Notification.user_id == user.id)
    )).scalars().first()
    assert notif is not None
    assert "tekshiril" not in (notif.title + notif.body).lower()


@pytest.mark.asyncio
async def test_hujjat_yuklansa_ham_belgi_yoq(client, db, user, auto_on):
    """Yuklangan hujjatni hali hech kim ko'rmagan."""
    await client.post(
        f"{API}/drivers/apply",
        data=CAR,
        files={"license_image": ("l.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    dp = await _profile(db, user)
    assert dp.license_image is not None
    assert dp.documents_verified is False


@pytest.mark.asyncio
async def test_admin_tekshirgach_belgi_paydo_boladi(client, db, user, admin_user, auto_on):
    r = await client.post(
        f"{API}/drivers/apply",
        data=CAR,
        files={"license_image": ("l.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    profile_id = r.json()["id"]

    ok = await client.post(
        f"{API}/admin/drivers/{profile_id}/approve", headers=auth_headers(admin_user)
    )
    assert ok.status_code == 200, ok.text

    dp = await _profile(db, user)
    await db.refresh(dp)
    assert dp.verified_by == admin_user.id
    assert dp.documents_verified is True


@pytest.mark.asyncio
async def test_ikki_marta_tekshirib_bolmaydi(client, db, user, admin_user, auto_on):
    r = await client.post(
        f"{API}/drivers/apply",
        data=CAR,
        files={"license_image": ("l.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    pid = r.json()["id"]
    await client.post(f"{API}/admin/drivers/{pid}/approve", headers=auth_headers(admin_user))
    again = await client.post(
        f"{API}/admin/drivers/{pid}/approve", headers=auth_headers(admin_user)
    )
    assert again.status_code == 400


@pytest.mark.asyncio
async def test_hujjatsizni_tasdiqlasa_ham_belgi_yoq(client, db, user, admin_user, auto_on):
    r = await client.post(f"{API}/drivers/apply", data=CAR, headers=auth_headers(user))
    pid = r.json()["id"]
    await client.post(f"{API}/admin/drivers/{pid}/approve", headers=auth_headers(admin_user))

    dp = await _profile(db, user)
    await db.refresh(dp)
    assert dp.verified_by == admin_user.id      # admin ko'rdi
    assert dp.documents_verified is False       # lekin ko'radigan hujjat yo'q edi


@pytest.mark.asyncio
async def test_rad_etilgan_qayta_arizada_avtomatika_ishlamaydi(client, db, user, auto_on):
    """Adminning "yo'q" qarori o'z-o'zidan bekor bo'lib qolmasin."""
    await client.post(f"{API}/drivers/apply", data=CAR, headers=auth_headers(user))
    dp = await _profile(db, user)
    dp.status = DriverStatus.rejected
    dp.rejection_reason = "Hujjat kerak"
    await db.commit()

    r = await client.post(f"{API}/drivers/apply", data=CAR, headers=auth_headers(user))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_tekshirilmagan_haydovchini_rad_etish_mumkin(client, db, user, admin_user, auto_on):
    """Avtomatik ochilganini rad etish — adminning yagona "yo'q" tugmasi."""
    r = await client.post(f"{API}/drivers/apply", data=CAR, headers=auth_headers(user))
    pid = r.json()["id"]

    out = await client.post(
        f"{API}/admin/drivers/{pid}/reject",
        json={"reason": "Telefonga javob bermadi"},
        headers=auth_headers(admin_user),
    )
    assert out.status_code == 200, out.text
    assert out.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_avtomatik_ochilgan_darrov_safar_elon_qiladi(client, db, user, auto_on):
    """Butun ishning maqsadi shu — kutish yo'q."""
    db.add_all([
        Region(id=201, name_uz="Farg'ona", name_ru="Фергана", slug="f", order=1),
        Region(id=202, name_uz="Toshkent", name_ru="Ташкент", slug="t", order=2),
    ])
    await db.commit()

    await client.post(f"{API}/drivers/apply", data=CAR, headers=auth_headers(user))

    trip = await client.post(
        f"{API}/trips",
        json={
            "from_region_id": 201,
            "to_region_id": 202,
            "departure_date": str(date.today() + timedelta(days=1)),
            "departure_time": "08:00",
            "total_seats": 4,
            "price_per_seat": 130_000,
        },
        headers=auth_headers(user),
    )
    assert trip.status_code == 201, trip.text
