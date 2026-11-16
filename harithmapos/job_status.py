"""Where a service job is on the floor (waiting, vacuuming ... done) and its history.

The job's stage is separate from the bill's state (documents.py): a job can
be Done while its bill is still a draft.
"""
import logging

from harithmapos import db
from harithmapos.models import InvoiceStatusLog

logger = logging.getLogger(__name__)


def change(invoice, new_status):
    """Move the job to another stage. Returns True if it actually moved. Does not commit."""
    if new_status is None:
        return False
    new_status = int(new_status)
    if new_status == (invoice.service_status or 0):
        return False
    invoice.service_status = new_status
    return True


def _latest_log_id(invoice):
    latest = (
        InvoiceStatusLog.query
        .filter(InvoiceStatusLog.invoice_id == invoice.id)
        .order_by(InvoiceStatusLog.id.desc())
        .first()
    )
    return latest.id if latest else None


def log(invoice, previous_log_id='lookup'):
    """Write a status history row for the job's current stage. Commits on its own and never raises."""
    try:
        if previous_log_id == 'lookup':
            previous_log_id = _latest_log_id(invoice)
        db.session.add(InvoiceStatusLog(
            previous_invoice_status_log_id=previous_log_id,
            invoice_id=invoice.id,
            service_status=invoice.service_status,
            employee_id=invoice.employee_id,
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Could not write status log for invoice %s", invoice.id)
