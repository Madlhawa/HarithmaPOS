"""Document states: draft, completed or void, for invoices, item sales and purchase orders

Each document gets doc_status plus who completed or voided it, when, and why
it was voided. A service invoice's job progress (service_status) stays as it
is but no longer decides whether the bill is completed.

Existing data: service invoices whose job is Done are completed (when their
last "Done" was logged, else their last update); item sales and purchase
orders with a completed time are completed; everything else is a draft.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-11-15
"""
from alembic import op
import sqlalchemy as sa


revision = 'e1f2a3b4c5d6'
down_revision = 'd0e1f2a3b4c5'
branch_labels = None
depends_on = None

TABLES = {'invoice_head': 'invoicehead', 'item_invoice_head': 'iteminvoicehead',
          'purchase_order_head': 'purchaseorderhead'}


def upgrade():
    with op.batch_alter_table('invoice_head') as batch:
        batch.add_column(sa.Column('completed_dttm', sa.DateTime(), nullable=True))

    for table, short in TABLES.items():
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column('doc_status', sa.String(10), nullable=False, server_default='draft'))
            batch.add_column(sa.Column('completed_by_id', sa.Integer(), nullable=True))
            batch.add_column(sa.Column('voided_dttm', sa.DateTime(), nullable=True))
            batch.add_column(sa.Column('voided_by_id', sa.Integer(), nullable=True))
            batch.add_column(sa.Column('void_reason', sa.String(200), nullable=True))
            batch.create_foreign_key(f'fk_{table}_completed_by', 'user', ['completed_by_id'], ['id'])
            batch.create_foreign_key(f'fk_{table}_voided_by', 'user', ['voided_by_id'], ['id'])
            batch.create_check_constraint(f'ck_{short}_doc_status', "doc_status IN ('draft', 'completed', 'void')")
            batch.create_index(f'ix_{table}_doc_status', ['doc_status'])

    op.execute("""
        UPDATE invoice_head SET doc_status = 'completed',
            completed_dttm = COALESCE(
                (SELECT MAX(l.created_dttm) FROM invoice_status_log l
                 WHERE l.invoice_id = invoice_head.id AND l.service_status = 4),
                update_dttm)
        WHERE service_status = 4
    """)
    for table in ('item_invoice_head', 'purchase_order_head'):
        op.execute(f"UPDATE {table} SET doc_status = 'completed' WHERE completed_dttm IS NOT NULL")


def downgrade():
    for table, short in TABLES.items():
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f'ix_{table}_doc_status')
            batch.drop_constraint(f'ck_{short}_doc_status', type_='check')
            batch.drop_constraint(f'fk_{table}_voided_by', type_='foreignkey')
            batch.drop_constraint(f'fk_{table}_completed_by', type_='foreignkey')
            for column in ('void_reason', 'voided_by_id', 'voided_dttm', 'completed_by_id', 'doc_status'):
                batch.drop_column(column)
    with op.batch_alter_table('invoice_head') as batch:
        batch.drop_column('completed_dttm')
