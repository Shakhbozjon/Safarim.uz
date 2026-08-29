"""add_password_reset_link_purpose

Parolni unutgan foydalanuvchining Telegrami ulanmagan bo'lsa, kodni unga
yuborishning imkoni yo'q edi — sahifa "administrator bilan bog'laning" deb
tugab qolardi.

Yechim: o'sha bot oqimi, uchinchi maqsad bilan. Foydalanuvchi botga kontaktini
ulashadi; raqam hisobdagi raqamga mos kelsa chat bog'lanadi va tiklash kodi
o'sha chatga yuboriladi.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-08-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE telegramlinkpurpose ADD VALUE IF NOT EXISTS 'password_reset'")


def downgrade() -> None:
    # PostgreSQL enum qiymatini o'chirishni qo'llab-quvvatlamaydi. Qiymat
    # qolaveradi — u ishlatilmasa zarari yo'q.
    pass
