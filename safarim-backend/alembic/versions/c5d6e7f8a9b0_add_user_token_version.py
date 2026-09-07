"""add_user_token_version

Parol o'zgarganda eski sessiyalarni uzish uchun. Shu paytgacha parolni
almashtirish hech narsani to'xtatmasdi: berilgan refresh token yana 30 kun
ishlayverardi, ya'ni hisobni egallab olgan odam parol almashtirilgandan keyin
ham kirib turaverardi. Endi har bir token ichida `ver` bo'ladi va u
`users.token_version` ga teng bo'lmasa token qabul qilinmaydi.

Bir tomonlama ta'sir: migratsiyadan keyin hamma eski tokenlarda `ver` yo'q
(0 deb o'qiladi), ustun ham 0 dan boshlanadi — ya'ni hech kim tizimdan
chiqarilmaydi.

Shu bilan birga admin harakatlari turiga ikkita qiymat qo'shiladi: hamyonni
qo'lda to'ldirish va komissiyani to'landi deb belgilash — ilgari pulga
tegadigan bu ikki amal jurnalga umuman yozilmasdi.

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-09-07 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c5d6e7f8a9b0'
down_revision: Union[str, None] = 'b4c5d6e7f8a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'),
    )
    op.execute("ALTER TYPE adminactiontype ADD VALUE IF NOT EXISTS 'wallet_topup'")
    op.execute("ALTER TYPE adminactiontype ADD VALUE IF NOT EXISTS 'commission_paid'")


def downgrade() -> None:
    op.drop_column('users', 'token_version')
    # PostgreSQL enum qiymatini o'chirib bo'lmaydi — enum o'sha holicha qoladi
