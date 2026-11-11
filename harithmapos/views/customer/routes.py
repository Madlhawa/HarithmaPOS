import logging

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required

from harithmapos import db
from harithmapos.models import Customer, InvoiceHead, ItemInvoiceHead, Payment, Vehicle
from harithmapos.textutils import normalize_phone
from harithmapos.timeutils import utcnow
from harithmapos.views.customer.forms import CustomerForm, QuickRegisterForm
from harithmapos.permissions import owner_required

import harithmapos.views.utils as utils
from utils.database import safe_insert_with_sequence_check

logger = logging.getLogger(__name__)

customer_blueprint = Blueprint('customer_blueprint', __name__)

PER_PAGE = 25
GENERAL_CUSTOMER_ID = -1


@customer_blueprint.route('/app/customer/', methods=['GET'])
@login_required
def customer():
    page = request.args.get('page', 1, type=int)
    query = (request.args.get('query') or '').strip()

    customers = Customer.query
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
    return render_template('customer.html', title='Customers', customers=customers, query=query)


@customer_blueprint.route('/app/insert_customer/', methods=['POST'])
@login_required
def insert_customer():
    form = CustomerForm()
    if form.validate_on_submit():
        try:
            safe_insert_with_sequence_check(
                Customer,
                name=form.name.data,
                contact=form.contact.data,
                address=form.address.data,
                email=form.email.data
            )
            flash(f"{form.name.data} added.", category='success')
        except Exception:
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
    existing = Vehicle.query.filter(func.upper(Vehicle.number) == number).first()
    if existing:
        flash(f"{existing.number} is already registered to {existing.owner.name}.", category='info')
        return redirect(url_for('dashboard_blueprint.dashboard', new_service_vehicle=existing.id))

    try:
        customer = None
        if form.contact.data:
            # Same phone and same name: this person is already a customer.
            customer = Customer.query.filter(
                Customer.contact == form.contact.data,
                func.lower(Customer.name) == form.name.data.lower(),
            ).first()
        if customer is None:
            customer = safe_insert_with_sequence_check(
                Customer, name=form.name.data, contact=form.contact.data)
        vehicle = safe_insert_with_sequence_check(
            Vehicle,
            number=number,
            make=form.make.data,
            model=form.model.data,
            year=str(form.year.data) if form.year.data else None,
            owner_id=customer.id,
        )
    except Exception:
        logger.exception("Could not register customer and vehicle")
        flash("The customer and vehicle could not be saved. Please try again.", category='danger')
        return redirect(url_for('dashboard_blueprint.dashboard'))

    flash(f"{vehicle.number} registered for {customer.name}.", category='success')
    return redirect(url_for('dashboard_blueprint.dashboard', new_service_vehicle=vehicle.id))


@customer_blueprint.route('/app/customer/<int:customer_id>/update', methods=['POST'])
@login_required
def update_customer(customer_id):
    customer = db.session.get(Customer, customer_id) or abort(404)
    form = CustomerForm()
    if form.validate_on_submit():
        try:
            customer.name = form.name.data
            customer.contact = form.contact.data
            customer.address = form.address.data
            customer.email = form.email.data
            customer.update_dttm = utcnow()
            db.session.commit()
            flash(f"{customer.name} saved.", category='success')
        except Exception:
            db.session.rollback()
            logger.exception("Could not update customer %s", customer_id)
            flash("The customer could not be saved. Please try again.", category='danger')
    else:
        utils.flash_form_errors(form)
    return utils.redirect_back('customer_blueprint.customer')


@customer_blueprint.route('/app/delete_customer/<int:customer_id>', methods=['POST'])
@owner_required
def delete_customer(customer_id):
    customer = db.session.get(Customer, customer_id) or abort(404)
    if customer.id == GENERAL_CUSTOMER_ID:
        flash("The General Customer is used for walk-in sales and can't be deleted.", category='warning')
        return utils.redirect_back('customer_blueprint.customer')

    blockers = [
        (InvoiceHead.query.filter(InvoiceHead.customer_id == customer.id).count(), 'service invoices'),
        (ItemInvoiceHead.query.filter(ItemInvoiceHead.customer_id == customer.id).count(), 'item invoices'),
        (Payment.query.filter(Payment.customer_id == customer.id).count(), 'payments'),
    ]
    in_use = [description for count, description in blockers if count]
    if in_use:
        flash(f"{customer.name} can't be deleted because they have {', '.join(in_use)}.", category='warning')
        return utils.redirect_back('customer_blueprint.customer')

    name = customer.name
    try:
        for vehicle in list(customer.vehicles):
            db.session.delete(vehicle)
        db.session.delete(customer)
        db.session.commit()
        flash(f"{name} deleted.", category='success')
    except IntegrityError:
        db.session.rollback()
        flash(f"{name} can't be deleted because one of their vehicles has invoices.", category='warning')
    return utils.redirect_back('customer_blueprint.customer')
