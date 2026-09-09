"""Hisobdan haydovchilik qismini olib tashlash (hisobning o'zi qoladi).

Kerak bo'ladigan holat: odam sinov uchun haydovchi bo'lib ro'yxatdan o'tgan
va uning avtomobil raqami band bo'lib qolgan — raqam unikal, shuning uchun
o'sha mashinani boshqa (yoki keyinchalik o'zi ochadigan haqiqiy) hisobga
biriktirib bo'lmaydi.

Nima qiladi:
  • haydovchi profilini o'chiradi (avtomobil raqami bo'shaydi);
  • guvohnoma suratini MinIO'dan olib tashlaydi;
  • `is_driver` ni false qiladi.

Nima qilmaydi: hisobni o'chirmaydi, safar tarixiga tegmaydi.

Ishlatish (serverda):
    # avval ko'rish — hech narsaga tegmaydi
    docker compose ... exec -T api python -m scripts.remove_driver +998901112233

    # tasdiqlab bajarish
    docker compose ... exec -T api python -m scripts.remove_driver +998901112233 --yes
"""
import asyncio
import sys

from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.driver import DriverProfile
from app.models.enums import TripStatus
from app.models.trip import Trip
from app.models.user import User
from app.services.storage_service import storage_service


async def main() -> None:
    phones = [a for a in sys.argv[1:] if a != "--yes"]
    confirm = "--yes" in sys.argv

    if not phones:
        print("Telefon raqamni ko'rsating, masalan:")
        print("  python -m scripts.remove_driver +998901112233")
        return

    async with AsyncSessionLocal() as db:
        users = (await db.execute(select(User).where(User.phone.in_(phones)))).scalars().all()
        found = {u.phone for u in users}
        for p in phones:
            if p not in found:
                print(f"  [topilmadi] {p}")

        targets = []
        for user in users:
            profile = (await db.execute(
                select(DriverProfile).where(DriverProfile.user_id == user.id)
            )).scalar_one_or_none()

            if profile is None:
                print(f"  [o'tkazildi] {user.phone} — haydovchi profili yo'q")
                continue

            # Faol safar qolsa, uni e'lon qilgan odam haydovchi bo'lmay
            # qoladi — avval safarlarni yopish kerak
            active = (await db.execute(
                select(Trip).where(
                    Trip.driver_id == user.id,
                    Trip.status.in_([TripStatus.active, TripStatus.full, TripStatus.started]),
                ).limit(1)
            )).scalar_one_or_none()
            if active is not None:
                print(f"  [TO'XTATILDI] {user.phone} — faol safari bor, avval uni bekor qiling")
                continue

            targets.append((user, profile))

        if not targets:
            print("\nO'zgartiriladigan hisob yo'q.")
            return

        print("\nHaydovchilik qismi olib tashlanadi:")
        for user, profile in targets:
            print(f"  {user.phone:16} {user.full_name:24} avto: {profile.vehicle_plate} ({profile.status.value})")

        if not confirm:
            print("\nHech narsa o'zgarmadi. Rozi bo'lsangiz oxiriga --yes qo'shing.")
            return

        for user, profile in targets:
            if profile.license_image:
                storage_service.delete_file(profile.license_image, settings.MINIO_BUCKET_DOCUMENTS)
            plate = profile.vehicle_plate
            await db.delete(profile)
            user.is_driver = False
            print(f"  {user.phone} → haydovchilik olib tashlandi, {plate} raqami bo'shadi")

        await db.commit()
        print("\nTayyor.")


if __name__ == "__main__":
    asyncio.run(main())
