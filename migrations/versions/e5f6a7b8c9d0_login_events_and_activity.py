"""Sign-in events, last seen and daily activity, for the developer page

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-14
"""
from alembic import op
import sqlalchemy as sa


revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_seen_dttm', sa.DateTime(), nullable=True))

    op.create_table(
        'login_event',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('outcome', sa.String(length=20), nullable=False),
        sa.Column('ip', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=200), nullable=True),
        sa.Column('created_dttm', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_login_event_user_id', 'login_event', ['user_id'])
    op.create_index('ix_login_event_created_dttm', 'login_event', ['created_dttm'])

    op.create_table(
        'user_activity_day',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('requests', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'day', name='uq_user_activity_day'),
    )
    op.create_index('ix_user_activity_day_day', 'user_activity_day', ['day'])


def downgrade():
    op.drop_index('ix_user_activity_day_day', table_name='user_activity_day')
    op.drop_table('user_activity_day')
    op.drop_index('ix_login_event_created_dttm', table_name='login_event')
    op.drop_index('ix_login_event_user_id', table_name='login_event')
    op.drop_table('login_event')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('last_seen_dttm')
