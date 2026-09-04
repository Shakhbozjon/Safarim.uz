"""add_driver_routes

Haydovchining doimiy yo'nalishi (shablon) — har kuni bir xil safarni
to'liq forma bilan qayta e'lon qilmaslik uchun.

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-09-04 12:00:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from alembic import op

revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'driver_routes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('driver_id', UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False, unique=True),

        sa.Column('from_region_id', sa.Integer, sa.ForeignKey('regions.id'), nullable=False),
        sa.Column('from_district_id', sa.Integer, sa.ForeignKey('districts.id'), nullable=True),
        sa.Column('from_address', sa.String(255), nullable=True),
        sa.Column('to_region_id', sa.Integer, sa.ForeignKey('regions.id'), nullable=False),
        sa.Column('to_district_id', sa.Integer, sa.ForeignKey('districts.id'), nullable=True),
        sa.Column('to_address', sa.String(255), nullable=True),

        sa.Column('departure_time', sa.Time, nullable=False),
        sa.Column('return_time', sa.Time, nullable=True),

        sa.Column('total_seats', sa.Integer, nullable=False),
        sa.Column('price_per_seat', sa.Integer, nullable=False),

        # create_type=False — bu enumlar bazada allaqachon bor (trips jadvalidan)
        sa.Column('payment_type', ENUM(name='paymenttype', create_type=False),
                  nullable=False, server_default='any'),
        sa.Column('smoking_allowed', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('pets_allowed', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('women_only', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('luggage_size', ENUM(name='luggagesize', create_type=False),
                  nullable=False, server_default='medium'),
        sa.Column('description', sa.Text, nullable=True),

        sa.Column('waypoints', JSONB, nullable=True),

        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('now()')),
    )
    op.create_index('ix_driver_routes_driver_id', 'driver_routes', ['driver_id'])


def downgrade() -> None:
    op.drop_index('ix_driver_routes_driver_id', table_name='driver_routes')
    op.drop_table('driver_routes')
