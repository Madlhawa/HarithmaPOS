"""Remove the saved RabbitMQ printer settings

Receipts are now printed from the browser, so the RabbitMQ connection
settings (including its encrypted password) are no longer used.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-11-15
"""
from alembic import op


revision = 'a7b8c9d0e1f2'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None

OLD_KEYS = ('printer_enabled', 'rabbitmq_host', 'rabbitmq_port', 'rabbitmq_username', 'rabbitmq_password', 'print_queue')


def upgrade():
    op.execute("DELETE FROM setting WHERE key IN ({})".format(', '.join(f"'{k}'" for k in OLD_KEYS)))


def downgrade():
    pass  # the values are gone; re-enter them on the Settings page of the older version
