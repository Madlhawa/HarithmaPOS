"""What the customer asked for on a service invoice

The floor supervisor notes the customer's requests when the vehicle comes
in; each is ticked off when done, so nothing is missed at handover.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-11-15
"""
from alembic import op
import sqlalchemy as sa


revision = 'b8c9d0e1f2a3'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'invoice_request',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('invoice_head.id', ondelete='CASCADE'), nullable=False),
        sa.Column('description', sa.String(length=200), nullable=False),
        sa.Column('done', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('done_dttm', sa.DateTime(), nullable=True),
        sa.Column('done_by_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('created_dttm', sa.DateTime(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
    )
    op.create_index('ix_invoice_request_invoice_id', 'invoice_request', ['invoice_id'])


def downgrade():
    op.drop_index('ix_invoice_request_invoice_id', table_name='invoice_request')
    op.drop_table('invoice_request')
