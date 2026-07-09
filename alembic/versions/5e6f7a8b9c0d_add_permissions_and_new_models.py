"""add permissions column and syllabus_topics, time_periods, time_table_entries

Revision ID: 5e6f7a8b9c0d
Revises: 4d0e939dceb2
Create Date: 2026-06-24 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '5e6f7a8b9c0d'
down_revision: Union[str, None] = '4d0e939dceb2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("permissions", postgresql.JSON(astext_type=sa.Text()), nullable=True))

    op.create_table(
        "time_periods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )

    op.create_table(
        "syllabus_topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("class_subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("class_subjects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("term_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("syllabus_topics.id", ondelete="CASCADE"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("week_number", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "time_table_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("time_period_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("time_periods.id"), nullable=False),
        sa.Column("class_subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("class_subjects.id"), nullable=False),
        sa.Column("room", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("time_table_entries")
    op.drop_table("syllabus_topics")
    op.drop_table("time_periods")
    op.drop_column("users", "permissions")
