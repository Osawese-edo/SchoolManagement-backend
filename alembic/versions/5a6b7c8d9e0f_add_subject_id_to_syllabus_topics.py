"""Add subject_id to syllabus_topics, make class_subject_id nullable

Revision ID: 5a6b7c8d9e0f
Revises: 392cf67eb8f3
Create Date: 2026-06-25 21:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "5a6b7c8d9e0f"
down_revision = "392cf67eb8f3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "syllabus_topics",
        sa.Column(
            "subject_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.alter_column(
        "syllabus_topics",
        "class_subject_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_index(
        "ix_syllabus_topics_subject_id", "syllabus_topics", ["subject_id"]
    )


def downgrade():
    op.drop_index("ix_syllabus_topics_subject_id", table_name="syllabus_topics")
    op.alter_column(
        "syllabus_topics",
        "class_subject_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("syllabus_topics", "subject_id")
