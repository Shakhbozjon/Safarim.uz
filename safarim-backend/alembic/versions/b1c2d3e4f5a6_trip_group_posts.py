"""Safar e'loni bir nechta guruhda — har biri uchun alohida xabar ID si

Ilgari `trips.telegram_message_id` da bitta ID saqlanardi, chunki lenta
bitta guruhga tashlanardi. Endi e'lon bir nechta guruhga ketadi va safar
holati o'zgarganda hammasini tahrirlash kerak — aks holda qolgan
guruhlarda eskirgan e'lon turib qoladi.

Eski ustun o'chirilmaydi: u "umuman tashlanganmi" belgisi sifatida
ishlatiladi va orqaga moslikni saqlaydi.

Revision ID: b1c2d3e4f5a6
Revises: a9b0c1d2e3f4
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b1c2d3e4f5a6"
down_revision = "a9b0c1d2e3f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trip_group_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("trips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chat_id", sa.String(32), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("trip_id", "chat_id", name="uq_trip_group_post"),
    )
    op.create_index("ix_trip_group_posts_trip_id", "trip_group_posts", ["trip_id"])


def downgrade() -> None:
    op.drop_index("ix_trip_group_posts_trip_id", table_name="trip_group_posts")
    op.drop_table("trip_group_posts")
