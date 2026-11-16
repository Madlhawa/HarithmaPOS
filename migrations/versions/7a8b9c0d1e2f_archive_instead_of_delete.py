"""Customers, items and suppliers are archived instead of deleted

Adds archived_dttm (when) and archived_by_id (who) to each. Nothing is
archived by the upgrade.

Revision ID: 7a8b9c0d1e2f
Revises: c3d4e5f6a7b8
Create Date: 2026-11-16
"""
from alembic import op
import sqlalchemy as sa


revision = '7a8b9c0d1e2f'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None

TABLES = ('customer', 'item', 'supplier')


def upgrade():
    for table in TABLES:
        op.add_column(table, sa.Column('archived_dttm', sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column('archived_by_id', sa.Integer(), nullable=True))
        op.create_foreign_key(f'fk_{table}_archived_by', table, 'user', ['archived_by_id'], ['id'])


def downgrade():
    for table in TABLES:
        op.drop_constraint(f'fk_{table}_archived_by', table, type_='foreignkey')
        op.drop_column(table, 'archived_by_id')
        op.drop_column(table, 'archived_dttm')
