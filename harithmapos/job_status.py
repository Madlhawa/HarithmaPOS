"""Where a service job is on the floor (waiting, vacuuming ... done) and its history.

The job's stage is separate from the bill's state (documents.py): a job can
be Done while its bill is still a draft.

A vehicle can wait in the queue with no bay and nobody assigned. Work needs
them: vacuuming and washing happen in a bay with someone on it, polishing
needs someone. Done needs neither (a job can be billed straight from the queue).
"""
import logging

from harithmapos import config, db
from harithmapos.models import InvoiceStatusLog

logger = logging.getLogger(__name__)

NEEDS_BAY = (config.SERVICE_STATUS_VACUUMING, config.SERVICE_STATUS_WASHING)
NEEDS_EMPLOYEE = NEEDS_BAY + (config.SERVICE_STATUS_POLISHING,)


class JobError(Exception):
    """The job can't move to that stage yet. The message is safe to show."""


def missing_for(invoice, status):
    """What the job still needs before it can be at `status`: a list like ['a wash bay', 'an employee']."""
    missing = []
    if status in NEEDS_BAY and not invoice.washbay_id:
        missing.append('a wash bay')
    if status in NEEDS_EMPLOYEE and not invoice.employee_id:
        missing.append('who will work on it')
    return missing


def change(invoice, new_status):
    """Move the job to another stage. Returns True if it actually moved. Does not commit.

    Raises JobError if the stage needs a bay or an employee the job doesn't have yet.
    """
    if new_status is None:
        return False
    new_status = int(new_status)
    if new_status == (invoice.service_status or 0):
        return False
    missing = missing_for(invoice, new_status)
    if missing:
        stage = dict(config.SERVICE_STATUS_FORM_LIST).get(new_status, 'that stage')
        raise JobError(f"Choose {' and '.join(missing)} before moving {invoice.vehicle.number} to "
                       f"{str(stage).lower()}.")
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
