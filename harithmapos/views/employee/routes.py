import logging

from flask import Blueprint, render_template, request, flash

from harithmapos import db, config, payroll
from harithmapos.models import Employee, InvoiceHead, Payment, AttendanceDay, ShortLeave, SalaryAdvance, Payslip
from harithmapos.timeutils import utcnow
from harithmapos.views.employee.forms import EmployeeCreateForm, EmployeeUpdateForm
from harithmapos.permissions import owner_required

import harithmapos.views.utils as utils
from utils.database import safe_insert_with_sequence_check

logger = logging.getLogger(__name__)

employee_blueprint = Blueprint('employee_blueprint', __name__)

PER_PAGE = 25


@employee_blueprint.route("/app/employee", methods=['GET'])
@owner_required
def employee():
    page = request.args.get('page', 1, type=int)
    query = (request.args.get('query') or '').strip()

    show = request.args.get('show', 'active')
    employees = Employee.query
    if show != 'all':
        employees = employees.filter(Employee.active.is_(True))
    if query:
        employees = employees.filter(Employee.name.ilike(f"%{query}%"))
    employees = employees.order_by(Employee.name).paginate(page=page, per_page=PER_PAGE)
    return render_template('employee.html', title='Employees', employees=employees, query=query, show=show,
                           pay_labels=dict(config.PAY_TYPE_FORM_LIST), pay_types=config.PAY_TYPE_FORM_LIST)


@employee_blueprint.route("/app/employee/create", methods=['POST'])
@owner_required
def insert_employee():
    form = EmployeeCreateForm()
    if form.validate_on_submit():
        try:
            safe_insert_with_sequence_check(
                Employee,
                name=form.name.data,
                contact=form.contact.data,
                address=form.address.data,
                designation=form.designation.data,
                joined_date=form.joined_date.data,
                wage=form.wage.data,
                pay_type=form.pay_type.data,
                epf_enabled=form.epf_enabled.data,
                epf_number=form.epf_number.data or None,
                active=form.active.data,
            )
            flash(f"{form.name.data} added.", category='success')
        except Exception:
            logger.exception("Could not add employee")
            flash("The employee could not be added. Please try again.", category='danger')
    else:
        utils.flash_form_errors(form)
    return utils.redirect_back('employee_blueprint.employee')


@employee_blueprint.route("/app/employee/<int:employee_id>/update", methods=['POST'])
@owner_required
def update_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    form = EmployeeUpdateForm()
    if form.validate_on_submit():
        try:
            employee.name = form.name.data
            employee.contact = form.contact.data
            employee.address = form.address.data
            employee.designation = form.designation.data
            employee.joined_date = form.joined_date.data
            employee.wage = form.wage.data
            employee.pay_type = form.pay_type.data
            employee.epf_enabled = form.epf_enabled.data
            employee.epf_number = form.epf_number.data or None
            employee.active = form.active.data
            employee.update_dttm = utcnow()
            db.session.commit()
            flash(f"{employee.name} saved.", category='success')
        except Exception:
            db.session.rollback()
            logger.exception("Could not update employee %s", employee_id)
            flash("The employee could not be saved. Please try again.", category='danger')
    else:
        utils.flash_form_errors(form)
    return utils.redirect_back('employee_blueprint.employee')


@employee_blueprint.route('/app/employee/<int:employee_id>/delete', methods=['POST'])
@owner_required
def delete_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    utils.delete_record(employee, employee.name, blockers=[
        (InvoiceHead.query.filter(InvoiceHead.employee_id == employee.id).count(), 'service invoices'),
        (Payment.query.filter(Payment.employee_id == employee.id).count(), 'payments'),
        (AttendanceDay.query.filter(AttendanceDay.employee_id == employee.id).count(), 'attendance days'),
        (Payslip.query.filter(Payslip.employee_id == employee.id).count(), 'payslips'),
        (SalaryAdvance.query.filter(SalaryAdvance.employee_id == employee.id).count(), 'salary advances'),
    ])
    return utils.redirect_back('employee_blueprint.employee')


@employee_blueprint.route("/app/employee/<int:employee_id>", methods=['GET'])
@owner_required
def employee_detail(employee_id):
    from datetime import date
    from harithmapos.timeutils import local_today
    employee = db.get_or_404(Employee, employee_id)
    today = local_today(config.APP_TIMEZONE)
    year_start = date(today.year, 1, 1)
    year_days = AttendanceDay.query.filter(AttendanceDay.employee_id == employee.id,
                                           AttendanceDay.work_date.between(year_start, today)).all()
    taken = payroll.leave_taken(year_days)
    rules = payroll.Rules.from_settings()
    balances = [
        ('Annual', rules.annual_days, taken.get(config.LEAVE_ANNUAL, 0)),
        ('Casual', rules.casual_days, taken.get(config.LEAVE_CASUAL, 0)),
        ('Sick', None, taken.get(config.LEAVE_SICK, 0)),
        ('No-pay', None, taken.get(config.LEAVE_NOPAY, 0)),
    ]
    month = today.replace(day=1)
    first, last = payroll.month_bounds(month)
    month_days = [d for d in year_days if d.work_date >= first]
    month_leaves = ShortLeave.query.filter(ShortLeave.employee_id == employee.id,
                                           ShortLeave.work_date.between(first, last)).all()
    summary = payroll.summarise_month(month_days, month_leaves, month, today)
    recent = (AttendanceDay.query.filter(AttendanceDay.employee_id == employee.id)
              .order_by(AttendanceDay.work_date.desc()).limit(14).all())
    advances = (SalaryAdvance.query.filter_by(employee_id=employee.id)
                .order_by(SalaryAdvance.advance_date.desc()).limit(20).all())
    open_total = sum((a.amount for a in advances if not a.is_recovered), 0)
    slips = employee.payslips.join(Payslip.run).order_by(Payslip.id.desc()).limit(12).all()
    return render_template('employee_detail.html', title=employee.name, e=employee, balances=balances,
                           summary=summary, recent=recent, advances=advances, open_total=open_total, slips=slips,
                           today=today, fmt=payroll.fmt_minutes, pay_labels=dict(config.PAY_TYPE_FORM_LIST),
                           status_labels=dict(config.ATTENDANCE_STATUSES), leave_labels=dict(config.LEAVE_TYPES),
                           methods=[m for m in config.PAYMENT_METHOD_FORM_LIST if m[0] != 'credit'])
