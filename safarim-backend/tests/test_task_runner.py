"""Celery vazifalarini bajarish qoidalari.

Jonli saytda (2026-09-08) `expire_old_trips` va `process_confirmations`
har safar shu xato bilan tugardi:

    InterfaceError: cannot perform operation: another operation is in progress

Sababi: har vazifa yangi event loop ochardi, baza ulanishlari esa umumiy
hovuzda qolib, keyingi loop'da qayta ishlatilardi. Quyidagi testlar shu
ikki qoidani qo'riqlaydi — ulanishlar vazifadan keyin yopiladi va fon
rejimidagi Telegram xabarlari loop yopilishidan oldin kutiladi.
"""
import asyncio

from app.services import notification_service
from app.tasks import runner


class _FakeEngine:
    def __init__(self) -> None:
        self.disposed = 0

    async def dispose(self) -> None:
        self.disposed += 1


def _queue_fake_send(flag: dict, delay: float = 0.05) -> asyncio.Task:
    async def send() -> None:
        await asyncio.sleep(delay)
        flag["yuborildi"] = True

    task = asyncio.create_task(send())
    notification_service._PENDING_SENDS.add(task)
    task.add_done_callback(notification_service._PENDING_SENDS.discard)
    return task


def test_run_task_disposes_connections(monkeypatch):
    fake = _FakeEngine()
    monkeypatch.setattr("app.db.session.engine", fake)

    assert runner.run_task(lambda: asyncio.sleep(0, result="natija")) == "natija"
    # Ulanishlar yopilmasa, keyingi vazifa ularni boshqa loop'da olib xato berardi
    assert fake.disposed == 1


def test_run_task_waits_for_background_telegram_sends(monkeypatch):
    monkeypatch.setattr("app.db.session.engine", _FakeEngine())
    flag = {"yuborildi": False}

    async def main():
        _queue_fake_send(flag)
        return "ok"

    runner.run_task(main)
    assert flag["yuborildi"] is True


def test_run_task_does_not_hang_on_stuck_send(monkeypatch):
    monkeypatch.setattr("app.db.session.engine", _FakeEngine())
    monkeypatch.setattr(runner, "PENDING_TIMEOUT", 0.05)
    flag = {"yuborildi": False}

    async def main():
        _queue_fake_send(flag, delay=30)   # "osilib qolgan" xabar
        return "ok"

    assert runner.run_task(main) == "ok"
    assert flag["yuborildi"] is False      # kutildi, lekin cheksiz emas


def test_two_runs_in_a_row(monkeypatch):
    fake = _FakeEngine()
    monkeypatch.setattr("app.db.session.engine", fake)

    assert runner.run_task(lambda: asyncio.sleep(0, result=1)) == 1
    assert runner.run_task(lambda: asyncio.sleep(0, result=2)) == 2
    assert fake.disposed == 2


def test_engine_error_does_not_lose_result(monkeypatch):
    """Ulanishni yopishdagi nosozlik bajarilgan ishni bekor qilmaydi."""
    class _BrokenEngine:
        async def dispose(self):
            raise RuntimeError("ulanish yopilmadi")

    monkeypatch.setattr("app.db.session.engine", _BrokenEngine())
    assert runner.run_task(lambda: asyncio.sleep(0, result="natija")) == "natija"
