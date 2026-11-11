import logging

from flask import Blueprint, render_template, request, flash

from harithmapos import db
from harithmapos.models import Employee, InvoiceHead, Payment
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

    employees = Employee.query
    if query:
        employees = employees.filter(Employee.name.ilike(f"%{query}%"))
    employees = employees.order_by(Employee.name).paginate(page=page, per_page=PER_PAGE)
    return render_template('employee.html', title='Employees', employees=employees, query=query)


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
                wage=form.wage.data
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
    ])
    return utils.redirect_back('employee_blueprint.employee')
