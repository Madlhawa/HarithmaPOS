"""Add user role and active flag

Revision ID: b3f1c2d4e5a6
Revises: 67eca949a222
Create Date: 2026-11-11 09:00:00

Users who exist before this change become owners, so nobody loses access.
New users default to counter staff.
"""
from alembic import op
import sqlalchemy as sa


revision = 'b3f1c2d4e5a6'
down_revision = '67eca949a222'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('role', sa.String(length=10), nullable=False, server_default='owner'))
        batch_op.add_column(sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()))
    with op.batch_alter_table('user') as batch_op:
        batch_op.alter_column('role', server_default='staff')


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('active')
        batch_op.drop_column('role')
