import logging

from flask_login import login_required
from flask import Blueprint, render_template, request, flash

from harithmapos import db
from harithmapos.models import Payment, InvoiceHead, ItemInvoiceHead, PurchaseOrderHead, Customer, Employee
from harithmapos.timeutils import utcnow
from harithmapos.views.ledger import apply_payment
from harithmapos.views.payment.forms import PaymentCreateForm, PaymentUpdateForm
from harithmapos.permissions import owner_required, user_is_owner

import harithmapos.views.utils as utils
from utils.database import safe_insert_with_sequence_check

logger = logging.getLogger(__name__)

payment_blueprint = Blueprint('payment_blueprint', __name__)

PER_PAGE = 25

# form field -> (model it must exist in, name shown in the error message)
LINK_MODELS = {
    'invoice_id': (InvoiceHead, 'Service invoice'),
    'item_invoice_id': (ItemInvoiceHead, 'Item invoice'),
    'purchase_order_id': (PurchaseOrderHead, 'Purchase order'),
    'customer_id': (Customer, 'Customer'),
    'employee_id': (Employee, 'Employee'),
}


def _links_from_form(form):
    """Read the linked record ids from the form. Returns (links, error message)."""
    links = {}
    for field_name, (model, label) in LINK_MODELS.items():
        value = getattr(form, field_name).data
        if value is not None and db.session.get(model, value) is None:
            return None, f"{label} #{value} does not exist."
        links[field_name] = value
    return links, None


@payment_blueprint.route("/app/payment", methods=['GET'])
@login_required
def payment():
    page = request.args.get('page', 1, type=int)
    direction = request.args.get('direction', '')

    payments = Payment.query
    if not user_is_owner():
        # Counter staff see the money they took in, not wages, withdrawals or supplier payments.
        direction = 'in'
    if direction in ('in', 'out'):
        payments = payments.filter(Payment.payment_direction == direction)
    payments = payments.order_by(Payment.created_dttm.desc(), Payment.id.desc()).paginate(page=page, per_page=PER_PAGE)
    return render_template('payment.html', title='Payments', payments=payments, direction=direction)


@payment_blueprint.route("/app/payment/create", methods=['POST'])
@login_required
def insert_payment():
    form = PaymentCreateForm()
    if not form.validate_on_submit():
        utils.flash_form_errors(form)
        return utils.redirect_back('payment_blueprint.payment')

    if form.payment_direction.data != 'in' and not user_is_owner():
        flash("Only an owner can record money going out.", category='warning')
        return utils.redirect_back('payment_blueprint.payment')

    links, error = _links_from_form(form)
    if error:
        flash(error, category='danger')
        return utils.redirect_back('payment_blueprint.payment')

    try:
        payment = safe_insert_with_sequence_check(
            Payment,
            payment_method=form.payment_method.data,
            payment_direction=form.payment_direction.data,
            payment_amount=form.payment_amount.data,
            payment_type=form.payment_type.data,
            remarks=form.remarks.data,
            **links,
        )
        # Keep the linked invoice / purchase order's paid and balance figures in step.
        apply_payment(payment, sign=1)
        db.session.commit()
        flash("Payment recorded.", category='success')
    except Exception:
        db.session.rollback()
        logger.exception("Could not record payment")
        flash("The payment could not be recorded. Please try again.", category='danger')
    return utils.redirect_back('payment_blueprint.payment')


@payment_blueprint.route("/app/payment/<int:payment_id>/update", methods=['POST'])
@owner_required
def update_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    form = PaymentUpdateForm()
    if not form.validate_on_submit():
        utils.flash_form_errors(form)
        return utils.redirect_back('payment_blueprint.payment')

    links, error = _links_from_form(form)
    if error:
        flash(error, category='danger')
        return utils.redirect_back('payment_blueprint.payment')

    try:
        # Take the old payment out of its documents, change it, then put it back in.
        apply_payment(payment, sign=-1)
        for field_name, value in links.items():
            setattr(payment, field_name, value)
        payment.payment_method = form.payment_method.data
        payment.payment_direction = form.payment_direction.data
        payment.payment_amount = form.payment_amount.data
        payment.payment_type = form.payment_type.data
        payment.remarks = form.remarks.data
        payment.update_dttm = utcnow()
        apply_payment(payment, sign=1)
        db.session.commit()
        flash("Payment saved.", category='success')
    except Exception:
        db.session.rollback()
        logger.exception("Could not update payment %s", payment_id)
        flash("The payment could not be saved. Please try again.", category='danger')
    return utils.redirect_back('payment_blueprint.payment')


@payment_blueprint.route('/app/payment/<int:payment_id>/delete', methods=['POST'])
@owner_required
def delete_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    try:
        apply_payment(payment, sign=-1)
        db.session.delete(payment)
        db.session.commit()
        flash("Payment deleted.", category='success')
    except Exception:
        db.session.rollback()
        logger.exception("Could not delete payment %s", payment_id)
        flash("The payment could not be deleted. Please try again.", category='danger')
    return utils.redirect_back('payment_blueprint.payment')
