"""driver_vehicle_year_optional

Avtomobil yili endi arizada so'ralmaydi: u yo'lovchiga hech qayerda
ko'rsatilmasdi (band qilish tasdig'ida ham yo'q), faqat haydovchining o'z
holat sahifasida va admin qatorida turardi — ya'ni bitta ortiqcha maydon
uchun haydovchidan qadam talab qilinardi.

Ustun o'chirilmadi, faqat NULL qabul qiladigan qilindi: eski haydovchilarning
ma'lumoti joyida qoladi va kerak bo'lsa maydonni qaytarish arzon.

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-09-09 18:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, None] = 'd6e7f8a9b0c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'driver_profiles', 'vehicle_year',
        existing_type=sa.Integer(), nullable=True,
    )


def downgrade() -> None:
    # Bo'sh qiymatlarni to'ldirmasdan NOT NULL ga qaytarib bo'lmaydi
    op.execute("UPDATE driver_profiles SET vehicle_year = 2015 WHERE vehicle_year IS NULL")
    op.alter_column(
        'driver_profiles', 'vehicle_year',
        existing_type=sa.Integer(), nullable=False,
    )
