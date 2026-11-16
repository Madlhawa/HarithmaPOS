"""A service invoice can wait in the queue without a bay or an employee

invoice_head.washbay_id and employee_id may be empty. The app asks for them
when the job moves into a work stage (job_status.py). The downgrade refuses
while any invoice still has them empty.

Revision ID: 9c0d1e2f3a4b
Revises: 8b9c0d1e2f3a
Create Date: 2026-11-16
"""
from alembic import op
import sqlalchemy as sa


revision = '9c0d1e2f3a4b'
down_revision = '8b9c0d1e2f3a'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('invoice_head', 'washbay_id', existing_type=sa.Integer(), nullable=True)
    op.alter_column('invoice_head', 'employee_id', existing_type=sa.Integer(), nullable=True)


def downgrade():
    empty = op.get_bind().exec_driver_sql(
        "SELECT count(*) FROM invoice_head WHERE washbay_id IS NULL OR employee_id IS NULL").scalar()
    if empty:
        raise RuntimeError(f"{empty} service invoice(s) have no bay or employee. Assign them first.")
    op.alter_column('invoice_head', 'washbay_id', existing_type=sa.Integer(), nullable=False)
    op.alter_column('invoice_head', 'employee_id', existing_type=sa.Integer(), nullable=False)
