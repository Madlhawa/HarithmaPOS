"""Reports for owners: the sales dashboard."""
from flask import Blueprint, render_template, request

from harithmapos import reports, staff_reports, payroll
from harithmapos.models import Employee
from harithmapos.permissions import owner_required

reports_blueprint = Blueprint('reports_blueprint', __name__)


@reports_blueprint.route('/app/reports/sales', methods=['GET'])
@owner_required
def sales():
    period = reports.period_from_args(request.args.get('range'), request.args.get('from'), request.args.get('to'))
    data = reports.sales_report(period)
    return render_template('reports/sales.html', title='Sales', r=data, presets=reports.PRESETS)


@reports_blueprint.route('/app/reports/staff', methods=['GET'])
@owner_required
def staff():
    period = reports.period_from_args(request.args.get('range'), request.args.get('from'), request.args.get('to'))
    employee_id = request.args.get('employee', type=int)
    employees = Employee.query.order_by(Employee.active.desc(), Employee.name).all()
    if employee_id and not any(e.id == employee_id for e in employees):
        employee_id = None
    data = staff_reports.staff_report(period, employee_id)
    chosen = next((e for e in employees if e.id == employee_id), None)
    return render_template('reports/staff.html', title='Staff report', r=data, presets=reports.PRESETS,
                           employees=employees, chosen=chosen, fmt=payroll.fmt_minutes)
