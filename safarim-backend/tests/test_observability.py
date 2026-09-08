"""Xato kuzatuvi (Sentry) sozlamalari.

Muhimi: DSN bo'lmasa hech narsa yoqilmaydi (lokal ishlash buzilmasin), DSN
bo'lsa esa shaxsiy ma'lumot yuborilmaydi — bu saytda telefon raqamlar bor.
"""
from app.core import observability
from app.core.config import settings


def test_disabled_without_dsn(monkeypatch):
    monkeypatch.setattr(settings, "SENTRY_DSN", "")
    assert observability.init_sentry("api") is False


def test_enabled_with_dsn_and_pii_off(monkeypatch):
    monkeypatch.setattr(settings, "SENTRY_DSN", "https://public@sentry.example/1")
    captured = {}

    class _FakeSdk:
        @staticmethod
        def init(**kwargs):
            captured.update(kwargs)

        @staticmethod
        def set_tag(key, value):
            captured[f"tag:{key}"] = value

    monkeypatch.setitem(__import__("sys").modules, "sentry_sdk", _FakeSdk)

    assert observability.init_sentry("worker") is True
    assert captured["dsn"] == "https://public@sentry.example/1"
    # Telefon raqam va boshqa shaxsiy ma'lumot Sentry'ga ketmaydi
    assert captured["send_default_pii"] is False
    assert captured["max_request_body_size"] == "never"
    # API va worker xatolari ajratilsin
    assert captured["tag:component"] == "worker"
