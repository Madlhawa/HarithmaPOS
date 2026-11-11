"""Keeps the Payment table in step with what invoices and purchase orders say was paid.

Two things touch the same money:
  * the "paid" box on an invoice / purchase order screen, and
  * rows on the Payments page.
The helpers here make sure each rupee is counted once.
"""

from flask import flash

from harithmapos import db, config
from harithmapos.billing import to_decimal, money, amount_to_record, ZERO
from harithmapos.models import Payment, InvoiceHead, ItemInvoiceHead, PurchaseOrderHead
from harithmapos.timeutils import local_today

from utils.database import safe_insert_with_sequence_check

# Payment link column -> (document model, payment direction that pays it off)
DOCUMENTS = {
    'invoice_id': (InvoiceHead, 'in'),
    'item_invoice_id': (ItemInvoiceHead, 'in'),
    'purchase_order_id': (PurchaseOrderHead, 'out'),
}


def signed_amount(payment, paying_direction):
    """A payment in the paying direction counts up; the opposite one (a refund) counts down."""
    opposite = 'out' if paying_direction == 'in' else 'in'
    amount = to_decimal(payment.payment_amount)
    return -amount if payment.payment_direction == opposite else amount


def recorded_total(link_field, document_id):
    """Net amount already in the payment ledger for one document."""
    _, paying_direction = DOCUMENTS[link_field]
    payments = Payment.query.filter(getattr(Payment, link_field) == document_id).all()
    return sum((signed_amount(payment, paying_direction) for payment in payments), ZERO)


def sync_document_payment(document, link_field, remarks='Invoice payment'):
    """Record in the ledger whatever part of document.paid_amount is not there yet.

    Called when an invoice or purchase order is completed. Safe to call
    again and again: pressing "Complete" twice does not create a second
    payment. Returns the amount that was added.
    """
    _, paying_direction = DOCUMENTS[link_field]
    target = amount_to_record(document.paid_amount, document.gross_price)
    recorded = recorded_total(link_field, document.id)
    difference = money(target - recorded)

    if difference > 0:
        safe_insert_with_sequence_check(
            Payment,
            customer_id=getattr(document, 'customer_id', None),
            payment_method=document.payment_method or 'cash',
            payment_direction=paying_direction,
            payment_amount=difference,
            payment_type='general',
            remarks=remarks,
            **{link_field: document.id},
        )
        return difference

    if difference < 0:
        flash(
            f"Payments already recorded for this document add up to {config.CURRENCY} {recorded:,.2f}, "
            "which is more than the paid amount entered. Check the Payments page.",
            category='warning',
        )
    return ZERO


def apply_payment(payment, sign=1):
    """Add (sign=1) or take back (sign=-1) a payment's effect on its documents.

    Does not commit; the caller decides when.
    """
    for link_field, (model, paying_direction) in DOCUMENTS.items():
        document_id = getattr(payment, link_field)
        if not document_id:
            continue
        document = db.session.get(model, document_id)
        if document is None:
            continue
        change = signed_amount(payment, paying_direction) * sign
        document.paid_amount = to_decimal(document.paid_amount) + change
        document.remaining_amount = to_decimal(document.gross_price) - document.paid_amount
        if sign > 0:
            document.last_payment_date = local_today(config.APP_TIMEZONE)
