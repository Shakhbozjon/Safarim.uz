"""Telegramga ulanish o'rnatilmasa qayta uriniladi.

Jonli serverdan tashqariga yo'lda paket yo'qoladi va `sendMessage` ba'zan
«All connection attempts failed» bilan tushardi — guruhga e'lon shunchaki
yo'qolardi. Qayta urinish faqat ULANISH xatosida: so'rov Telegramga yetib
bormagan, demak xabar ikki marta ketmaydi.
"""
import httpx
import pytest

from app.services import telegram_service as tg


class _FakeClient:
    """`httpx.AsyncClient` o'rnida: navbatdagi natijani qaytaradi yoki xato otadi."""

    outcomes: list = []
    calls = 0

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json):
        type(self).calls += 1
        item = type(self).outcomes.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture
def fake(monkeypatch):
    _FakeClient.outcomes = []
    _FakeClient.calls = 0
    monkeypatch.setattr(tg.httpx, "AsyncClient", _FakeClient)
    monkeypatch.setattr(tg, "_CONNECT_RETRY_PAUSES", (0.0, 0.0))
    return _FakeClient


def _ok():
    return httpx.Response(200, json={"ok": True, "result": {"message_id": 7}})


async def test_ulanish_xatosidan_keyin_otadi(fake):
    fake.outcomes = [httpx.ConnectError("All connection attempts failed"), _ok()]
    data = await tg._call("sendMessage", {"chat_id": "1", "text": "x"}, token="t")
    assert data == {"ok": True, "result": {"message_id": 7}}
    assert fake.calls == 2


async def test_ulanish_taymauti_ham_qayta_urinadi(fake):
    fake.outcomes = [httpx.ConnectTimeout("t"), httpx.ConnectTimeout("t"), _ok()]
    assert await tg._call("sendMessage", {}, token="t") is not None
    assert fake.calls == 3


async def test_uch_urinishdan_keyin_toxtaydi(fake):
    fake.outcomes = [httpx.ConnectError("x")] * 5
    assert await tg._call("sendMessage", {}, token="t") is None
    assert fake.calls == 3


async def test_javob_taymautida_qayta_urinmaydi(fake):
    """So'rov yetib borgan bo'lishi mumkin — qayta yuborilsa guruhda ikkita e'lon chiqadi."""
    fake.outcomes = [httpx.ReadTimeout("r"), _ok()]
    assert await tg._call("sendMessage", {}, token="t") is None
    assert fake.calls == 1


async def test_telegram_rad_etsa_qayta_urinmaydi(fake):
    fake.outcomes = [httpx.Response(403, text="bot was kicked"), _ok()]
    assert await tg._call("sendMessage", {}, token="t") is None
    assert fake.calls == 1
