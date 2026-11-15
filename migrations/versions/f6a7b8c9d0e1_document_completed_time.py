"""When an item sale or purchase order was completed

Service invoices already know this from their status (Done). Item sales and
purchase orders did not record it, so a completed one could not be told apart
from one still being filled in. Payments on the document page need that.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-15
"""
from alembic import op
import sqlalchemy as sa


revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('item_invoice_head', schema=None) as batch_op:
        batch_op.add_column(sa.Column('completed_dttm', sa.DateTime(), nullable=True))
    with op.batch_alter_table('purchase_order_head', schema=None) as batch_op:
        batch_op.add_column(sa.Column('completed_dttm', sa.DateTime(), nullable=True))

    # Completing has always recorded a payment row, so documents that have one were completed.
    op.execute("""
        UPDATE item_invoice_head SET completed_dttm = update_dttm
        WHERE EXISTS (SELECT 1 FROM payment WHERE payment.item_invoice_id = item_invoice_head.id)
    """)
    op.execute("""
        UPDATE purchase_order_head SET completed_dttm = update_dttm
        WHERE EXISTS (SELECT 1 FROM payment WHERE payment.purchase_order_id = purchase_order_head.id)
    """)


def downgrade():
    with op.batch_alter_table('purchase_order_head', schema=None) as batch_op:
        batch_op.drop_column('completed_dttm')
    with op.batch_alter_table('item_invoice_head', schema=None) as batch_op:
        batch_op.drop_column('completed_dttm')
