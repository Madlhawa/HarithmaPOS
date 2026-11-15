"""The money ledger: the only way money is recorded.

Every rupee that comes in or goes out is one Payment row (an "entry"), and
entries are never changed or deleted. To undo one, `reverse()` adds an entry
for the same amount the other way, pointing back at it. What an invoice,
item sale or purchase order has been paid is the sum of its entries (see
`_paid_column` in models.py), so there is one answer to "what was paid".

Rules kept here:
  * the type fixes the direction (a customer payment is money in, wages out);
  * a document is never paid more than it costs: change is given back at the
    counter and noted on the entry (`tendered_amount`), not kept as a credit;
  * refunds only take back what a document was overpaid;
  * a reversal cannot be reversed, and an entry can be reversed only once.

Nothing here commits: the caller does, so an entry and the change it belongs
to are saved together.
"""
from decimal import Decimal

from sqlalchemy import case, event, func
from sqlalchemy.orm import Session

from harithmapos import config, db
from harithmapos.billing import money, to_decimal, ZERO
from harithmapos.models import InvoiceHead, ItemInvoiceHead, Payment, PurchaseOrderHead, Payslip, SalaryAdvance
from harithmapos.timeutils import utcnow

TYPES = {key: {'label': label, 'direction': direction} for key, label, direction in config.PAYMENT_TYPES}
METHODS = dict(config.PAYMENT_METHOD_FORM_LIST)

# Which ledger types money from customers and to suppliers fall under (used by reports and the dashboard).
SALES_TYPES = ('sale', 'sale_refund')
PAID_OUT_TYPES = ('supplier', 'supplier_refund', 'wage', 'advance', 'expense', 'withdrawal')

# document model -> (link column on Payment, type that pays it, type that refunds it)
DOCUMENTS = {
    InvoiceHead: ('invoice_id', 'sale', 'sale_refund'),
    ItemInvoiceHead: ('item_invoice_id', 'sale', 'sale_refund'),
    PurchaseOrderHead: ('purchase_order_id', 'supplier', 'supplier_refund'),
}


class LedgerError(Exception):
    """A payment that the rules do not allow. The message is safe to show."""


def _user_id(user):
    return getattr(user, 'id', None) if user is not None and getattr(user, 'is_authenticated', True) else None


def post(payment_type, amount, method, *, user=None, remarks=None, tendered=None, **links):
    """Add one entry to the ledger. Does not commit."""
    if payment_type not in TYPES:
        raise LedgerError(f"Unknown payment type {payment_type!r}.")
    if method not in METHODS:
        raise LedgerError("Choose how the money was paid.")
    amount = money(to_decimal(amount))
    if amount <= 0:
        raise LedgerError("Enter an amount above 0.")
    if tendered is not None:
        tendered = money(to_decimal(tendered))
        if tendered <= amount:
            tendered = None                      # only worth noting when there was change
    entry = Payment(
        payment_type=payment_type, payment_direction=TYPES[payment_type]['direction'],
        payment_method=method, payment_amount=amount, tendered_amount=tendered,
        remarks=(remarks or None), created_by_id=_user_id(user), created_dttm=utcnow(), **links)
    db.session.add(entry)
    db.session.flush()
    _refresh_documents(entry)
    return entry


def reverse(entry, reason, user=None):
    """Cancel an entry with an equal entry the other way. Does not commit.

    A reversed wage payment leaves its payslip unpaid again; a reversed salary
    advance removes the advance (unless a payslip has already taken it back).
    """
    if entry.is_reversal:
        raise LedgerError("This entry is itself a reversal and cannot be reversed. Record a new payment instead.")
    if entry.is_reversed:
        raise LedgerError("This entry has already been reversed.")
    reason = (reason or '').strip()
    if not reason:
        raise LedgerError("Say why it is being reversed.")
    advance = SalaryAdvance.query.filter_by(payment_id=entry.id).first()
    if advance is not None and advance.is_recovered:
        raise LedgerError("A payslip has already taken this salary advance back. Reopen that month's payroll first.")

    reversal = Payment(
        payment_type=entry.payment_type,
        payment_direction='out' if entry.payment_direction == 'in' else 'in',
        payment_method=entry.payment_method, payment_amount=entry.payment_amount,
        remarks=f"Reversal of #{entry.id}: {reason}"[:255], reverses_id=entry.id,
        invoice_id=entry.invoice_id, item_invoice_id=entry.item_invoice_id,
        purchase_order_id=entry.purchase_order_id, customer_id=entry.customer_id, employee_id=entry.employee_id,
        created_by_id=_user_id(user), created_dttm=utcnow())
    db.session.add(reversal)
    for slip in Payslip.query.filter_by(payment_id=entry.id).all():
        slip.payment_id = None
    if advance is not None:
        db.session.delete(advance)
    db.session.flush()
    db.session.expire(entry, ['reversed_by'])
    _refresh_documents(reversal)
    return reversal


def _refresh_documents(entry):
    """The paid amount of a linked document is computed in SQL: reload it after a new entry."""
    for model, (link, _, _) in DOCUMENTS.items():
        document_id = getattr(entry, link)
        if document_id:
            document = db.session.get(model, document_id)
            if document is not None:
                db.session.expire(document, ['paid_amount'])


def _document_link(document):
    link, pay_type, refund_type = DOCUMENTS[type(document)]
    links = {link: document.id}
    if getattr(document, 'customer_id', None):
        links['customer_id'] = document.customer_id
    return links, pay_type, refund_type


def pay_document(document, amount, method, user=None, remarks=None, tendered=None):
    """Money towards what a document still owes (a customer paying, or paying a supplier)."""
    if not document.is_completed:
        raise LedgerError("Complete it first: money is only taken against a completed bill.")
    links, pay_type, _ = _document_link(document)
    balance = money(document.balance)
    amount = money(to_decimal(amount))
    if balance <= 0:
        raise LedgerError("Nothing is left to pay on it.")
    if amount > balance:
        raise LedgerError(f"That is more than the balance of {config.CURRENCY} {balance:,.2f}.")
    return post(pay_type, amount, method, user=user, remarks=remarks, tendered=tendered, **links)


def refund_document(document, amount, method, user=None, remarks=None):
    """Give back money paid on a document (a customer refund, or the supplier paying us back).

    Up to what was paid. Refunding everything is how a paid bill is emptied before it is voided.
    """
    if not document.is_completed:
        raise LedgerError("Only a completed bill can be refunded.")
    links, _, refund_type = _document_link(document)
    paid = money(document.paid_amount)
    amount = money(to_decimal(amount))
    if paid <= 0:
        raise LedgerError("Nothing has been paid on it, so there is nothing to refund.")
    if amount > paid:
        raise LedgerError(f"That is more than the {config.CURRENCY} {paid:,.2f} paid.")
    return post(refund_type, amount, method, user=user, remarks=remarks, **links)


def take_on_completion(document, received, method, user=None):
    """Money handed over when a document is completed.

    Records at most what is owed; anything above that is change, noted on the
    entry. Returns (entry or None, change to give back).
    """
    received = money(max(to_decimal(received), ZERO))
    balance = money(document.balance)
    if received <= 0 or balance <= 0:
        return None, received if balance <= 0 else ZERO
    amount = min(received, balance)
    entry = pay_document(document, amount, method, user=user, tendered=received)
    return entry, money(received - amount)


def net(query, positive='in'):
    """Sum of entries in a query: one direction counts up, the other (refunds, reversals) down."""
    signed = case((Payment.payment_direction == positive, Payment.payment_amount), else_=-Payment.payment_amount)
    total = query.with_entities(func.coalesce(func.sum(signed), 0)).scalar()
    return money(Decimal(str(total or 0)))


def between(lo, hi):
    """Entries made in [lo, hi) (UTC)."""
    return Payment.query.filter(Payment.created_dttm >= lo, Payment.created_dttm < hi)


def collected(lo, hi):
    """Money from customers for invoices and sales, less refunds and reversals."""
    return net(between(lo, hi).filter(Payment.payment_type.in_(SALES_TYPES)), 'in')


def paid_out(lo, hi):
    """Money paid out to suppliers, staff, expenses and the owner, less refunds and reversals."""
    return net(between(lo, hi).filter(Payment.payment_type.in_(PAID_OUT_TYPES)), 'out')


# ---------------------------------------------------------------------------
# Entries are append-only
# ---------------------------------------------------------------------------

@event.listens_for(Session, 'before_flush')
def _entries_are_append_only(session, flush_context, instances):
    for obj in session.deleted:
        if isinstance(obj, Payment):
            raise LedgerError("Payments cannot be deleted. Reverse it instead.")
    for obj in session.dirty:
        if isinstance(obj, Payment) and session.is_modified(obj, include_collections=False):
            raise LedgerError("Payments cannot be changed. Reverse it and record it again instead.")
