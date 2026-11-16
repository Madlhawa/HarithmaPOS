"""One vehicle per plate

Adds vehicle.plate_key, the plate with only its letters and digits
(CAB-1234 and CAB 1234 are both CAB1234), and a unique constraint on it.
Refuses to run if two vehicles already share a plate, listing them, so
they can be merged first.

Revision ID: 8b9c0d1e2f3a
Revises: 7a8b9c0d1e2f
Create Date: 2026-11-16
"""
from alembic import op
import sqlalchemy as sa


revision = '8b9c0d1e2f3a'
down_revision = '7a8b9c0d1e2f'
branch_labels = None
depends_on = None

KEY = "upper(regexp_replace(number, '[^A-Za-z0-9]', '', 'g'))"


def upgrade():
    bind = op.get_bind()
    clashes = bind.exec_driver_sql(f"""
        SELECT string_agg(number || ' (vehicle ' || id || ')', ', ' ORDER BY id)
        FROM vehicle GROUP BY {KEY} HAVING count(*) > 1
    """).fetchall()
    if clashes:
        raise RuntimeError("These vehicles share a plate: " + "; ".join(row[0] for row in clashes)
                           + ". Move their invoices to one of them and remove the others, then upgrade again.")
    op.add_column('vehicle', sa.Column('plate_key', sa.String(8), nullable=True))
    op.execute(f"UPDATE vehicle SET plate_key = {KEY}")
    op.alter_column('vehicle', 'plate_key', existing_type=sa.String(8), nullable=False)
    op.create_unique_constraint('uq_vehicle_plate_key', 'vehicle', ['plate_key'])


def downgrade():
    op.drop_constraint('uq_vehicle_plate_key', 'vehicle', type_='unique')
    op.drop_column('vehicle', 'plate_key')
