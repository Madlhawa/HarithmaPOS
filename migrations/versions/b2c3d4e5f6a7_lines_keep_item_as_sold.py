"""Invoice and order lines keep the item's name and prices as sold

Lines used to show the item's current name, and +/- on a draft repriced the
line at the item's current price. Each line now stores the name, unit cost,
unit price and (for sales) the automatic discount it was added with.

Existing lines are filled from what they already hold: the unit amounts are
the line's totals divided by its quantity, the name and discount are the
item's as they are now.

Revision ID: b2c3d4e5f6a7
Revises: a1c2e3f4b5d6
Create Date: 2026-11-16
"""
from alembic import op
import sqlalchemy as sa


revision = 'b2c3d4e5f6a7'
down_revision = 'a1c2e3f4b5d6'
branch_labels = None
depends_on = None

SALE_LINES = ('invoice_detail', 'item_invoice_detail')
ALL_LINES = SALE_LINES + ('purchase_order_detail',)


def upgrade():
    for table in ALL_LINES:
        op.add_column(table, sa.Column('item_name', sa.String(100), nullable=True))
        op.add_column(table, sa.Column('unit_cost', sa.Numeric(10, 2), nullable=True))
        op.add_column(table, sa.Column('unit_price', sa.Numeric(10, 2), nullable=True))
        op.execute(f"""
            UPDATE {table} AS l SET
                item_name = i.name,
                unit_cost = CASE WHEN l.quantity <> 0 THEN round(l.total_cost / l.quantity, 2) ELSE coalesce(i.unit_cost, 0) END,
                unit_price = CASE WHEN l.quantity <> 0 THEN round(l.total_price / l.quantity, 2) ELSE coalesce(i.unit_price, 0) END
            FROM item AS i WHERE i.id = l.item_id
        """)
        with op.batch_alter_table(table) as batch:
            batch.alter_column('item_name', existing_type=sa.String(100), nullable=False)
            batch.alter_column('unit_cost', existing_type=sa.Numeric(10, 2), nullable=False)
            batch.alter_column('unit_price', existing_type=sa.Numeric(10, 2), nullable=False)
    for table in SALE_LINES:
        op.add_column(table, sa.Column('discount_pct', sa.Numeric(5, 2), nullable=False, server_default='0'))
        op.execute(f"""
            UPDATE {table} AS l SET discount_pct = coalesce(i.discount_pct, 0)
            FROM item AS i WHERE i.id = l.item_id
        """)


def downgrade():
    for table in SALE_LINES:
        op.drop_column(table, 'discount_pct')
    for table in ALL_LINES:
        op.drop_column(table, 'unit_price')
        op.drop_column(table, 'unit_cost')
        op.drop_column(table, 'item_name')
