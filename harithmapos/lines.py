"""The lines of a service invoice, item sale or purchase order, and the totals they add up to.

Every change to a document's lines goes through here: adding, removing and
changing the quantity of a line, with the matching stock movement (see
stock.py) and the document's totals worked out again. The routes only read
the form, call one of these and show the result.

  * Only a draft's lines can change (documents.require_draft).
  * Sales take stock off the shelf and refuse to sell what isn't there;
    a purchase order puts stock on the shelf. Removing a line or lowering
    its quantity undoes exactly that.
  * The head's totals always equal the sum of its lines (billing.py has the
    arithmetic and the rounding).
  * A line keeps the item's name, cost, price and automatic discount as they
    were when it was added (models.SoldAs). Changing the item later, or +/- on
    a draft line, never reprices it.

Nothing here commits: the caller does. Problems the person can fix raise
documents.DocumentError or stock.StockError, with a message safe to show.
"""
from harithmapos import db, stock
from harithmapos.billing import invoice_totals, line_amounts, money, purchase_totals, to_decimal
from harithmapos.documents import DocumentError, LINES, lines_of, require_draft
from harithmapos.models import InvoiceDetail, InvoiceHead, ItemInvoiceDetail, ItemInvoiceHead, PurchaseOrderHead
from harithmapos.timeutils import utcnow

# The column on each line model that points at its document.
HEAD_FIELD = {
    InvoiceHead: 'invoice_head_id',
    ItemInvoiceHead: 'item_invoice_head_id',
    PurchaseOrderHead: 'purchase_order_head_id',
}


def is_purchase(document):
    return isinstance(document, PurchaseOrderHead)


def head_of(line):
    """The document a line belongs to."""
    if isinstance(line, InvoiceDetail):
        return db.session.get(InvoiceHead, line.invoice_head_id)
    if isinstance(line, ItemInvoiceDetail):
        return db.session.get(ItemInvoiceHead, line.item_invoice_head_id)
    return db.session.get(PurchaseOrderHead, line.purchase_order_head_id)


# ---------------------------------------------------------------------------
# Totals
# ---------------------------------------------------------------------------

def recalculate(document):
    """Work the document's totals out again from its lines. Returns the lines."""
    lines = lines_of(document)
    if is_purchase(document):
        totals = purchase_totals(lines, document.discount_pct)
        # total_cost is not a column on the order; it is set for the screen to show.
        document.total_cost = totals['total_cost']
        document.total_price = totals['total_price']
        document.gross_price = totals['gross_price']
        return lines
    totals = invoice_totals(lines, bill_discount=document.discount_amount)
    document.total_cost = totals['total_cost']
    document.total_price = totals['total_price']
    document.total_discount = totals['total_discount']
    document.discount_amount = totals['discount_amount']
    document.gross_price = totals['gross_price']
    return lines


def _touch(document):
    db.session.flush()
    recalculate(document)
    document.update_dttm = utcnow()


# ---------------------------------------------------------------------------
# One line's amounts
# ---------------------------------------------------------------------------

def set_sale_amounts(line, extra_discount=None):
    """Fill a sale line's totals and discounts from its own unit prices and quantity."""
    if extra_discount is None:
        extra_discount = line.additional_discount
    amounts = line_amounts(line.quantity, line.unit_cost, line.unit_price,
                           line.discount_pct, extra_discount)
    for key, value in amounts.items():
        setattr(line, key, value)


def _set_purchase_quantity(line, quantity):
    """A purchase line keeps its own unit cost and price when its quantity changes."""
    line.quantity = quantity
    line.total_cost = money(to_decimal(line.unit_cost) * quantity)
    line.total_price = money(to_decimal(line.unit_price) * quantity)


# ---------------------------------------------------------------------------
# Changing lines
# ---------------------------------------------------------------------------

def add_sale_line(document, item, quantity, extra_discount=0):
    """Sell `quantity` of `item` on a service invoice or item sale. Returns the new line."""
    require_draft(document)
    quantity = to_decimal(quantity)
    if quantity <= 0:
        raise DocumentError("Enter a quantity above zero.")
    stock.take(item, quantity, document)
    line_model = LINES[type(document)][0]
    line = line_model(item_id=item.id, quantity=quantity, item_name=item.name,
                      unit_cost=money(to_decimal(item.unit_cost)), unit_price=money(to_decimal(item.unit_price)),
                      discount_pct=to_decimal(item.discount_pct))
    set_sale_amounts(line, extra_discount)
    setattr(line, HEAD_FIELD[type(document)], document.id)
    db.session.add(line)
    _touch(document)
    return line


def add_purchase_line(order, item, quantity, unit_cost=None):
    """Buy in `quantity` of `item` at `unit_cost` (default: the item's cost). Returns the new line."""
    require_draft(order)
    if not item.tracks_stock:
        raise DocumentError(f"{item.name} is set up as a service with no stock. "
                            "Give it a stock quantity on the Items page before buying it in.")
    quantity = to_decimal(quantity)
    if quantity <= 0:
        raise DocumentError("Enter a quantity above zero.")
    unit_cost = to_decimal(item.unit_cost if unit_cost is None else unit_cost)
    stock.receive(item, quantity, order)
    # Remember what the item costs now, so profit on later sales is right.
    item.unit_cost = money(unit_cost)
    line = LINES[PurchaseOrderHead][0](
        purchase_order_head_id=order.id, item_id=item.id, quantity=quantity, item_name=item.name,
        unit_cost=money(unit_cost), unit_price=money(to_decimal(item.unit_price)),
        discount_pct=0,
    )
    _set_purchase_quantity(line, quantity)
    db.session.add(line)
    _touch(order)
    return line


def remove_line(document, line):
    """Take a line off the document and undo its stock movement."""
    require_draft(document)
    if is_purchase(document):
        stock.unreceive(line.item, line.quantity, document)
    else:
        stock.put_back(line.item, line.quantity, document)
    db.session.delete(line)
    _touch(document)


def change_quantity(document, line, step):
    """One more (step=1) or one less (step=-1) on a line."""
    require_draft(document)
    step = to_decimal(step)
    new_quantity = to_decimal(line.quantity) + step
    if new_quantity < 1:
        raise DocumentError("Quantity is already at the minimum. Remove the item instead.")
    if is_purchase(document):
        if step > 0:
            stock.receive(line.item, step, document)
        else:
            stock.unreceive(line.item, -step, document)
        _set_purchase_quantity(line, new_quantity)
    else:
        if step > 0:
            stock.take(line.item, step, document)
        else:
            stock.put_back(line.item, -step, document)
        line.quantity = new_quantity
        set_sale_amounts(line)
    line.update_dttm = utcnow()
    _touch(document)

