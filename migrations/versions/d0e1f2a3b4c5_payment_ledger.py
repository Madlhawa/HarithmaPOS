"""Payments become an append-only ledger; documents no longer store what was paid

* payment: types say what the money was for (customer payment, refund,
  supplier, wages, advance, expense, other income, owner withdrawal or
  deposit) and fix its direction; new columns for the cash handed over
  (tendered_amount), the entry a reversal cancels (reverses_id) and who
  recorded it (created_by_id); update_dttm goes, since entries never change.
  Checks keep amounts positive and directions in/out; on PostgreSQL a
  trigger refuses UPDATE and DELETE.
* invoice_head, item_invoice_head, purchase_order_head: paid_amount,
  remaining_amount, payment_method and last_payment_date are dropped. What a
  document has been paid is summed from its payments.

Checked on the live data before writing this: every document's stored paid
amount (less change) already equalled the sum of its payments.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-11-15
"""
from alembic import op
import sqlalchemy as sa


revision = 'd0e1f2a3b4c5'
down_revision = 'c9d0e1f2a3b4'
branch_labels = None
depends_on = None

HEADS = ('invoice_head', 'item_invoice_head', 'purchase_order_head')


def upgrade():
    bind = op.get_bind()

    op.execute("""
        UPDATE payment SET payment_type = CASE
            WHEN invoice_id IS NOT NULL OR item_invoice_id IS NOT NULL THEN
                CASE WHEN payment_direction = 'in' THEN 'sale' ELSE 'sale_refund' END
            WHEN purchase_order_id IS NOT NULL THEN
                CASE WHEN payment_direction = 'out' THEN 'supplier' ELSE 'supplier_refund' END
            WHEN payment_type = 'wage' THEN 'wage'
            WHEN payment_type = 'advance' THEN 'advance'
            WHEN payment_type = 'withdraw' THEN 'withdrawal'
            WHEN payment_direction = 'out' THEN 'expense'
            ELSE 'income' END
    """)
    op.execute("UPDATE payment SET payment_method = 'cash' WHERE payment_method IS NULL OR payment_method = 'credit'")
    op.execute("DELETE FROM payment WHERE payment_amount IS NULL OR payment_amount <= 0")

    with op.batch_alter_table('payment') as batch:
        batch.add_column(sa.Column('tendered_amount', sa.Numeric(10, 2), nullable=True))
        batch.add_column(sa.Column('reverses_id', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('created_by_id', sa.Integer(), nullable=True))
        batch.create_foreign_key('fk_payment_reverses', 'payment', ['reverses_id'], ['id'])
        batch.create_unique_constraint('uq_payment_reverses', ['reverses_id'])
        batch.create_foreign_key('fk_payment_created_by', 'user', ['created_by_id'], ['id'])
        batch.alter_column('payment_type', type_=sa.String(20), existing_type=sa.String(10), nullable=False)
        batch.alter_column('payment_direction', type_=sa.String(3), existing_type=sa.String(10), nullable=False)
        batch.alter_column('payment_method', existing_type=sa.String(10), nullable=False)
        batch.alter_column('payment_amount', existing_type=sa.Numeric(10, 2), nullable=False)
        batch.drop_column('update_dttm')
        batch.create_check_constraint('ck_payment_amount_positive', 'payment_amount > 0')
        batch.create_check_constraint('ck_payment_direction', "payment_direction IN ('in', 'out')")
        batch.create_check_constraint('ck_payment_tendered', 'tendered_amount IS NULL OR tendered_amount >= payment_amount')
        batch.create_index('ix_payment_invoice_id', ['invoice_id'])
        batch.create_index('ix_payment_item_invoice_id', ['item_invoice_id'])
        batch.create_index('ix_payment_purchase_order_id', ['purchase_order_id'])
        batch.create_index('ix_payment_created_dttm', ['created_dttm'])

    for table in HEADS:
        with op.batch_alter_table(table) as batch:
            for column in ('paid_amount', 'remaining_amount', 'payment_method', 'last_payment_date'):
                batch.drop_column(column)

    if bind.dialect.name == 'postgresql':
        op.execute("""
            CREATE FUNCTION payment_is_append_only() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'payments are a ledger: they cannot be changed or deleted, post a reversal instead';
            END
            $$ LANGUAGE plpgsql
        """)
        op.execute("""
            CREATE TRIGGER payment_append_only BEFORE UPDATE OR DELETE ON payment
            FOR EACH ROW EXECUTE FUNCTION payment_is_append_only()
        """)


def downgrade():
    raise NotImplementedError("The ledger change cannot be undone; restore the pre-deploy backup instead.")
