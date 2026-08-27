"""add_telegram_link_purpose

Telegram havolasi ikki ish uchun ishlatiladi: raqamni tasdiqlash va raqamni
almashtirish. Bot kontaktni qabul qilganda qaysi biri ekanini bilishi kerak —
tasdiqlashda raqam hisobdagi raqam bilan solishtiriladi, almashtirishda esa
hisobdagi raqam kelgan raqamga o'rnatiladi.

Shu paytgacha almashtirish umuman yo'q edi: xato raqam bilan ro'yxatdan o'tgan
odam hisobini tuzata olmasdi va tasdiqlanmagani uchun na band qila olardi,
na safar e'lon qila olardi.

Mavjud tokenlar uchun server_default='verify' — eski xatti-harakat saqlanadi.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-08-27 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    purpose = sa.Enum('verify', 'change_phone', name='telegramlinkpurpose')
    purpose.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'telegram_link_tokens',
        sa.Column('purpose', purpose, nullable=False, server_default='verify'),
    )


def downgrade() -> None:
    op.drop_column('telegram_link_tokens', 'purpose')
    sa.Enum(name='telegramlinkpurpose').drop(op.get_bind(), checkfirst=True)
