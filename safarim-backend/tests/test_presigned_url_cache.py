"""Bir xil rasm uchun imzolangan havola qayta ishlatiladi.

Havola ichida imzo vaqti bor, shuning uchun ilgari har API javobida manzil
boshqacha chiqardi. Brauzer ham, Next optimizatori ham buni yangi rasm deb
bilib, avatarni har sahifada qaytadan yuklab olardi.
"""
from unittest.mock import MagicMock

from app.services import storage_service as mod
from app.services.storage_service import StorageService


def _service():
    svc = StorageService()
    client = MagicMock()
    client.generate_presigned_url.side_effect = lambda *a, **kw: f"url-{client.generate_presigned_url.call_count}"
    svc._public_client = client
    return svc, client


def _patch_time(monkeypatch, value):
    monkeypatch.setattr(mod.time, "monotonic", lambda: value)


def test_bir_xil_kalit_bir_xil_havola(monkeypatch):
    svc, client = _service()
    monkeypatch.setattr(mod.settings, "MINIO_PUBLIC_ENDPOINT", "cdn.example")
    _patch_time(monkeypatch, 1000.0)
    a = svc.get_url("avatars/x.jpg", "photos")
    _patch_time(monkeypatch, 1000.0 + 1799)
    b = svc.get_url("avatars/x.jpg", "photos")
    assert a == b
    assert client.generate_presigned_url.call_count == 1


def test_yarim_muddatdan_keyin_yangilanadi(monkeypatch):
    """Berilgan havola kamida 30 daqiqa amal qilishi kerak."""
    svc, client = _service()
    monkeypatch.setattr(mod.settings, "MINIO_PUBLIC_ENDPOINT", "cdn.example")
    _patch_time(monkeypatch, 1000.0)
    a = svc.get_url("avatars/x.jpg", "photos")
    _patch_time(monkeypatch, 1000.0 + 1800)
    b = svc.get_url("avatars/x.jpg", "photos")
    assert a != b


def test_har_xil_kalit_aralashmaydi(monkeypatch):
    svc, _ = _service()
    monkeypatch.setattr(mod.settings, "MINIO_PUBLIC_ENDPOINT", "cdn.example")
    _patch_time(monkeypatch, 1000.0)
    assert svc.get_url("avatars/a.jpg", "photos") != svc.get_url("avatars/b.jpg", "photos")
    assert svc.get_url("avatars/a.jpg", "photos") != svc.get_url("avatars/a.jpg", "docs")


def test_xato_keshlanmaydi(monkeypatch):
    svc, client = _service()
    monkeypatch.setattr(mod.settings, "MINIO_PUBLIC_ENDPOINT", "cdn.example")
    _patch_time(monkeypatch, 1000.0)
    client.generate_presigned_url.side_effect = RuntimeError("minio yo'q")
    assert svc.get_url("avatars/x.jpg", "photos") == ""
    client.generate_presigned_url.side_effect = None
    client.generate_presigned_url.return_value = "ok"
    assert svc.get_url("avatars/x.jpg", "photos") == "ok"


def test_kesh_cheksiz_osmaydi(monkeypatch):
    svc, _ = _service()
    monkeypatch.setattr(mod.settings, "MINIO_PUBLIC_ENDPOINT", "cdn.example")
    monkeypatch.setattr(mod, "_URL_CACHE_MAX", 10)
    _patch_time(monkeypatch, 1000.0)
    for i in range(10):
        svc.get_url(f"avatars/{i}.jpg", "photos")
    _patch_time(monkeypatch, 1000.0 + 3000)
    svc.get_url("avatars/yangi.jpg", "photos")
    assert len(svc._url_cache) == 1
