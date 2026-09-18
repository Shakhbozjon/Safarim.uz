"""Lokal ishlab chiqish uchun sinov hisoblari.

Ishlatish:
    python -m scripts.seed_locations     # avval viloyat/tumanlar
    python -m scripts.seed_dev

Nega kerak: lokal test klasteri vaqtinchalik papkada yotadi va vaqti-vaqti
bilan butunlay yo'qoladi (2026-09-18 da shunday bo'ldi). Hisoblarni har safar
qo'lda tiklash o'rniga shu skript ishlatiladi.

FAQAT lokal baza uchun. Parol hammada bir xil va sodda — jonli bazada
ishlatilmasin (skript `DEBUG=False` bo'lsa o'zi to'xtaydi).

Yaratiladigan hisoblar (parol: Test1234!):
    +998901111111  yo'lovchi (ayol — «faqat ayollar» safarini sinash uchun)
    +998902222222  tasdiqlangan haydovchi + doimiy yo'nalish
    +998901112233  super admin
"""
import asyncio
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.driver import DriverProfile
from app.models.enums import (
    AdminRole, DriverStatus, Gender, LuggageSize, PaymentType,
)
from app.models.location import District, Region
from app.models.route import DriverRoute
from app.models.user import User

PASSWORD = "Test1234!"

PASSENGER = "+998901111111"
DRIVER = "+998902222222"
ADMIN = "+998901112233"


async def _get_or_create_user(db, phone: str, **fields) -> tuple[User, bool]:
    user = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
    if user is not None:
        return user, False
    user = User(phone=phone, password_hash=hash_password(PASSWORD), **fields)
    db.add(user)
    await db.flush()
    return user, True


async def seed() -> None:
    if not settings.DEBUG:
        print("DEBUG=False — bu skript faqat lokal baza uchun. To'xtatildi.")
        sys.exit(1)

    async with AsyncSessionLocal() as db:
        regions = (await db.execute(select(Region).order_by(Region.order))).scalars().all()
        if not regions:
            print("Viloyatlar yo'q. Avval: python -m scripts.seed_locations")
            sys.exit(1)

        passenger, new_p = await _get_or_create_user(
            db, PASSENGER,
            full_name="Sinov Yolovchi",
            is_phone_verified=True,
            gender=Gender.female,     # «faqat ayollar» safarlarini sinash uchun
        )
        driver, new_d = await _get_or_create_user(
            db, DRIVER,
            full_name="Sinov Haydovchi",
            is_phone_verified=True,
            is_driver=True,
        )
        admin, new_a = await _get_or_create_user(
            db, ADMIN,
            full_name="Sinov Admin",
            is_phone_verified=True,
            is_admin=True,
            admin_role=AdminRole.super_admin,
        )

        # Haydovchi profili — tasdiqlangan, ya'ni darrov safar e'lon qila oladi
        profile = (await db.execute(
            select(DriverProfile).where(DriverProfile.user_id == driver.id)
        )).scalar_one_or_none()
        if profile is None:
            profile = DriverProfile(
                user_id=driver.id,
                vehicle_make="Chevrolet",
                vehicle_model="Cobalt",
                vehicle_year=2021,
                vehicle_color="Oq",
                vehicle_plate="01A777BC",
                vehicle_seats=4,
                status=DriverStatus.approved,
            )
            db.add(profile)

        # Doimiy yo'nalish — Telegram botdagi e'lon oqimi shunga tayanadi
        route = (await db.execute(
            select(DriverRoute).where(DriverRoute.driver_id == driver.id)
        )).scalar_one_or_none()
        if route is None:
            fargona = next((r for r in regions if "arg'ona" in r.name_uz), regions[0])
            toshkent = next((r for r in regions if r.name_uz.startswith("Toshkent sh")), regions[-1])
            buvayda = (await db.execute(
                select(District).where(
                    District.region_id == fargona.id,
                    District.name_uz == "Buvayda",
                )
            )).scalar_one_or_none()

            import datetime as dt
            db.add(DriverRoute(
                driver_id=driver.id,
                from_region_id=fargona.id,
                from_district_id=buvayda.id if buvayda else None,
                to_region_id=toshkent.id,
                departure_time=dt.time(8, 0),
                return_time=dt.time(16, 0),
                total_seats=4,
                price_per_seat=150_000,
                payment_type=PaymentType.cash,
                luggage_size=LuggageSize.medium,
            ))

        await db.commit()

    def mark(created: bool) -> str:
        return "yaratildi" if created else "bor edi"

    print("Lokal sinov hisoblari tayyor. Parol: " + PASSWORD)
    print(f"  {PASSENGER}  yo'lovchi           ({mark(new_p)})")
    print(f"  {DRIVER}  haydovchi + yo'nalish ({mark(new_d)})")
    print(f"  {ADMIN}  admin               ({mark(new_a)})")


if __name__ == "__main__":
    asyncio.run(seed())
