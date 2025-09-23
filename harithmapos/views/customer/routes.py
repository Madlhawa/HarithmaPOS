from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from harithmapos import db
from harithmapos.models import Customer
from harithmapos.views.vehicle.forms import VehicleForm
from harithmapos.views.customer.forms import CustomerForm

from utils.database import safe_insert_with_sequence_check

customer_blueprint = Blueprint('customer_blueprint', __name__)

@customer_blueprint.route('/app/customer/', methods = ['GET', 'POST'])
@login_required
def customer():
    customer_form = CustomerForm()
    vehicle_form = VehicleForm()
    if request.method == 'POST' and 'query' in request.form:
        query = request.form["query"]
        customers = Customer.query.filter(Customer.name.icontains(query)).all()
        return render_template('customer.html', title='Customers', customer_form=customer_form, vehicle_form=vehicle_form, customers=customers, query=query)
    else:
        customers = Customer.query.all()
        return render_template('customer.html', title='Customers', customer_form=customer_form, vehicle_form=vehicle_form, customers=customers)

@customer_blueprint.route('/app/insert_customer/', methods = ['POST'])
@login_required
def insert_customer():
    form = CustomerForm()
    if form.validate_on_submit():
        try:
            customer = safe_insert_with_sequence_check(
                Customer,
                name=form.name.data,
                contact=form.contact.data,
                address=form.address.data,
                email=form.email.data
            )
            flash("Customer added successfully.", category='success')
        except Exception as e:
            flash(f"Customer failed to add: {str(e)}", category='danger')
    else:
        flash("Customer failed to add - form validation failed.", category='danger')
    return redirect(url_for('customer_blueprint.customer'))

@customer_blueprint.route('/app/update_customer/', methods = ['POST'])
@login_required
def update_customer():
    form = CustomerForm()
    print(f"{request.form.get('id') = }")
    if form.validate_on_submit():
        customer = db.session.get(Customer, request.form.get('id'))
        customer.name = form.name.data
        customer.contact = form.contact.data
        customer.address = form.address.data
        customer.email = form.email.data
        db.session.commit()
        flash("Customer updated successfully.", category='success')
    else:
        flash("Customer failed to update", category='danger')
    return redirect(url_for('customer_blueprint.customer'))
 
@customer_blueprint.route('/app/delete_customer/<int:customer_id>', methods = ['GET', 'POST'])
@login_required
def delete_customer(customer_id):
    customer = db.session.get(Customer, customer_id)
    db.session.delete(customer)
    db.session.commit()
    flash("Customer is deleted!", category="success")
    return redirect(url_for('customer_blueprint.customer'))
