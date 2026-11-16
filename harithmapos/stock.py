"""Stock on the shelf: the only code that changes an item's quantity.

Every change is written down as a StockMovement (what moved, why, which
document, who, and the balance after), in the same transaction as the new
quantity, so an item's quantity always equals the sum of its movements and
its history can be read back on the item's stock page.

Items with no quantity (None) are services or labour: nothing here touches
them. Every change locks the item's row first (SELECT ... FOR UPDATE on
PostgreSQL) and works from the value in the database, so two counters
selling the same item at the same moment can't lose a deduction.

Nothing here commits: the caller does.
"""
from flask import has_request_context
from flask_login import current_user

from harithmapos import db
from harithmapos.billing import to_decimal
from harithmapos.models import InvoiceHead, ItemInvoiceHead, PurchaseOrderHead, StockMovement
from harithmapos.timeutils import utcnow

# Why stock moved, as shown on the item's stock page.
KINDS = {
    'opening': 'Opening stock',
    'count': 'Stock count',
    'sale': 'Sold',
    'sale_undo': 'Sale taken back',
    'purchase': 'Bought in',
    'purchase_undo': 'Purchase taken back',
    'void': 'Voided',
}

DOC_TYPES = {InvoiceHead: 'invoice', ItemInvoiceHead: 'item_sale', PurchaseOrderHead: 'purchase_order'}


class StockError(Exception):
    """Not enough stock. The message is safe to show."""


def qty_text(value):
    """2.5000 -> '2.5', 3.0000 -> '3', for messages."""
    text = f"{to_decimal(value):f}"
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text or '0'


def _locked(item):
    """The item with its row locked and its quantity read fresh from the database."""
    db.session.flush()   # earlier changes in this transaction must not be lost by the re-read
    db.session.refresh(item, attribute_names=['quantity'], with_for_update=True)
    return item


def _user_id(user):
    if user is not None:
        return getattr(user, 'id', None)
    if has_request_context() and getattr(current_user, 'is_authenticated', False):
        return current_user.id
    return None


def _record(item, change, kind, document=None, note=None, user=None):
    db.session.add(StockMovement(
        item_id=item.id, change=to_decimal(change), quantity_after=to_decimal(item.quantity),
        kind=kind, doc_type=DOC_TYPES.get(type(document)) if document is not None else None,
        doc_id=getattr(document, 'id', None), note=(note or None) and note[:200],
        user_id=_user_id(user),
    ))


def adjust(item, change, kind, document=None, note=None, user=None):
    """Add `change` (negative to remove) to a stock item and write it down. No check: see take()."""
    if item is None or not item.tracks_stock:
        return
    change = to_decimal(change)
    if not change:
        return
    item = _locked(item)
    item.quantity = to_decimal(item.quantity) + change
    item.update_dttm = utcnow()
    _record(item, change, kind, document, note, user)


def take(item, quantity, document=None):
    """Take `quantity` off the shelf for a sale. Raises StockError if there isn't that much."""
    if item is None or not item.tracks_stock:
        return
    quantity = to_decimal(quantity)
    item = _locked(item)
    left = to_decimal(item.quantity)
    if left < quantity:
        if left <= 0:
            raise StockError(f"No more {item.name} in stock.")
        raise StockError(f"Not enough stock of {item.name}: {qty_text(left)} left, {qty_text(quantity)} asked for.")
    adjust(item, -quantity, 'sale', document)


def put_back(item, quantity, document=None):
    """A sold quantity comes back (line removed or reduced)."""
    adjust(item, quantity, 'sale_undo', document)


def receive(item, quantity, document=None):
    """A delivery from a supplier goes onto the shelf."""
    adjust(item, quantity, 'purchase', document)


def unreceive(item, quantity, document=None):
    """A delivery is taken back off the shelf (line removed or reduced)."""
    adjust(item, -to_decimal(quantity), 'purchase_undo', document)


def set_count(item, quantity, user=None):
    """The owner typed the quantity on the Items page. None makes it a service with no stock.

    A new item is saved here (to get its id) and starts with an opening
    movement; for an existing one the difference is written down as a count.
    """
    quantity = None if quantity is None else to_decimal(quantity)
    if item.id is None:
        item.quantity = quantity
        db.session.add(item)
        db.session.flush()
        if quantity:
            _record(item, quantity, 'opening', user=user)
        return
    if item.tracks_stock:
        item = _locked(item)
        before = to_decimal(item.quantity)
    else:
        before = None
    if quantity is None:
        if before is not None:
            item.quantity = 0           # the balance the movement leaves behind
            _record(item, -before, 'count', note='Made a service: stock no longer kept', user=user)
        item.quantity = None
        return
    item.quantity = quantity
    if before is None:
        if quantity:
            _record(item, quantity, 'count', note='Now kept in stock', user=user)
    elif quantity != before:
        _record(item, quantity - before, 'count', user=user)
