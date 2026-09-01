"""booking_pickup_address

Olib ketish joyi endi doim yo'lovchidan olinadi: u band qilishda manzilini
yozadi va haydovchi o'sha yerga boradi. Shu sababli e'londagi tanlov
(trips.door_to_door) keraksiz bo'lib qoldi — har doim bir xil qiymat
saqlaydigan ustun sxemada yolg'on gapiradi, shuning uchun olib tashlanadi.

Koordinata ixtiyoriy: brauzerning geolocation'i orqali olinadi va haydovchiga
xarita havolasi bo'lib ko'rinadi. Xarita provayderi, kalit yoki to'lov
kerak emas.

Mavjud band qilishlarda manzil NULL bo'lib qoladi — ular yaratilganda bunday
maydon yo'q edi va orqaga qarab to'ldirib bo'lmaydi.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-09-01 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('bookings', sa.Column('pickup_address', sa.String(length=255), nullable=True))
    op.add_column('bookings', sa.Column('pickup_lat', sa.Float(), nullable=True))
    op.add_column('bookings', sa.Column('pickup_lng', sa.Float(), nullable=True))
    op.drop_column('trips', 'door_to_door')


def downgrade() -> None:
    op.add_column(
        'trips',
        sa.Column('door_to_door', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.drop_column('bookings', 'pickup_lng')
    op.drop_column('bookings', 'pickup_lat')
    op.drop_column('bookings', 'pickup_address')
