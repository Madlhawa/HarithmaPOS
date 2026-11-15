"""The life of an invoice, item sale or purchase order: draft -> completed, or -> void.

All state changes go through here, so the rules are in one place:

  * Only a draft can change its lines, discounts, or customer/supplier.
  * Completing needs at least one line. It stamps who and when; a service
    invoice's job is marked Done too if it is not already.
  * Nothing goes back from completed to draft. A wrong bill is voided and a
    new one made. Voiding needs a reason and an owner, and the document must
    hold no money: refund or reverse its payments first, so the ledger
    explains where the money went.
  * Voiding puts stock back: lines sold go back on the shelf, a delivery is
    taken back off it. The document and its lines stay, marked void.

Nothing here commits: the caller does.
"""
from decimal import Decimal

from harithmapos import config, db
from harithmapos.models import (
    DOC_COMPLETED, DOC_DRAFT, DOC_VOID, InvoiceDetail, InvoiceHead, ItemInvoiceDetail, ItemInvoiceHead,
    PurchaseOrderDetail, PurchaseOrderHead,
)
from harithmapos.timeutils import utcnow

# document model -> (line model, line column pointing at it, stock sign when the lines were added)
LINES = {
    InvoiceHead: (InvoiceDetail, InvoiceDetail.invoice_head_id, -1),
    ItemInvoiceHead: (ItemInvoiceDetail, ItemInvoiceDetail.item_invoice_head_id, -1),
    PurchaseOrderHead: (PurchaseOrderDetail, PurchaseOrderDetail.purchase_order_head_id, +1),
}


class DocumentError(Exception):
    """A change the document's state does not allow. The message is safe to show."""


def label(document):
    if isinstance(document, InvoiceHead):
        return f"Invoice #{document.id}"
    if isinstance(document, ItemInvoiceHead):
        return f"Item sale #{document.id}"
    return f"Purchase order #{document.id}"


def lines_of(document):
    model, column, _ = LINES[type(document)]
    return model.query.filter(column == document.id).order_by(model.id).all()


def require_draft(document):
    """Refuse any change to lines, prices, discounts or the other party once it is not a draft."""
    if document.is_void:
        raise DocumentError(f"{label(document)} is void and cannot be changed.")
    if not document.is_draft:
        raise DocumentError(f"{label(document)} is completed, so its items and amounts are fixed. "
                            "An owner can void it and start a new one.")


def complete(document, user=None):
    """Draft -> completed. Returns True if a service invoice's job had to be marked Done."""
    require_draft(document)
    if not lines_of(document):
        raise DocumentError(f"Add at least one item before completing {label(document).lower()}.")
    document.doc_status = DOC_COMPLETED
    document.completed_dttm = document.update_dttm = utcnow()
    document.completed_by_id = getattr(user, 'id', None)
    if isinstance(document, InvoiceHead) and document.service_status != config.SERVICE_STATUS_DONE:
        document.service_status = config.SERVICE_STATUS_DONE
        return True
    return False


def void(document, reason, user=None):
    """Draft or completed -> void, putting stock back. The document must hold no money."""
    if document.is_void:
        raise DocumentError(f"{label(document)} is already void.")
    reason = (reason or '').strip()
    if not reason:
        raise DocumentError("Say why it is being voided.")
    paid = Decimal(str(document.paid_amount or 0))
    if paid != 0:
        verb = 'paid to the supplier' if isinstance(document, PurchaseOrderHead) else 'paid'
        raise DocumentError(f"{config.CURRENCY} {paid:,.2f} has been {verb} on {label(document).lower()}. "
                            "Refund or reverse those payments first, then void it.")
    _, _, sign = LINES[type(document)]
    for line in lines_of(document):
        item = line.item
        if item is not None and item.tracks_stock:
            item.quantity = item.quantity - sign * line.quantity       # undo what adding the line did
    document.doc_status = DOC_VOID
    document.voided_dttm = document.update_dttm = utcnow()
    document.voided_by_id = getattr(user, 'id', None)
    document.void_reason = reason[:200]
