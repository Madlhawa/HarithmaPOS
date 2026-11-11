"""Add settings table

Revision ID: c7d8e9f0a1b2
Revises: b3f1c2d4e5a6
Create Date: 2026-11-11 10:00:00

Holds the values from the Settings page. Empty at first: every setting falls
back to the environment (.env) until an owner saves it.
"""
from alembic import op
import sqlalchemy as sa


revision = 'c7d8e9f0a1b2'
down_revision = 'b3f1c2d4e5a6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'setting',
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('update_dttm', sa.DateTime(), nullable=False),
        sa.Column('updated_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by_id'], ['user.id']),
        sa.PrimaryKeyConstraint('key'),
    )


def downgrade():
    op.drop_table('setting')
