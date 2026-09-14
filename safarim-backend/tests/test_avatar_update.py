"""Profil rasmini almashtirish — yangi rasm haqiqatan saqlanadimi.

User xabari: yangi rasm yuklansa ham eskisi qaytib qolyapti.
Bu yerda MinIO'ning faqat TARMOQ qismi mock qilinadi — `upload()` ning o'zi
(tekshirish, kichraytirish, kalit yasash) haqiqiy holda ishlaydi.
"""
import io

import pytest
from PIL import Image

from app.services.storage_service import storage_service
from tests.conftest import auth_headers

API = "/api/v1"


def _jpeg(w=1200, h=900) -> bytes:
    img = Image.new("RGB", (w, h))
    px = img.load()
    for x in range(0, w, 3):
        for y in range(0, h, 3):
            px[x, y] = ((x * 7) % 256, (y * 5) % 256, (x + y) % 256)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def _fake_minio(monkeypatch):
    """Faqat tarmoqni to'sadi — `upload()` mantiqi haqiqiy qoladi."""
    stored = {}

    class _Client:
        def put_object(self, Bucket, Key, Body, ContentType):
            stored[Key] = Body

        def head_bucket(self, Bucket):
            return {}

        def generate_presigned_url(self, *a, **kw):
            return "https://cdn.test/" + kw.get("Params", {}).get("Key", "x")

    monkeypatch.setattr(type(storage_service), "client", property(lambda self: _Client()))
    monkeypatch.setattr(type(storage_service), "public_client", property(lambda self: _Client()))
    monkeypatch.setattr(storage_service, "_ensure_bucket", lambda bucket: None)
    return stored


@pytest.mark.asyncio
async def test_yangi_rasm_javobda_qaytadi(client, user, _fake_minio):
    r = await client.post(
        f"{API}/users/me/photo",
        files={"photo": ("a.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    assert r.status_code == 200, r.text
    assert r.json()["profile_photo"], "javobda rasm yo'q"
    assert len(_fake_minio) == 1, "MinIO'ga saqlanmadi"


@pytest.mark.asyncio
async def test_bazada_yangi_kalit_turadi(client, db, user, _fake_minio):
    await client.post(
        f"{API}/users/me/photo",
        files={"photo": ("a.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    await db.refresh(user)
    assert user.profile_photo, "bazada rasm kalitiga yozilmadi"
    assert user.profile_photo in _fake_minio


@pytest.mark.asyncio
async def test_rasm_yuklagach_PUT_uni_ochirmaydi(client, db, user, _fake_minio):
    """Frontend avval rasmni yuklab, KEYIN `PUT /users/me` chaqiradi va
    o'sha ikkinchi javobni keshga yozadi. Agar PUT javobida rasm bo'lmasa,
    ekranda eski rasm qaytib qoladi — user aynan shundan shikoyat qildi."""
    up = await client.post(
        f"{API}/users/me/photo",
        files={"photo": ("a.jpg", _jpeg(), "image/jpeg")},
        headers=auth_headers(user),
    )
    yangi = up.json()["profile_photo"]

    put = await client.put(
        f"{API}/users/me",
        json={"full_name": "Yangi Ism", "email": None, "talk_level": "normal"},
        headers=auth_headers(user),
    )
    assert put.status_code == 200, put.text
    assert put.json()["profile_photo"] == yangi, (
        "PUT javobida rasm yo'qolgan — frontend shuni keshga yozadi"
    )


@pytest.mark.asyncio
async def test_ikkinchi_marta_yuklash_almashtiradi(client, db, user, _fake_minio):
    """Ikki marta ketma-ket yuklaganda ikkinchisi g'olib bo'lsin."""
    first = await client.post(
        f"{API}/users/me/photo",
        files={"photo": ("a.jpg", _jpeg(800, 600), "image/jpeg")},
        headers=auth_headers(user),
    )
    second = await client.post(
        f"{API}/users/me/photo",
        files={"photo": ("b.jpg", _jpeg(1000, 700), "image/jpeg")},
        headers=auth_headers(user),
    )
    assert first.json()["profile_photo"] != second.json()["profile_photo"]
    await db.refresh(user)
    assert user.profile_photo == list(_fake_minio)[-1]
