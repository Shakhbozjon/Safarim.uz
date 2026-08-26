"""add_user_gender

"Faqat ayollar" safarlarini haqiqiy qilish uchun jins maydoni.

Shu paytgacha trip.women_only shunchaki yorliq edi: band qilishda hech qanday
tekshiruv yo'q edi va erkak yo'lovchi bemalol joy olishi mumkin edi.

Maydon nullable: ro'yxatdan o'tishda so'ralmaydi, faqat "faqat ayollar"
safarini band qilmoqchi bo'lganda so'raladi. NULL = hali so'ralmagan.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-08-26 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    gender = sa.Enum('female', 'male', name='gender')
    gender.create(op.get_bind(), checkfirst=True)
    op.add_column('users', sa.Column('gender', gender, nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'gender')
    sa.Enum(name='gender').drop(op.get_bind(), checkfirst=True)
