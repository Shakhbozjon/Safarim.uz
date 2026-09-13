"""Rasm yuklash yo'lidagi ikki himoya.

1. «Rasm bombasi» — siqilgan fayl kichik bo'lsa ham ochilganda yuzlab megabayt
   joy egallashi mumkin. Shuning uchun OCHISHDAN OLDIN piksel soni tekshiriladi.
2. Yuklash endpointlari rate limit ostida — PIL dekodi protsessorni yeydi,
   ro'yxatdan o'tish esa bepul va ochiq.
"""
import io

import pytest
from PIL import Image

from app.core import ratelimit
from app.services import image_validation
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


def _jpeg(w=800, h=500) -> bytes:
    img = Image.new("RGB", (w, h))
    px = img.load()
    for x in range(w):
        for y in range(h):
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


# ─── 1. Piksel bombasi ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_juda_katta_rasm_rad_etiladi(client, user, monkeypatch):
    """Chegarani kichraytirib sinaymiz — haqiqiy bomba yasash uchun testda
    gigabaytlab xotira kerak bo'lardi, mantiq esa aynan bir xil."""
    monkeypatch.setattr(image_validation, "_MAX_PIXELS", 100_000)

    r = await client.post(
        f"{API}/drivers/apply",
        data=CAR,
        files={"license_image": ("l.jpg", _jpeg(800, 500), "image/jpeg")},  # 400 000 piksel
        headers=auth_headers(user),
    )
    assert r.status_code == 400
    # ⚠️ Xabar «rasm emas» bo'lib qolmasligi kerak — o'lcham haqida bo'lsin
    assert "katta" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_odatiy_telefon_surati_otadi(client, user):
    """Chegara haqiqiy suratlarga xalaqit bermasin."""
    r = await client.post(
        f"{API}/drivers/apply",
        data=CAR,
        files={"license_image": ("l.jpg", _jpeg(1200, 900), "image/jpeg")},
        headers=auth_headers(user),
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_chegara_haqiqiy_suratdan_ancha_baland():
    """40 mln piksel ≈ 6300x6300 — eng yaxshi telefon ham buncha bermaydi."""
    assert image_validation._MAX_PIXELS >= 40_000_000
    # 12 MP (4000x3000) — zamonaviy telefon surati — bemalol sig'sin
    assert 4000 * 3000 < image_validation._MAX_PIXELS


# ─── 2. Yuklash rate limiti ──────────────────────────────────────────────────

@pytest.fixture
def _spy_hits(monkeypatch):
    """`_hit` chaqiruvlarini yozib boradi (Redis testda yo'q — fail-open)."""
    hits = []

    async def _fake_hit(bucket, limit, window):
        hits.append(bucket)

    monkeypatch.setattr(ratelimit, "_hit", _fake_hit)
    return hits


@pytest.mark.asyncio
async def test_ariza_yuklashi_cheklangan(client, user, _spy_hits):
    await client.post(
        f"{API}/drivers/apply",
        data=CAR,
        files={"license_image": ("l.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    assert any(b.startswith("upload:ip:") for b in _spy_hits)
    assert any(b.startswith("upload:user:") for b in _spy_hits)


@pytest.mark.asyncio
async def test_hujjat_yuklashi_cheklangan(client, user, _spy_hits):
    await client.post(f"{API}/drivers/apply", data=CAR, headers=auth_headers(user))
    _spy_hits.clear()

    await client.post(
        f"{API}/drivers/me/documents",
        files={"license_image": ("l.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    assert any(b.startswith("upload:user:") for b in _spy_hits)


@pytest.mark.asyncio
async def test_avatar_yuklashi_cheklangan(client, user, _spy_hits):
    await client.post(
        f"{API}/users/me/photo",
        files={"photo": ("a.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    assert any(b.startswith("upload:user:") for b in _spy_hits)
