"""Foydalanuvchini bazadan butunlay o'chirish (sinov hisoblari uchun).

⚠️ Bu QAYTARIB BO'LMAYDIGAN amal. Saytdagi «Hisobni o'chirish» tugmasidan
farqi shunda: u ma'lumotni anonimlashtiradi va yozuvni qoldiradi (safar
tarixi boshqa odamlarda ham bor). Bu skript esa qatorni butunlay o'chiradi —
faqat o'zingiz yaratgan sinov hisoblari uchun.

Bazada `ON DELETE` qoidalari yo'q, shuning uchun bog'liq yozuvlar to'g'ri
tartibda qo'lda o'chiriladi.

Ishlatish (serverda):
    # avval nima o'chishini ko'rsatadi, hech narsaga tegmaydi
    docker compose ... exec -T api python -m scripts.delete_users +998991111111

    # tasdiqlab o'chirish
    docker compose ... exec -T api python -m scripts.delete_users +998991111111 --yes
"""
import asyncio
import sys
import uuid

from sqlalchemy import delete, func, or_, select

from app.db.session import AsyncSessionLocal
from app.models.admin import AdminAction
from app.models.booking import Booking
from app.models.driver import DriverProfile
from app.models.message import Message
from app.models.notification import Notification
from app.models.otp import OtpCode
from app.models.payment import DriverMonthlyCommission, Payment
from app.models.review import Review
from app.models.route import DriverRoute
from app.models.telegram import TelegramLinkToken
from app.models.trip import Trip, TripWaypoint
from app.models.user import User
from app.models.wallet import DriverWallet, WalletTopupPayment, WalletTransaction


async def _collect(db, phones: list[str]):
    """O'chiriladigan foydalanuvchilar va ular bilan bog'liq yozuvlarni topadi."""
    users = (await db.execute(select(User).where(User.phone.in_(phones)))).scalars().all()
    found = {u.phone for u in users}
    missing = [p for p in phones if p not in found]

    admins = [u for u in users if u.is_admin]
    users = [u for u in users if not u.is_admin]

    user_ids = [u.id for u in users]
    trip_ids = list((await db.scalars(
        select(Trip.id).where(Trip.driver_id.in_(user_ids))
    )).all()) if user_ids else []

    # Safarlarga tegishli barcha bronlar (begonalarniki ham) + o'z bronlari
    booking_ids = list((await db.scalars(
        select(Booking.id).where(
            or_(Booking.passenger_id.in_(user_ids), Booking.trip_id.in_(trip_ids))
        )
    )).all()) if user_ids else []

    others = 0
    if booking_ids:
        others = await db.scalar(
            select(func.count(Booking.id)).where(
                Booking.id.in_(booking_ids), Booking.passenger_id.notin_(user_ids)
            )
        ) or 0

    return users, admins, missing, trip_ids, booking_ids, others


async def _delete(db, users, trip_ids, booking_ids, phones):
    user_ids = [u.id for u in users]

    async def wipe(model, condition):
        res = await db.execute(delete(model).where(condition))
        return res.rowcount or 0

    counts = {}
    if booking_ids:
        counts["messages"] = await wipe(Message, Message.booking_id.in_(booking_ids))
        counts["reviews"] = await wipe(Review, Review.booking_id.in_(booking_ids))
        counts["payments"] = await wipe(Payment, Payment.booking_id.in_(booking_ids))
        counts["wallet_transactions"] = await wipe(
            WalletTransaction, WalletTransaction.booking_id.in_(booking_ids)
        )
    # Bu odam yozgan yoki u haqida yozilgan boshqa baholar
    counts["reviews_other"] = await wipe(
        Review, or_(Review.reviewer_id.in_(user_ids), Review.reviewee_id.in_(user_ids))
    )
    counts["messages_other"] = await wipe(Message, Message.sender_id.in_(user_ids))
    if booking_ids:
        counts["bookings"] = await wipe(Booking, Booking.id.in_(booking_ids))
    if trip_ids:
        counts["trip_waypoints"] = await wipe(TripWaypoint, TripWaypoint.trip_id.in_(trip_ids))
        counts["admin_actions_trip"] = await wipe(AdminAction, AdminAction.target_trip_id.in_(trip_ids))
        counts["trips"] = await wipe(Trip, Trip.id.in_(trip_ids))

    # Hamyon: tranzaksiyalar hamyonga bog'langan
    wallet_ids = list((await db.scalars(
        select(DriverWallet.id).where(DriverWallet.driver_id.in_(user_ids))
    )).all())
    if wallet_ids:
        counts["wallet_transactions_rest"] = await wipe(
            WalletTransaction, WalletTransaction.wallet_id.in_(wallet_ids)
        )
    counts["driver_wallets"] = await wipe(DriverWallet, DriverWallet.driver_id.in_(user_ids))
    counts["wallet_topups"] = await wipe(WalletTopupPayment, WalletTopupPayment.driver_id.in_(user_ids))
    counts["commissions"] = await wipe(
        DriverMonthlyCommission, DriverMonthlyCommission.driver_id.in_(user_ids)
    )
    counts["driver_routes"] = await wipe(DriverRoute, DriverRoute.driver_id.in_(user_ids))
    # Haydovchi profilida `verified_by` ham users ga qaraydi — bo'shatamiz
    await db.execute(
        DriverProfile.__table__.update()
        .where(DriverProfile.verified_by.in_(user_ids))
        .values(verified_by=None)
    )
    counts["driver_profiles"] = await wipe(DriverProfile, DriverProfile.user_id.in_(user_ids))
    counts["notifications"] = await wipe(Notification, Notification.user_id.in_(user_ids))
    counts["telegram_tokens"] = await wipe(TelegramLinkToken, TelegramLinkToken.user_id.in_(user_ids))
    counts["otp_codes"] = await wipe(OtpCode, OtpCode.phone.in_(phones))
    counts["admin_actions"] = await wipe(
        AdminAction, or_(AdminAction.admin_id.in_(user_ids), AdminAction.target_user_id.in_(user_ids))
    )
    counts["users"] = await wipe(User, User.id.in_(user_ids))

    await db.commit()
    return counts


async def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--yes"]
    confirm = "--yes" in sys.argv

    if not args:
        print("Telefon raqamlarni ko'rsating, masalan:")
        print("  python -m scripts.delete_users +998991111111 +998992222222")
        return

    async with AsyncSessionLocal() as db:
        users, admins, missing, trip_ids, booking_ids, others = await _collect(db, args)

        for p in missing:
            print(f"  [topilmadi] {p}")
        for u in admins:
            print(f"  [O'TKAZIB YUBORILDI] {u.phone} — bu ADMIN hisobi, o'chirilmaydi")

        if not users:
            print("\nO'chiriladigan hisob yo'q.")
            return

        print("\nO'chiriladi:")
        for u in users:
            print(f"  {u.phone:16} {u.full_name}")
        print(f"\n  safarlar: {len(trip_ids)} ta")
        print(f"  band qilishlar: {len(booking_ids)} ta")
        if others:
            print(f"  ⚠️  shundan {others} tasi BOSHQA odamlarniki (shu safarlarga bron qilgan)")

        if not confirm:
            print("\nHech narsa o'chirilmadi. Rozi bo'lsangiz oxiriga --yes qo'shing.")
            return

        counts = await _delete(db, users, trip_ids, booking_ids, args)
        print("\nO'chirildi:")
        for table, n in counts.items():
            if n:
                print(f"  {table}: {n}")
        print("\nTayyor.")


if __name__ == "__main__":
    asyncio.run(main())
