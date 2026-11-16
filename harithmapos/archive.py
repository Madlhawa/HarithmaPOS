"""Archive instead of delete, for customers, items and suppliers.

Deleting a customer, item or supplier would either fail (their invoices and
orders still name them) or lose history. Instead they are archived: hidden
from the lists and search boxes, kept on every document. An owner can show
the archived ones on each list and restore them.

Using an archived customer or supplier again brings it back by itself: a new
invoice, item sale, vehicle or purchase order for them restores them, so a
returning customer never has to be found in the archive first. Archived
items can't be sold or bought until they are restored (lines.py refuses).
"""
from sqlalchemy import event
from sqlalchemy.orm import Session

from harithmapos.models import Customer, InvoiceHead, ItemInvoiceHead, PurchaseOrderHead, Supplier, Vehicle
from harithmapos.timeutils import utcnow

WALK_IN_CUSTOMER_ID = -1


class ArchiveError(Exception):
    """The record can't be archived. The message is safe to show."""


def archive(record, user=None):
    if isinstance(record, Customer) and record.id == WALK_IN_CUSTOMER_ID:
        raise ArchiveError("The General Customer is used for walk-in sales and can't be archived.")
    if record.is_archived:
        return
    record.archived_dttm = utcnow()
    record.archived_by_id = getattr(user, 'id', None)


def restore(record):
    record.archived_dttm = None
    record.archived_by_id = None


def current(query, model):
    """Only the records that are not archived."""
    return query.filter(model.archived_dttm.is_(None))


# A new document or vehicle for an archived customer or supplier restores them.
_OWNER = {
    InvoiceHead: (Customer, 'customer_id'),
    ItemInvoiceHead: (Customer, 'customer_id'),
    Vehicle: (Customer, 'owner_id'),
    PurchaseOrderHead: (Supplier, 'supplier_id'),
}


@event.listens_for(Session, 'before_flush')
def _restore_when_used(session, flush_context, instances):
    for obj in list(session.new):
        owner = _OWNER.get(type(obj))
        if owner is None:
            continue
        model, column = owner
        owner_id = getattr(obj, column, None)
        record = session.get(model, owner_id) if owner_id is not None else None
        if record is not None and record.is_archived:
            restore(record)
