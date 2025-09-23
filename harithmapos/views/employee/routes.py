from flask_login import login_required
from flask import Blueprint, render_template, request, redirect, url_for, flash

from harithmapos import db
from harithmapos.models import Employee
from harithmapos.views.employee.forms import EmployeeCreateForm, EmployeeUpdateForm

employee_blueprint = Blueprint('employee_blueprint', __name__)

@employee_blueprint.route("/app/employee", methods=['GET', 'POST'])
@login_required
def employee():
    employee_create_form = EmployeeCreateForm()
    employee_update_form = EmployeeUpdateForm()

    per_page = 10
    page = request.args.get('page',1,type=int)
    query = request.args.get("query",None)

    if query:
        employees = Employee.query.order_by(Employee.update_dttm.desc()).filter(Employee.name.icontains(query)).paginate(page=page, per_page=per_page)
    else:
        employees = Employee.query.order_by(Employee.update_dttm.desc()).paginate(page=page, per_page=per_page)
    return render_template(
        'employee.html', 
        title='Employee', 
        employee_create_form=employee_create_form, 
        employee_update_form=employee_update_form,
        employees=employees,
        query=query
    )

@employee_blueprint.route("/app/employee/create", methods=['GET', 'POST'])
@login_required
def insert_employee():
    employee_create_form = EmployeeCreateForm()
    if employee_create_form.validate_on_submit():
        try:
            from utils.database import safe_insert_with_sequence_check
            employee = safe_insert_with_sequence_check(
                Employee,
                name=employee_create_form.name.data,
                contact=employee_create_form.contact.data,
                address=employee_create_form.address.data,
                designation=employee_create_form.designation.data,
                joined_date=employee_create_form.joined_date.data,
                wage=employee_create_form.wage.data
            )
            flash("Employee added successfully!", category='success')
        except Exception as e:
            flash(f"Employee failed to add: {str(e)}", category='danger')
    else:
        flash("Employee failed to add - form validation failed!", category='danger')
    return redirect(url_for('employee_blueprint.employee'))

@employee_blueprint.route("/app/employee/<int:employee_id>/update", methods=['GET', 'POST'])
@login_required
def update_employee(employee_id):
    employee_update_form = EmployeeUpdateForm()
    if employee_update_form.validate_on_submit():
        employee = Employee.query.get_or_404(employee_id)
        employee.name = employee_update_form.name.data
        employee.contact = employee_update_form.contact.data
        employee.address = employee_update_form.address.data
        employee.designation = employee_update_form.designation.data
        employee.joined_date = employee_update_form.joined_date.data
        employee.wage = employee_update_form.wage.data
        db.session.commit()
        flash("Employee is updated!", category='success')
    else:
        flash("Employee failed to add!", category='danger')
    return redirect(url_for('employee_blueprint.employee'))

@employee_blueprint.route('/app/employee/<int:employee_id>/delete', methods = ['GET', 'POST'])
@login_required
def delete_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    db.session.delete(employee)
    db.session.commit()
    flash("Employee is deleted!", category='success')
    return redirect(url_for('employee_blueprint.employee'))
