"""add leads table

Revision ID: 20260228_add_leads
Revises: 20260228_add_v2_tables
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260228_add_leads'
down_revision: Union[str, None] = '20260228_add_v2_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === LEADS TABLE ===
    op.create_table(
        'leads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('program', sa.String(length=50), nullable=True, server_default='classic'),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True, server_default='website'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='new'),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leads_id'), 'leads', ['id'], unique=False)
    op.create_index(op.f('ix_leads_phone'), 'leads', ['phone'], unique=False)


def downgrade() -> None:
    op.drop_table('leads')
