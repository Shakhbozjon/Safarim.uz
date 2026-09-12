"""Hujjatni ARIZADAN KEYIN yuklash.

«Hozircha o'tkazib yuborish»ni bosgan haydovchining tasdiq belgisiga
boradigan yagona yo'li shu endpoint. Asosiy shart: hujjat yuklash uning
ish holatiga (`approved`) tegmasligi kerak.
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
    uploaded: list[str] = []
    deleted: list[str] = []

    async def _fake_upload(file, bucket, folder=""):
        await file.read()
        await file.seek(0)
        key = f"{folder}/{len(uploaded)}.jpg"
        uploaded.append(key)
        return key

    def _fake_delete(key, bucket):
        deleted.append(key)
        return True

    monkeypatch.setattr(storage_service, "upload", _fake_upload)
    monkeypatch.setattr(storage_service, "delete_file", _fake_delete)
    return deleted


async def _apply_without_documents(client, user):
    r = await client.post(f"{API}/drivers/apply", data=CAR, headers=auth_headers(user))
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.asyncio
async def test_keyin_yuklagan_haydovchining_holati_ozgarmaydi(client, db, user):
    """Eng muhim shart: `approved` haydovchi hujjat yuklagani uchun
    `pending` ga tushib, safar e'lon qila olmay qolmasligi kerak."""
    await _apply_without_documents(client, user)

    dp = (await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == user.id)
    )).scalar_one()
    dp.status = DriverStatus.approved          # avtomatik ochilgan haydovchi
    await db.commit()

    r = await client.post(
        f"{API}/drivers/me/documents",
        files={"license_image": ("l.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == DriverStatus.approved.value
    assert r.json()["has_license"] is True
    # Hujjat yuklandi, lekin hech kim ko'rmadi — belgi hali yo'q
    assert r.json()["documents_verified"] is False

    await db.refresh(dp)
    assert dp.license_image is not None
    assert dp.verified_by is None


@pytest.mark.asyncio
async def test_keyin_yuklangan_hujjat_admin_navbatiga_tushadi(
    client, db, user, admin_user
):
    """Yuklash o'z-o'zidan `needs_review` ro'yxatiga qo'shilishi kerak —
    aks holda hujjat yuklanadi-yu, admin uni hech qachon ko'rmaydi."""
    profile = await _apply_without_documents(client, user)

    empty = await client.get(
        f"{API}/admin/drivers?status=all&needs_review=true", headers=auth_headers(admin_user)
    )
    assert empty.status_code == 200, empty.text
    assert all(d["id"] != profile["id"] for d in empty.json())

    await client.post(
        f"{API}/drivers/me/documents",
        files={"license_image": ("l.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )

    queue = await client.get(
        f"{API}/admin/drivers?status=all&needs_review=true", headers=auth_headers(admin_user)
    )
    assert any(d["id"] == profile["id"] for d in queue.json())


@pytest.mark.asyncio
async def test_tekshirilgan_hujjatni_ozgartirib_bolmaydi(client, db, user, admin_user):
    """Admin ko'rgan suratni keyin boshqasiga almashtirish yo'li yopiq."""
    profile = await _apply_without_documents(client, user)
    await client.post(
        f"{API}/drivers/me/documents",
        files={"license_image": ("l.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    ok = await client.post(
        f"{API}/admin/drivers/{profile['id']}/approve", headers=auth_headers(admin_user)
    )
    assert ok.status_code == 200, ok.text

    r = await client.post(
        f"{API}/drivers/me/documents",
        files={"license_image": ("l2.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    assert r.status_code == 400
    assert "tekshirilgan" in r.json()["detail"]


@pytest.mark.asyncio
async def test_faqat_texpasport_qabul_qilinadi_lekin_belgi_bermaydi(client, db, user):
    """Texpasport mashina raqamini tekshirishga foydali, lekin tasdiq
    belgisi guvohnomaga bog'liq."""
    await _apply_without_documents(client, user)

    r = await client.post(
        f"{API}/drivers/me/documents",
        files={"tech_passport_image": ("t.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    assert r.status_code == 200, r.text
    assert r.json()["has_tech_passport"] is True
    assert r.json()["has_license"] is False
    assert r.json()["documents_verified"] is False


@pytest.mark.asyncio
async def test_eski_surat_almashtirilsa_ochiriladi(client, db, user, _no_minio):
    """Almashtirilgan guvohnoma MinIO'da qolib ketmasin — shaxsiy hujjat."""
    await _apply_without_documents(client, user)
    first = await client.post(
        f"{API}/drivers/me/documents",
        files={"license_image": ("l.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    old_key = (await db.execute(
        select(DriverProfile.license_image).where(DriverProfile.user_id == user.id)
    )).scalar_one()
    assert first.status_code == 200

    await client.post(
        f"{API}/drivers/me/documents",
        files={"license_image": ("l2.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    assert old_key in _no_minio


@pytest.mark.asyncio
async def test_bosh_sorov_rad_etiladi(client, user):
    await _apply_without_documents(client, user)
    r = await client.post(f"{API}/drivers/me/documents", headers=auth_headers(user))
    assert r.status_code == 400
    assert "Kamida bitta" in r.json()["detail"]


@pytest.mark.asyncio
async def test_haydovchi_bolmagan_odam_yuklay_olmaydi(client, user):
    r = await client.post(
        f"{API}/drivers/me/documents",
        files={"license_image": ("l.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_rad_etilgan_haydovchi_bu_yoldan_qaytmaydi(client, db, user, admin_user):
    """Rad etilgan haydovchining yo'li — qaytadan ariza, hujjat yuklash emas."""
    profile = await _apply_without_documents(client, user)
    rej = await client.post(
        f"{API}/admin/drivers/{profile['id']}/reject",
        json={"reason": "Hujjat yo'q"},
        headers=auth_headers(admin_user),
    )
    assert rej.status_code == 200, rej.text

    r = await client.post(
        f"{API}/drivers/me/documents",
        files={"license_image": ("l.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    assert r.status_code == 400
    assert "rad etilgan" in r.json()["detail"]


@pytest.mark.asyncio
async def test_yuklangan_rasm_tekshiriladi(client, user):
    await _apply_without_documents(client, user)
    r = await client.post(
        f"{API}/drivers/me/documents",
        files={"license_image": ("l.jpg", b"bu rasm emas", "image/jpeg")},
        headers=auth_headers(user),
    )
    assert r.status_code == 400
