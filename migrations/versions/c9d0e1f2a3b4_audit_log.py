"""Audit log of price, discount, payment, pay, role and setting changes

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-11-15
"""
from alembic import op
import sqlalchemy as sa


revision = 'c9d0e1f2a3b4'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_dttm', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('action', sa.String(length=10), nullable=False),
        sa.Column('entity', sa.String(length=30), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('link_entity', sa.String(length=30), nullable=True),
        sa.Column('link_id', sa.Integer(), nullable=True),
        sa.Column('label', sa.String(length=200), nullable=False),
        sa.Column('field', sa.String(length=60), nullable=True),
        sa.Column('old_value', sa.String(length=255), nullable=True),
        sa.Column('new_value', sa.String(length=255), nullable=True),
        sa.Column('path', sa.String(length=120), nullable=True),
    )
    op.create_index('ix_audit_log_created_dttm', 'audit_log', ['created_dttm'])
    op.create_index('ix_audit_log_category', 'audit_log', ['category'])


def downgrade():
    op.drop_index('ix_audit_log_category', table_name='audit_log')
    op.drop_index('ix_audit_log_created_dttm', table_name='audit_log')
    op.drop_table('audit_log')
