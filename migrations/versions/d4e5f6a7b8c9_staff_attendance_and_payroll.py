"""Staff attendance, leave, salary advances and payroll

Revision ID: d4e5f6a7b8c9
Revises: c7d8e9f0a1b2
Create Date: 2026-11-12

Existing employees become monthly-paid, EPF on, active; their wage is
treated as the monthly salary. Change any of that on the Employees page.
"""
from alembic import op
import sqlalchemy as sa


revision = 'd4e5f6a7b8c9'
down_revision = 'c7d8e9f0a1b2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('employee', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pay_type', sa.String(length=10), nullable=False, server_default='monthly'))
        batch_op.add_column(sa.Column('epf_enabled', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column('epf_number', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()))

    op.create_table(
        'attendance_day',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('work_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('leave_type', sa.String(length=10), nullable=True),
        sa.Column('time_in', sa.Time(), nullable=True),
        sa.Column('time_out', sa.Time(), nullable=True),
        sa.Column('late_minutes', sa.Integer(), nullable=False),
        sa.Column('early_minutes', sa.Integer(), nullable=False),
        sa.Column('overtime_minutes', sa.Integer(), nullable=False),
        sa.Column('note', sa.String(length=255), nullable=True),
        sa.Column('updated_by_id', sa.Integer(), nullable=True),
        sa.Column('create_dttm', sa.DateTime(), nullable=False),
        sa.Column('update_dttm', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employee.id']),
        sa.ForeignKeyConstraint(['updated_by_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'work_date', name='uq_attendance_employee_date'),
    )
    op.create_index('ix_attendance_day_employee_id', 'attendance_day', ['employee_id'])
    op.create_index('ix_attendance_day_work_date', 'attendance_day', ['work_date'])

    op.create_table(
        'short_leave',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('work_date', sa.Date(), nullable=False),
        sa.Column('time_from', sa.Time(), nullable=False),
        sa.Column('time_to', sa.Time(), nullable=False),
        sa.Column('minutes', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('create_dttm', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employee.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_short_leave_employee_id', 'short_leave', ['employee_id'])
    op.create_index('ix_short_leave_work_date', 'short_leave', ['work_date'])

    op.create_table(
        'payroll_run',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('month', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('finalised_by_id', sa.Integer(), nullable=True),
        sa.Column('create_dttm', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['finalised_by_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('month'),
    )

    money = lambda name: sa.Column(name, sa.Numeric(precision=10, scale=2), nullable=False)
    op.create_table(
        'payslip',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payroll_run_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('pay_type', sa.String(length=10), nullable=False),
        money('rate'),
        sa.Column('days_in_month', sa.Integer(), nullable=False),
        sa.Column('days_present', sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column('paid_leave_days', sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column('nopay_days', sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column('unmarked_days', sa.Integer(), nullable=False),
        sa.Column('late_count', sa.Integer(), nullable=False),
        sa.Column('late_minutes', sa.Integer(), nullable=False),
        sa.Column('short_leave_count', sa.Integer(), nullable=False),
        sa.Column('short_leave_minutes', sa.Integer(), nullable=False),
        sa.Column('overtime_minutes', sa.Integer(), nullable=False),
        money('basic_pay'), money('nopay_deduction'), money('overtime_pay'), money('allowances'),
        money('gross_pay'), money('epf_employee'), money('advances'), money('other_deductions'),
        money('net_pay'), money('epf_employer'), money('etf_employer'),
        sa.Column('note', sa.String(length=255), nullable=True),
        sa.Column('payment_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['employee.id']),
        sa.ForeignKeyConstraint(['payment_id'], ['payment.id']),
        sa.ForeignKeyConstraint(['payroll_run_id'], ['payroll_run.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('payroll_run_id', 'employee_id', name='uq_payslip_run_employee'),
    )
    op.create_index('ix_payslip_employee_id', 'payslip', ['employee_id'])
    op.create_index('ix_payslip_payroll_run_id', 'payslip', ['payroll_run_id'])

    op.create_table(
        'salary_advance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('advance_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('note', sa.String(length=255), nullable=True),
        sa.Column('payment_id', sa.Integer(), nullable=True),
        sa.Column('payslip_id', sa.Integer(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('create_dttm', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['user.id']),
        sa.ForeignKeyConstraint(['employee_id'], ['employee.id']),
        sa.ForeignKeyConstraint(['payment_id'], ['payment.id']),
        sa.ForeignKeyConstraint(['payslip_id'], ['payslip.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_salary_advance_employee_id', 'salary_advance', ['employee_id'])


def downgrade():
    op.drop_index('ix_salary_advance_employee_id', table_name='salary_advance')
    op.drop_table('salary_advance')
    op.drop_index('ix_payslip_payroll_run_id', table_name='payslip')
    op.drop_index('ix_payslip_employee_id', table_name='payslip')
    op.drop_table('payslip')
    op.drop_table('payroll_run')
    op.drop_index('ix_short_leave_work_date', table_name='short_leave')
    op.drop_index('ix_short_leave_employee_id', table_name='short_leave')
    op.drop_table('short_leave')
    op.drop_index('ix_attendance_day_work_date', table_name='attendance_day')
    op.drop_index('ix_attendance_day_employee_id', table_name='attendance_day')
    op.drop_table('attendance_day')
    with op.batch_alter_table('employee', schema=None) as batch_op:
        batch_op.drop_column('active')
        batch_op.drop_column('epf_number')
        batch_op.drop_column('epf_enabled')
        batch_op.drop_column('pay_type')
