"""Hujjat yuklash ixtiyoriy (ishga tushirish davri).

Dala ma'lumoti: birinchi haydovchi guvohnoma va texpasportini yangi saytga
yuklashga ishonmadi. Tekshiruv olib tashlangani yo'q — admin haydovchini
yuzma-yuz ko'rib tasdiqlaydi, surat esa majburiy emas.
"""
import io

import pytest
from PIL import Image
from sqlalchemy import select

from app.models.driver import DriverProfile
from app.models.enums import DriverStatus
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
    """Tekshiruvdan o'tadigan rasm: yetarli o'lcham va rang tarqalishi."""
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


@pytest.mark.asyncio
async def test_hujjatsiz_ariza_qabul_qilinadi(client, db, user):
    r = await client.post(f"{API}/drivers/apply", data=CAR, headers=auth_headers(user))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending"

    dp = (await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == user.id)
    )).scalar_one()
    assert dp.license_image is None
    assert dp.tech_passport_image is None


@pytest.mark.asyncio
async def test_faqat_guvohnoma_bilan_ham_boladi(client, db, user):
    r = await client.post(
        f"{API}/drivers/apply",
        data=CAR,
        files={"license_image": ("l.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    assert r.status_code == 200, r.text

    dp = (await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == user.id)
    )).scalar_one()
    assert dp.license_image is not None
    assert dp.tech_passport_image is None


@pytest.mark.asyncio
async def test_yuklangan_rasm_hamon_tekshiriladi(client, user):
    """Ixtiyoriy degani "har qanday fayl" degani emas."""
    r = await client.post(
        f"{API}/drivers/apply",
        data=CAR,
        files={"license_image": ("l.jpg", b"bu rasm emas", "image/jpeg")},
        headers=auth_headers(user),
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_hujjatsiz_haydovchini_admin_tasdiqlay_oladi(client, db, user, admin_user):
    """Yuzma-yuz ko'rgan admin uchun yo'l ochiq bo'lishi kerak."""
    r = await client.post(f"{API}/drivers/apply", data=CAR, headers=auth_headers(user))
    profile_id = r.json()["id"]

    docs = await client.get(
        f"{API}/admin/drivers/{profile_id}/documents", headers=auth_headers(admin_user)
    )
    assert docs.status_code == 200
    assert docs.json()["license_url"] is None
    assert docs.json()["vehicle"]["plate"] == "40A777BB"

    ok = await client.post(
        f"{API}/admin/drivers/{profile_id}/approve", headers=auth_headers(admin_user)
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == DriverStatus.approved.value


@pytest.mark.asyncio
async def test_qayta_arizada_eski_surat_yoqolmaydi(client, db, user):
    """Guvohnoma bilan topshirib, keyin hujjatsiz qayta topshirsa —
    avval yuklangan surat o'chib ketmasligi kerak."""
    await client.post(
        f"{API}/drivers/apply",
        data=CAR,
        files={"license_image": ("l.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    dp = (await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == user.id)
    )).scalar_one()
    dp.status = DriverStatus.rejected          # rad etilgan ariza qayta topshiriladi
    await db.commit()

    r = await client.post(f"{API}/drivers/apply", data=CAR, headers=auth_headers(user))
    assert r.status_code == 200, r.text

    await db.refresh(dp)
    assert dp.license_image is not None
