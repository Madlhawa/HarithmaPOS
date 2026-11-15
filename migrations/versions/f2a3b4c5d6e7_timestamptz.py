"""Every moment in time is stored as timestamptz (UTC)

Until now timestamps were naive "timestamp without time zone" columns that
happened to hold UTC. They become "timestamp with time zone", reading the
stored values as UTC, so the database itself knows what they mean and no
value can be mistaken for shop time. Dates (attendance days, payroll
months) and times of day stay as they are: they are calendar facts.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-11-15
"""
from alembic import op


revision = 'f2a3b4c5d6e7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def _columns(bind, data_type):
    return bind.exec_driver_sql("""
        SELECT table_name, column_name FROM information_schema.columns
        WHERE table_schema = current_schema() AND data_type = %s
        ORDER BY table_name, column_name
    """, (data_type,)).fetchall()


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return      # SQLite (tests) keeps no time zone; the UTCDateTime type handles it
    # The payment ledger's trigger refuses UPDATE; changing a column type is DDL, which it does not see.
    for table, column in _columns(bind, 'timestamp without time zone'):
        op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
                   f'TYPE timestamptz USING "{column}" AT TIME ZONE \'UTC\'')


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return
    for table, column in _columns(bind, 'timestamp with time zone'):
        op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
                   f'TYPE timestamp USING "{column}" AT TIME ZONE \'UTC\'')
