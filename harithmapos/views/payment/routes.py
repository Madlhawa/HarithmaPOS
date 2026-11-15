"""The Payments page (the money ledger) and payments taken on an invoice or purchase order.

Entries are only ever added: by completing or paying a document, by payroll,
or by hand here for expenses, other income and the owner's own money. A
mistake is put right by reversing the entry (owners only), never by editing
or deleting it. See harithmapos/ledger.py.
"""
import logging

from flask_login import current_user, login_required
from flask import Blueprint, render_template, request, flash, redirect, url_for

from harithmapos import db, config, ledger
from harithmapos.billing import money, to_decimal
from harithmapos.models import Payment, Payslip, InvoiceHead, ItemInvoiceHead, PurchaseOrderHead
from harithmapos.views.payment.forms import LedgerEntryForm, ReversalForm, DocumentPaymentForm
from harithmapos.permissions import owner_required, user_is_owner

import harithmapos.views.utils as utils

logger = logging.getLogger(__name__)

payment_blueprint = Blueprint('payment_blueprint', __name__)

PER_PAGE = 25
STAFF_TYPES = ('income',)        # counter staff can only record money coming in


@payment_blueprint.route("/app/payment", methods=['GET'])
@login_required
def payment():
    page = request.args.get('page', 1, type=int)
    direction = request.args.get('direction', '')
    kind = request.args.get('type', '')

    entries = Payment.query
    if not user_is_owner():
        # Counter staff see the money they took in, not wages, withdrawals or supplier payments.
        direction = 'in'
        entries = entries.filter(Payment.payment_type.in_(('sale', 'income')))
    if direction in ('in', 'out'):
        entries = entries.filter(Payment.payment_direction == direction)
    if kind in ledger.TYPES:
        entries = entries.filter(Payment.payment_type == kind)
    entries = entries.order_by(Payment.created_dttm.desc(), Payment.id.desc()).paginate(page=page, per_page=PER_PAGE)
    manual_types = [(t, ledger.TYPES[t]['label']) for t in config.MANUAL_PAYMENT_TYPES
                    if user_is_owner() or t in STAFF_TYPES]
    return render_template('payment.html', title='Payments', payments=entries, direction=direction, kind=kind,
                           manual_types=manual_types, type_labels={k: v['label'] for k, v in ledger.TYPES.items()})


@payment_blueprint.route("/app/payment/create", methods=['POST'])
@login_required
def insert_payment():
    form = LedgerEntryForm()
    if not form.validate_on_submit():
        utils.flash_form_errors(form)
        return utils.redirect_back('payment_blueprint.payment')
    if not user_is_owner() and form.payment_type.data not in STAFF_TYPES:
        flash("Only an owner can record money going out.", category='warning')
        return utils.redirect_back('payment_blueprint.payment')
    try:
        entry = ledger.post(form.payment_type.data, form.payment_amount.data, form.payment_method.data,
                            user=current_user, remarks=form.remarks.data)
        db.session.commit()
        flash(f"{ledger.TYPES[entry.payment_type]['label']} of {config.CURRENCY} {entry.payment_amount:,.2f} recorded.",
              category='success')
    except ledger.LedgerError as exc:
        db.session.rollback()
        flash(str(exc), category='warning')
    except Exception:
        db.session.rollback()
        logger.exception("Could not record a ledger entry")
        flash("The payment could not be recorded. Please try again.", category='danger')
    return utils.redirect_back('payment_blueprint.payment')


@payment_blueprint.route('/app/payment/<int:payment_id>/reverse', methods=['POST'])
@owner_required
def reverse_payment(payment_id):
    entry = db.get_or_404(Payment, payment_id)
    form = ReversalForm()
    if not form.validate_on_submit():
        utils.flash_form_errors(form)
        return utils.redirect_back('payment_blueprint.payment')
    had_payslip = Payslip.query.filter_by(payment_id=entry.id).count() > 0
    was_advance = entry.payment_type == 'advance'
    try:
        reversal = ledger.reverse(entry, form.reason.data, current_user)
        db.session.commit()
    except ledger.LedgerError as exc:
        db.session.rollback()
        flash(str(exc), category='warning')
        return utils.redirect_back('payment_blueprint.payment')
    except Exception:
        db.session.rollback()
        logger.exception("Could not reverse payment %s", payment_id)
        flash("The payment could not be reversed. Please try again.", category='danger')
        return utils.redirect_back('payment_blueprint.payment')
    note = ''
    if had_payslip:
        note = ' The payslip is unpaid again.'
    elif was_advance:
        note = ' The salary advance was removed.'
    flash(f"Payment #{entry.id} reversed by #{reversal.id}.{note}", category='success')
    return utils.redirect_back('payment_blueprint.payment')


# ---------------------------------------------------------------------------
# Payments and refunds on a completed invoice or purchase order's own page
# ---------------------------------------------------------------------------

def _document_action(document, here, label, refund=False):
    form = DocumentPaymentForm()
    if not form.validate_on_submit():
        utils.flash_form_errors(form)
        return redirect(here)
    if not document.is_completed:
        flash(f"Complete {label} first. Money handed over before that is entered on the bill and "
              "recorded when you press Complete.", category='warning')
        return redirect(here)
    amount = money(to_decimal(form.payment_amount.data))
    try:
        if refund:
            ledger.refund_document(document, amount, form.payment_method.data, current_user, form.remarks.data)
        else:
            ledger.pay_document(document, amount, form.payment_method.data, current_user, form.remarks.data)
        db.session.commit()
    except ledger.LedgerError as exc:
        db.session.rollback()
        flash(f"{str(exc)} Nothing was recorded.", category='warning')
        return redirect(here)
    except Exception:
        db.session.rollback()
        logger.exception("Could not record a %s for %s", 'refund' if refund else 'payment', label)
        flash("The payment could not be recorded. Please try again.", category='danger')
        return redirect(here)

    left = money(document.balance)
    if refund:
        flash(f"Refund of {config.CURRENCY} {amount:,.2f} recorded.", category='success')
    elif left > 0:
        flash(f"Payment of {config.CURRENCY} {amount:,.2f} recorded. "
              f"Still to pay: {config.CURRENCY} {left:,.2f}.", category='success')
    else:
        flash(f"Payment of {config.CURRENCY} {amount:,.2f} recorded. {label[0].upper() + label[1:]} is now settled.",
              category='success')
    return redirect(here)


def _invoice(invoice_head_id):
    invoice = db.get_or_404(InvoiceHead, invoice_head_id)
    return invoice, url_for('invoice_blueprint.invoice_head_detail', invoice_head_id=invoice.id), f"invoice #{invoice.id}"


def _sale(item_invoice_head_id):
    sale = db.get_or_404(ItemInvoiceHead, item_invoice_head_id)
    return sale, url_for('invoice_blueprint.item_invoice_head_detail', item_invoice_head_id=sale.id), f"item sale #{sale.id}"


def _order(purchase_order_head_id):
    order = db.get_or_404(PurchaseOrderHead, purchase_order_head_id)
    return (order, url_for('purchase_order_blueprint.purchase_order_head_detail', purchase_order_head_id=order.id),
            f"purchase order #{order.id}")


@payment_blueprint.route("/app/invoice/head/<int:invoice_head_id>/pay", methods=['POST'])
@login_required
def pay_invoice(invoice_head_id):
    return _document_action(*_invoice(invoice_head_id))


@payment_blueprint.route("/app/item_invoice/head/<int:item_invoice_head_id>/pay", methods=['POST'])
@login_required
def pay_item_invoice(item_invoice_head_id):
    return _document_action(*_sale(item_invoice_head_id))


@payment_blueprint.route("/app/purchase_order/head/<int:purchase_order_head_id>/pay", methods=['POST'])
@owner_required
def pay_purchase_order(purchase_order_head_id):
    return _document_action(*_order(purchase_order_head_id))


@payment_blueprint.route("/app/invoice/head/<int:invoice_head_id>/refund", methods=['POST'])
@owner_required
def refund_invoice(invoice_head_id):
    return _document_action(*_invoice(invoice_head_id), refund=True)


@payment_blueprint.route("/app/item_invoice/head/<int:item_invoice_head_id>/refund", methods=['POST'])
@owner_required
def refund_item_invoice(item_invoice_head_id):
    return _document_action(*_sale(item_invoice_head_id), refund=True)


@payment_blueprint.route("/app/purchase_order/head/<int:purchase_order_head_id>/refund", methods=['POST'])
@owner_required
def refund_purchase_order(purchase_order_head_id):
    return _document_action(*_order(purchase_order_head_id), refund=True)
