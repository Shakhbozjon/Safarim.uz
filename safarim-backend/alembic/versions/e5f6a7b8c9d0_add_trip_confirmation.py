"""add_trip_confirmation

Ikki tomonlama safar tasdiqi + soxta belgilash jarima ustunlari.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-23 12:00:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Yangi bron holatlari
    op.execute("ALTER TYPE bookingstatus ADD VALUE IF NOT EXISTS 'awaiting_confirmation'")
    op.execute("ALTER TYPE bookingstatus ADD VALUE IF NOT EXISTS 'disputed'")

    # bookings — tasdiq maydonlari ('yes' / 'no' / NULL=jim)
    op.add_column("bookings", sa.Column("driver_confirmed", sa.String(length=3), nullable=True))
    op.add_column("bookings", sa.Column("passenger_confirmed", sa.String(length=3), nullable=True))
    op.add_column("bookings", sa.Column("confirmation_requested_at", sa.DateTime(), nullable=True))
    op.add_column("bookings", sa.Column("driver_denied_reprompt_at", sa.DateTime(), nullable=True))

    # driver_profiles — soxta belgilash jarimasi
    op.add_column(
        "driver_profiles",
        sa.Column("fake_confirmation_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("driver_profiles", sa.Column("fake_count_reset_at", sa.DateTime(), nullable=True))
    op.add_column("driver_profiles", sa.Column("paused_until", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("driver_profiles", "paused_until")
    op.drop_column("driver_profiles", "fake_count_reset_at")
    op.drop_column("driver_profiles", "fake_confirmation_count")
    op.drop_column("bookings", "driver_denied_reprompt_at")
    op.drop_column("bookings", "confirmation_requested_at")
    op.drop_column("bookings", "passenger_confirmed")
    op.drop_column("bookings", "driver_confirmed")
    # PostgreSQL enum qiymatini o'chirib bo'lmaydi — bookingstatus o'zgarmaydi
