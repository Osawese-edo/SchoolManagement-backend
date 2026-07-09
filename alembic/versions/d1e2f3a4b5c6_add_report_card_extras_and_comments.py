"""add report_card_extras and teacher_comment columns

Revision ID: d1e2f3a4b5c6
Revises: 88a6507e1b73
Create Date: 2026-07-01 07:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = '88a6507e1b73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('report_card_extras',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('students.id', ondelete='CASCADE'), nullable=False),
        sa.Column('term_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('academic_terms.id'), nullable=False),
        sa.Column('times_school_opened', sa.Integer(), nullable=True),
        sa.Column('times_present', sa.Integer(), nullable=True),
        sa.Column('times_absent', sa.Integer(), nullable=True),
        sa.Column('punctuality', sa.String(50), nullable=True),
        sa.Column('neatness', sa.String(50), nullable=True),
        sa.Column('leadership', sa.String(50), nullable=True),
        sa.Column('demeanour', sa.String(50), nullable=True),
        sa.Column('literacy', sa.String(50), nullable=True),
        sa.Column('sporting', sa.String(50), nullable=True),
        sa.Column('cultural', sa.String(50), nullable=True),
        sa.Column('proprietors_remarks', sa.Text(), nullable=True),
        sa.Column('teacher_remark', sa.Text(), nullable=True),
        sa.Column('tuition_fee', sa.Numeric(10, 2), nullable=True),
        sa.Column('other_fees', sa.Numeric(10, 2), nullable=True),
        sa.Column('total_fees', sa.Numeric(10, 2), nullable=True),
        sa.Column('next_term_begin', sa.Date(), nullable=True),
        sa.Column('class_teacher_comment', sa.Text(), nullable=True),
        sa.Column('head_teacher_comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('student_id', 'term_id', name='uq_student_term_extra'),
    )
    op.add_column('academic_records', sa.Column('teacher_comment', sa.Text(), nullable=True))
    op.add_column('assessment_scores', sa.Column('teacher_comment', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('assessment_scores', 'teacher_comment')
    op.drop_column('academic_records', 'teacher_comment')
    op.drop_table('report_card_extras')
