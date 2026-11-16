"""Stock movement history

Every change to an item's stock is written down as a stock_movement row
(what moved, why, which document, who, and the balance after). Each stock
item starts with one opening movement holding its stock today, so its
quantity is the sum of its movements from the start.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-16
"""
from alembic import op
import sqlalchemy as sa



revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'stock_movement',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('item.id', ondelete='CASCADE'), nullable=False),
        sa.Column('change', sa.Numeric(10, 4), nullable=False),
        sa.Column('quantity_after', sa.Numeric(10, 4), nullable=False),
        sa.Column('kind', sa.String(20), nullable=False),
        sa.Column('doc_type', sa.String(20)),
        sa.Column('doc_id', sa.Integer()),
        sa.Column('note', sa.String(200)),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id')),
        sa.Column('created_dttm', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('opening', 'count', 'sale', 'sale_undo', 'purchase', 'purchase_undo', 'void')",
                           name='ck_stock_movement_kind'),
        sa.CheckConstraint("doc_type IS NULL OR doc_type IN ('invoice', 'item_sale', 'purchase_order')",
                           name='ck_stock_movement_doc_type'),
    )
    op.create_index('ix_stock_movement_item_time', 'stock_movement', ['item_id', 'id'])
    op.execute("""
        INSERT INTO stock_movement (item_id, change, quantity_after, kind, note, created_dttm)
        SELECT id, quantity, quantity, 'opening', 'Stock when the history started', CURRENT_TIMESTAMP
        FROM item WHERE quantity IS NOT NULL AND quantity <> 0 ORDER BY id
    """)


def downgrade():
    op.drop_index('ix_stock_movement_item_time', table_name='stock_movement')
    op.drop_table('stock_movement')
