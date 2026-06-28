"""
Super admin foydalanuvchi yaratish yoki mavjudni admin qilish.

Ishlatish:
    python -m scripts.create_admin

Yoki argumentlar bilan:
    python -m scripts.create_admin --phone +998901234567 --name "Ism Familiya" --password "parol123"
"""
import asyncio
import argparse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.enums import AdminRole
from app.core.security import hash_password


async def create_admin(phone: str, full_name: str, password: str) -> None:
    async with AsyncSessionLocal() as db:
        # Mavjud foydalanuvchini tekshirish
        result = await db.execute(select(User).where(User.phone == phone))
        user = result.scalar_one_or_none()

        if user:
            # Mavjud foydalanuvchini admin qilish
            user.is_admin = True
            user.admin_role = AdminRole.super_admin
            await db.commit()
            print(f"✅ Mavjud foydalanuvchi admin qilindi!")
            print(f"   Telefon  : {user.phone}")
            print(f"   Ism      : {user.full_name}")
            print(f"   Admin rol: super_admin")
        else:
            # Yangi admin foydalanuvchi yaratish
            user = User(
                phone=phone,
                full_name=full_name,
                password_hash=hash_password(password),
                is_phone_verified=True,
                is_admin=True,
                admin_role=AdminRole.super_admin,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"✅ Yangi admin yaratildi!")
            print(f"   Telefon  : {user.phone}")
            print(f"   Ism      : {user.full_name}")
            print(f"   Admin rol: super_admin")

        print(f"\n🔑 Kirish uchun:")
        print(f"   URL   : http://localhost:3000/login")
        print(f"   Telefon: {phone}")
        print(f"   Parol : {password}")
        print(f"\n   Admin panel: http://localhost:3000/admin")


def main():
    parser = argparse.ArgumentParser(description="Admin foydalanuvchi yaratish")
    parser.add_argument("--phone",    default="+998900000001", help="Telefon raqam (+998XXXXXXXXX)")
    parser.add_argument("--name",     default="Super Admin",   help="To'liq ism")
    parser.add_argument("--password", default="admin123",      help="Parol")
    args = parser.parse_args()

    asyncio.run(create_admin(args.phone, args.name, args.password))


if __name__ == "__main__":
    main()
