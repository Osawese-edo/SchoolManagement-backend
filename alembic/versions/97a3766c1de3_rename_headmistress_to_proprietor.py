"""rename_headmistress_to_proprietor

Revision ID: 97a3766c1de3
Revises: 5a6b7c8d9e0f
Create Date: 2026-06-27 15:48:26.011455

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '97a3766c1de3'
down_revision: Union[str, None] = '5a6b7c8d9e0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE users SET role = 'proprietor' WHERE role = 'headmistress'")
    op.execute("UPDATE staff SET role = 'proprietor' WHERE role = 'headmistress'")


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'headmistress' WHERE role = 'proprietor'")
    op.execute("UPDATE staff SET role = 'headmistress' WHERE role = 'proprietor'")
