"""Stock on the shelf: the only code that changes an item's quantity.

Items with no quantity (None) are services or labour: nothing here touches
them. Every change locks the item's row first (SELECT ... FOR UPDATE on
PostgreSQL) and works from the value in the database, so two counters
selling the same item at the same moment can't lose a deduction.

Nothing here commits: the caller does.
"""
from harithmapos import db
from harithmapos.billing import to_decimal
from harithmapos.timeutils import utcnow


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


def adjust(item, change):
    """Add `change` (negative to remove) to a stock item. No check: see take()."""
    if item is None or not item.tracks_stock:
        return
    change = to_decimal(change)
    if not change:
        return
    item = _locked(item)
    item.quantity = to_decimal(item.quantity) + change
    item.update_dttm = utcnow()


def take(item, quantity):
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
    adjust(item, -quantity)


def put_back(item, quantity):
    """A sold quantity comes back (line removed or reduced, sale voided)."""
    adjust(item, quantity)


def receive(item, quantity):
    """A delivery from a supplier goes onto the shelf."""
    adjust(item, quantity)


def unreceive(item, quantity):
    """A delivery is taken back off the shelf (line removed or reduced, order voided)."""
    adjust(item, -to_decimal(quantity))


def set_count(item, quantity):
    """The owner typed the quantity on the Items page. None makes it a service with no stock."""
    if quantity is None:
        item.quantity = None
        return
    if item.id is not None and item.tracks_stock:
        item = _locked(item)
    item.quantity = to_decimal(quantity)
