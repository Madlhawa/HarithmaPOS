import logging

from flask_login import login_required
from flask import Blueprint, render_template, request, flash, redirect, url_for

from harithmapos import db, config
from harithmapos.billing import money, to_decimal
from harithmapos.models import Payment, InvoiceHead, ItemInvoiceHead, PurchaseOrderHead, Customer, Employee
from harithmapos.timeutils import utcnow
from harithmapos.views.ledger import apply_payment, record_document_payment
from harithmapos.views.payment.forms import PaymentCreateForm, PaymentUpdateForm, DocumentPaymentForm
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
    from harithmapos.models import Payslip, SalaryAdvance
    advance = SalaryAdvance.query.filter_by(payment_id=payment.id).first()
    if advance is not None and advance.is_recovered:
        flash("This is a salary advance that a payslip has already taken back. Reopen that month's payroll first.",
              category='danger')
        return utils.redirect_back('payment_blueprint.payment')
    try:
        apply_payment(payment, sign=-1)
        note = ''
        for slip in Payslip.query.filter_by(payment_id=payment.id).all():
            slip.payment_id = None
            note = ' The payslip is now unpaid again.'
        if advance is not None:
            db.session.delete(advance)
            note = ' The salary advance was removed too.'
        db.session.delete(payment)
        db.session.commit()
        flash("Payment deleted." + note, category='success')
    except Exception:
        db.session.rollback()
        logger.exception("Could not delete payment %s", payment_id)
        flash("The payment could not be deleted. Please try again.", category='danger')
    return utils.redirect_back('payment_blueprint.payment')


# ---------------------------------------------------------------------------
# Payments taken on a completed invoice or purchase order's own page
# ---------------------------------------------------------------------------

def _pay_document(document, link_field, here, label):
    """Record a later payment against a completed document, then go back to it."""
    form = DocumentPaymentForm()
    if not form.validate_on_submit():
        utils.flash_form_errors(form)
        return redirect(here)
    if not document.is_completed:
        flash(f"Complete {label} first. Until then, enter the amount paid on the bill.", category='warning')
        return redirect(here)

    balance = money(document.balance)
    amount = money(to_decimal(form.payment_amount.data))
    if balance <= 0:
        flash(f"Nothing is left to pay on {label}.", category='info')
        return redirect(here)
    if amount > balance:
        flash(f"That is more than the balance of {config.CURRENCY} {balance:,.2f}. "
              "Enter the balance or less.", category='warning')
        return redirect(here)

    try:
        record_document_payment(document, link_field, amount, form.payment_method.data, form.remarks.data)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Could not record a payment for %s %s", link_field, document.id)
        flash("The payment could not be recorded. Please try again.", category='danger')
        return redirect(here)

    left = money(document.balance)
    if left > 0:
        flash(f"Payment of {config.CURRENCY} {amount:,.2f} recorded. "
              f"Still to pay: {config.CURRENCY} {left:,.2f}.", category='success')
    else:
        flash(f"Payment of {config.CURRENCY} {amount:,.2f} recorded. {label[0].upper() + label[1:]} is now settled.",
              category='success')
    return redirect(here)


@payment_blueprint.route("/app/invoice/head/<int:invoice_head_id>/pay", methods=['POST'])
@login_required
def pay_invoice(invoice_head_id):
    invoice = InvoiceHead.query.get_or_404(invoice_head_id)
    here = url_for('invoice_blueprint.invoice_head_detail', invoice_head_id=invoice.id)
    return _pay_document(invoice, 'invoice_id', here, f"invoice #{invoice.id}")


@payment_blueprint.route("/app/item_invoice/head/<int:item_invoice_head_id>/pay", methods=['POST'])
@login_required
def pay_item_invoice(item_invoice_head_id):
    sale = ItemInvoiceHead.query.get_or_404(item_invoice_head_id)
    here = url_for('invoice_blueprint.item_invoice_head_detail', item_invoice_head_id=sale.id)
    return _pay_document(sale, 'item_invoice_id', here, f"item sale #{sale.id}")


@payment_blueprint.route("/app/purchase_order/head/<int:purchase_order_head_id>/pay", methods=['POST'])
@owner_required
def pay_purchase_order(purchase_order_head_id):
    order = PurchaseOrderHead.query.get_or_404(purchase_order_head_id)
    here = url_for('purchase_order_blueprint.purchase_order_head_detail', purchase_order_head_id=order.id)
    return _pay_document(order, 'purchase_order_id', here, f"purchase order #{order.id}")
