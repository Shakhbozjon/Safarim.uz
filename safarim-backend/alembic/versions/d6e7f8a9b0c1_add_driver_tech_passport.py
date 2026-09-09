"""add_driver_tech_passport

Haydovchi arizasiga texpasport rasmi qo'shiladi. Shu paytgacha avtomobil
raqami qo'lda yozilardi va uni hech narsa bilan solishtirib bo'lmasdi —
admin faqat guvohnomani ko'rardi, mashina esa umuman tekshirilmasdi.
Endi admin texpasportdagi raqam haydovchi yozgan raqamga mos kelishini
ko'zi bilan tekshiradi.

Ustun nullable: bu talab kiritilgunga qadar tasdiqlangan haydovchilarda
rasm yo'q. Ularni majburan qayta ariza berishga tushirish jonli bazadagi
ishlayotgan haydovchilarni to'xtatib qo'yardi.

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-09-09 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd6e7f8a9b0c1'
down_revision: Union[str, None] = 'c5d6e7f8a9b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'driver_profiles',
        sa.Column('tech_passport_image', sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('driver_profiles', 'tech_passport_image')
