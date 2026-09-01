"""add_trip_door_to_door

Band qilingandan keyin "qayerdan olib ketaman?" degan muzokara boshlanardi:
yo'lovchi haydovchiga yozib, joylashuvini tushuntirar yoki yuborardi.

Yechim — muzokarani yo'qotish: olib ketish shakli e'lon qo'yilayotganda
aytiladi. Haydovchi yo'lovchining manziliga borishga rozimi yoki kelishilgan
joydan oladimi — shu bayroq belgilaydi. Kelishilgan joy `from_address` da
allaqachon saqlanadi, yangi ustun kerak emas.

Default false: mavjud e'lonlar avvalgidek "kelishilgan joydan" bo'lib qoladi.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-09-01 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'trips',
        sa.Column('door_to_door', sa.Boolean(), nullable=False, server_default='false'),
    )


def downgrade() -> None:
    op.drop_column('trips', 'door_to_door')
