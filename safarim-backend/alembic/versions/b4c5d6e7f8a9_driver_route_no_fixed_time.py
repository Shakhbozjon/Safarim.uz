"""driver_route_no_fixed_time

Doimiy yo'nalish endi vaqt saqlamaydi: haydovchi har doim ham yozgan vaqtida
jo'nay olmaydi, shuning uchun vaqt shablonda emas, e'lon qilish paytida
kiritiladi. Mavjud qiymatlar tozalanadi.

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-09-05 01:00:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = 'b4c5d6e7f8a9'
down_revision: Union[str, None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('driver_routes', 'departure_time',
                    existing_type=sa.Time(), nullable=True)
    op.execute("UPDATE driver_routes SET departure_time = NULL, return_time = NULL")


def downgrade() -> None:
    # Vaqtsiz qatorlarga biror qiymat kerak — 08:00 shartli
    op.execute("UPDATE driver_routes SET departure_time = '08:00' WHERE departure_time IS NULL")
    op.alter_column('driver_routes', 'departure_time',
                    existing_type=sa.Time(), nullable=False)
