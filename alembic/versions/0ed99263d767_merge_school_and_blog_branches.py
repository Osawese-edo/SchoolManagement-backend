"""merge school and blog branches

Revision ID: 0ed99263d767
Revises: a1b2c3d4e5f6, 5e6f7a8b9c0d
Create Date: 2026-06-24 22:31:49.446413

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0ed99263d767'
down_revision: Union[str, None] = ('a1b2c3d4e5f6', '5e6f7a8b9c0d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
