"""add_expired_trip_status

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-05 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE tripstatus ADD VALUE IF NOT EXISTS 'expired'")


def downgrade() -> None:
    # PostgreSQL enum qiymatini o'chirish mumkin emas — downgrade qilinmaydi
    pass
