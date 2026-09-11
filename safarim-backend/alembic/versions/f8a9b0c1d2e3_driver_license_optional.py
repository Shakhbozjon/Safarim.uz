"""driver_license_optional

Hujjat yuklash ishga tushirish davrida majburiy emas. Sabab dala ma'lumoti:
birinchi haydovchi guvohnoma va texpasportini yangi saytga yuklashga
ishonmadi. Bu bosqichda tekshiruvning haqiqiy shakli boshqacha — admin
haydovchi bilan yuzma-yuz uchrashadi va hujjatni o'sha yerda ko'radi.

Ya'ni tekshiruv olib tashlanmadi, faqat surat majburiy bo'lmay qoldi.
Notanish odam ro'yxatdan o'tadigan bosqichda yuklash yana majburiy
qilinishi kerak.

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-09-11 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f8a9b0c1d2e3'
down_revision: Union[str, None] = 'e7f8a9b0c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'driver_profiles', 'license_image',
        existing_type=sa.String(), nullable=True,
    )


def downgrade() -> None:
    # NOT NULL ga qaytarishdan oldin bo'sh qiymatlarni to'ldirish kerak
    op.execute("UPDATE driver_profiles SET license_image = '' WHERE license_image IS NULL")
    op.alter_column(
        'driver_profiles', 'license_image',
        existing_type=sa.String(), nullable=False,
    )
