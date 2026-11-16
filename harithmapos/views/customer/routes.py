import logging

from sqlalchemy import func, or_
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required

from harithmapos import db
from harithmapos.models import Customer, Vehicle
from harithmapos.textutils import normalize_phone
from harithmapos.timeutils import utcnow
from harithmapos.views.customer.forms import CustomerForm, QuickRegisterForm
from harithmapos.permissions import owner_required

import harithmapos.views.utils as utils

logger = logging.getLogger(__name__)

customer_blueprint = Blueprint('customer_blueprint', __name__)

PER_PAGE = 25
GENERAL_CUSTOMER_ID = -1


@customer_blueprint.route('/app/customer/', methods=['GET'])
@login_required
def customer():
    page = request.args.get('page', 1, type=int)
    query = (request.args.get('query') or '').strip()
    show = 'archived' if request.args.get('show') == 'archived' else ''

    customers = Customer.query.filter(Customer.is_archived if show else ~Customer.is_archived)
    if query:
        pattern = f"%{query}%"
        conditions = [
            Customer.name.ilike(pattern),
            Customer.contact.ilike(pattern),
            Customer.email.ilike(pattern),
            Customer.vehicles.any(Vehicle.number.ilike(pattern)),
        ]
        # "0771234567" should find the stored "771234567".
        phone = normalize_phone(query)
        if phone and phone != query:
            conditions.append(Customer.contact.ilike(f"%{phone}%"))
        customers = customers.filter(or_(*conditions))

    customers = customers.order_by(Customer.name).paginate(page=page, per_page=PER_PAGE)
    return render_template('customer.html', title='Customers', customers=customers, query=query, show=show)


@customer_blueprint.route('/app/insert_customer/', methods=['POST'])
@login_required
def insert_customer():
    form = CustomerForm()
    if form.validate_on_submit():
        try:
            customer = Customer(
                name=form.name.data,
                contact=form.contact.data,
                address=form.address.data,
                email=form.email.data,
            )
            db.session.add(customer)
            db.session.commit()
            flash(f"{form.name.data} added.", category='success')
            utils.warn_shared_phone(customer)
        except Exception:
            db.session.rollback()
            logger.exception("Could not add customer")
            flash("The customer could not be added. Please try again.", category='danger')
    else:
        utils.flash_form_errors(form)
    return utils.redirect_back('customer_blueprint.customer')


@customer_blueprint.route('/app/customer/quick', methods=['POST'])
@login_required
def quick_register():
    """Front-counter shortcut: add a customer and their vehicle together, then start the service."""
    form = QuickRegisterForm()
    if not form.validate_on_submit():
        utils.flash_form_errors(form)
        return redirect(url_for('dashboard_blueprint.dashboard'))

    number = form.number.data
    existing = Vehicle.with_plate(number)
    if existing:
        flash(utils.plate_taken_message(existing), category='info')
        return redirect(url_for('dashboard_blueprint.dashboard', new_service_vehicle=existing.id))

    new_customer = None
    try:
        customer = None
        if form.contact.data:
            # Same phone and same name: this person is already a customer.
            customer = Customer.query.filter(
                Customer.contact == form.contact.data,
                func.lower(Customer.name) == form.name.data.lower(),
            ).first()
        if customer is None:
            customer = new_customer = Customer(name=form.name.data, contact=form.contact.data)
            db.session.add(customer)
            db.session.flush()
        vehicle = Vehicle(
            number=number,
            make=form.make.data,
            model=form.model.data,
            year=str(form.year.data) if form.year.data else None,
            owner_id=customer.id,
        )
        db.session.add(vehicle)
        db.session.commit()   # customer and vehicle together, or neither
    except Exception:
        db.session.rollback()
        logger.exception("Could not register customer and vehicle")
        flash("The customer and vehicle could not be saved. Please try again.", category='danger')
        return redirect(url_for('dashboard_blueprint.dashboard'))

    flash(f"{vehicle.number} registered for {customer.name}.", category='success')
    if new_customer is not None:
        utils.warn_shared_phone(new_customer)
    return redirect(url_for('dashboard_blueprint.dashboard', new_service_vehicle=vehicle.id))


@customer_blueprint.route('/app/customer/<int:customer_id>/update', methods=['POST'])
@login_required
def update_customer(customer_id):
    customer = db.session.get(Customer, customer_id) or abort(404)
    form = CustomerForm()
    if form.validate_on_submit():
        try:
            phone_changed = customer.contact != form.contact.data
            customer.name = form.name.data
            customer.contact = form.contact.data
            customer.address = form.address.data
            customer.email = form.email.data
            customer.update_dttm = utcnow()
            db.session.commit()
            flash(f"{customer.name} saved.", category='success')
            if phone_changed:
                utils.warn_shared_phone(customer)
        except Exception:
            db.session.rollback()
            logger.exception("Could not update customer %s", customer_id)
            flash("The customer could not be saved. Please try again.", category='danger')
    else:
        utils.flash_form_errors(form)
    return utils.redirect_back('customer_blueprint.customer')


@customer_blueprint.route('/app/customer/<int:customer_id>/archive', methods=['POST'])
@owner_required
def archive_customer(customer_id):
    customer = db.session.get(Customer, customer_id) or abort(404)
    utils.archive_record(customer, customer.name)
    return utils.redirect_back('customer_blueprint.customer')


@customer_blueprint.route('/app/customer/<int:customer_id>/restore', methods=['POST'])
@owner_required
def restore_customer(customer_id):
    customer = db.session.get(Customer, customer_id) or abort(404)
    utils.restore_record(customer, customer.name)
    return utils.redirect_back('customer_blueprint.customer')
