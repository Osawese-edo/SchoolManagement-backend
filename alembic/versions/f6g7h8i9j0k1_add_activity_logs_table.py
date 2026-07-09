"""add activity_logs table

Revision ID: f6g7h8i9j0k1
Revises: d1e2f3a4b5c6
Create Date: 2026-07-03 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f6g7h8i9j0k1'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('activity_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=False, index=True),
        sa.Column('user_name', sa.String(255), nullable=False),
        sa.Column('user_role', sa.String(20), nullable=False),
        sa.Column('action', sa.String(255), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True, index=True),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('details', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table('activity_logs')
