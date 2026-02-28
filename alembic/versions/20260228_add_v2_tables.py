"""add new tables for v2.0

Revision ID: 20260228_add_v2_tables
Revises: initial
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260228_add_v2_tables'
down_revision: Union[str, None] = 'initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === PAYMENTS TABLE ===
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('method', sa.Enum('CASH', 'CARD', 'ONLINE', 'TRANSFER', name='paymentmethod'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'COMPLETED', 'FAILED', 'REFUNDED', name='paymentstatus'), nullable=False),
        sa.Column('payment_date', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)
    op.create_index(op.f('ix_payments_client_id'), 'payments', ['client_id'], unique=False)

    # === EXPENSES TABLE ===
    op.create_table(
        'expenses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category', sa.Enum('RENT', 'SALARY', 'UTILITIES', 'MARKETING', 'EQUIPMENT', 'SUPPLIES', 'TAXES', 'OTHER', name='expensecategory'), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('expense_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('receipt_number', sa.String(length=100), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_expenses_id'), 'expenses', ['id'], unique=False)

    # === SCHEDULES TABLE ===
    op.create_table(
        'schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('trainer_id', sa.Integer(), nullable=True),
        sa.Column('hall', sa.String(length=50), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('max_participants', sa.Integer(), nullable=False, server_default='15'),
        sa.Column('status', sa.Enum('ACTIVE', 'CANCELLED', 'COMPLETED', name='schedulestatus'), nullable=False, server_default='active'),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['trainer_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_schedules_id'), 'schedules', ['id'], unique=False)

    # === ENROLLMENTS TABLE ===
    op.create_table(
        'enrollments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('schedule_id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='enrolled'),
        sa.Column('attended', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['schedule_id'], ['schedules.id'], ),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_enrollments_id'), 'enrollments', ['id'], unique=False)

    # === FEEDBACK TABLE ===
    op.create_table(
        'feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('schedule_id', sa.Integer(), nullable=True),
        sa.Column('feedback_type', sa.Enum('RATING', 'NPS', 'COMPLAINT', 'SUGGESTION', name='feedbacktype'), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('nps_score', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['schedule_id'], ['schedules.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_feedback_id'), 'feedback', ['id'], unique=False)

    # === NOTIFICATIONS TABLE ===
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notification_type', sa.String(length=50), nullable=False, server_default='info'),
        sa.Column('is_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('feedback')
    op.drop_table('enrollments')
    op.drop_table('schedules')
    op.drop_table('expenses')
    op.drop_table('payments')
    
    # Drop enums (PostgreSQL only, SQLite ignores this)
    op.execute('DROP TYPE IF EXISTS paymentmethod')
    op.execute('DROP TYPE IF EXISTS paymentstatus')
    op.execute('DROP TYPE IF EXISTS expensecategory')
    op.execute('DROP TYPE IF EXISTS schedulestatus')
    op.execute('DROP TYPE IF EXISTS feedbacktype')
