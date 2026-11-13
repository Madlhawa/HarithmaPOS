"""The floor board: a full-screen, touch-friendly page for the supervisor's tablet.

Shows the waiting queue, every wash bay, polishing and what is ready, and lets
the supervisor add a vehicle to the queue and move vehicles between stages with
one tap. Billing stays on the counter: a vehicle marked Ready shows up there as
unpaid until someone presses Complete on its invoice.
"""
import logging
import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import and_, func, or_

from harithmapos import config, db
from harithmapos.models import Customer, Employee, InvoiceHead, InvoiceStatusLog, Vehicle, WashBay
from harithmapos.textutils import normalize_phone, normalize_plate
from harithmapos.timeutils import local_day_bounds_utc, utcnow
from harithmapos.views.invoice.routes import _change_status, _log_status
from utils.database import safe_insert_with_sequence_check

logger = logging.getLogger(__name__)
floor_blueprint = Blueprint('floor_blueprint', __name__)

WAITING = config.SERVICE_STATUS_WAITING
POLISHING = config.SERVICE_STATUS_POLISHING
DONE = config.SERVICE_STATUS_DONE
IN_BAY = (config.SERVICE_STATUS_VACUUMING, config.SERVICE_STATUS_WASHING)
READY_SHOWN = 12


def _here():
    return redirect(url_for('floor_blueprint.board'))


def _int(name):
    try:
        return int(request.form.get(name, ''))
    except (TypeError, ValueError):
        return None


def _stage_since(invoices):
    """When each invoice entered its current stage (the latest status log), by invoice id."""
    ids = [invoice.id for invoice in invoices]
    if not ids:
        return {}
    rows = (db.session.query(InvoiceStatusLog.invoice_id, func.max(InvoiceStatusLog.created_dttm))
            .filter(InvoiceStatusLog.invoice_id.in_(ids))
            .group_by(InvoiceStatusLog.invoice_id).all())
    since = dict(rows)
    return {invoice.id: since.get(invoice.id) or invoice.created_dttm for invoice in invoices}


def board_data():
    open_invoices = (InvoiceHead.query.filter(InvoiceHead.service_status < DONE)
                     .order_by(InvoiceHead.created_dttm).all())

    day_start, day_end = local_day_bounds_utc(tz_name=config.APP_TIMEZONE)
    finished_today = InvoiceHead.invoice_statuses.any(and_(
        InvoiceStatusLog.service_status == DONE,
        InvoiceStatusLog.created_dttm >= day_start,
        InvoiceStatusLog.created_dttm < day_end,
    ))
    created_today = and_(InvoiceHead.created_dttm >= day_start, InvoiceHead.created_dttm < day_end)
    ready = (InvoiceHead.query.filter(InvoiceHead.service_status == DONE, or_(finished_today, created_today))
             .order_by(InvoiceHead.update_dttm.desc()).all())

    since = _stage_since(open_invoices + ready)
    queue = [i for i in open_invoices if (i.service_status or 0) == WAITING]
    polishing = [i for i in open_invoices if i.service_status == POLISHING]

    washbays = WashBay.query.order_by(WashBay.name).all()
    bays = []
    for bay in washbays:
        jobs = [i for i in open_invoices if i.service_status in IN_BAY and i.washbay_id == bay.id]
        bays.append({
            'bay': bay,
            'jobs': jobs,
            'next': [i for i in queue if i.washbay_id == bay.id],
        })
    free_bays = [entry['bay'] for entry in bays if not entry['jobs']]

    busy = {}
    for invoice in open_invoices:
        if invoice.service_status != WAITING:
            busy[invoice.employee_id] = busy.get(invoice.employee_id, 0) + 1
    employees = (Employee.query.filter(Employee.active.is_(True)).order_by(Employee.name).all())

    return {
        'queue': queue,
        'bays': bays,
        'free_bays': free_bays,
        'polishing': polishing,
        'ready': ready[:READY_SHOWN],
        'ready_count': len(ready),
        'unpaid_ready': sum(1 for i in ready if i.balance > 0),
        'since': since,
        'washbays': washbays,
        'employees': employees,
        'busy': busy,
        'in_station': len(open_invoices),
    }


@floor_blueprint.route('/app/floor')
@login_required
def board():
    return render_template('floor/board.html', title='Floor', **board_data())


def _bay_taken_by(bay_id, invoice_id=None):
    """The other vehicle already in this bay (vacuuming or washing), if any."""
    query = InvoiceHead.query.filter(InvoiceHead.washbay_id == bay_id, InvoiceHead.service_status.in_(IN_BAY))
    if invoice_id:
        query = query.filter(InvoiceHead.id != invoice_id)
    return query.first()


@floor_blueprint.route('/app/floor/<int:invoice_id>/move', methods=['POST'])
@login_required
def move(invoice_id):
    """Change a vehicle's stage, and optionally its bay and employee."""
    invoice = db.get_or_404(InvoiceHead, invoice_id)
    status = _int('status')
    if status is None or not 0 <= status <= DONE:
        status = invoice.service_status or 0

    bay_id = _int('washbay_id')
    if bay_id and bay_id != invoice.washbay_id:
        if not db.session.get(WashBay, bay_id):
            flash("That wash bay no longer exists.", category='danger')
            return _here()
        invoice.washbay_id = bay_id
    employee_id = _int('employee_id')
    if employee_id and employee_id != invoice.employee_id:
        if not db.session.get(Employee, employee_id):
            flash("That employee no longer exists.", category='danger')
            return _here()
        invoice.employee_id = employee_id

    if status in IN_BAY:
        other = _bay_taken_by(invoice.washbay_id, invoice.id)
        if other:
            db.session.rollback()
            flash(f"{other.washbay.name} already has {other.vehicle.number}. "
                  f"Move it on first, or choose another bay.", category='warning')
            return _here()

    try:
        changed = _change_status(invoice, status)
        invoice.update_dttm = utcnow()
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Could not move invoice %s", invoice_id)
        flash("That change was not saved. Please try again.", category='danger')
        return _here()

    if changed:
        _log_status(invoice)
        label = 'ready to collect' if status == DONE else invoice.service_status_str.lower()
        flash(f"{invoice.vehicle.number} is now {label}.", category='success')
    else:
        flash(f"{invoice.vehicle.number} updated.", category='success')
    return _here()


@floor_blueprint.route('/app/floor/add', methods=['POST'])
@login_required
def add():
    """Put a vehicle in the queue (or straight into a bay), registering it first if it is new."""
    employee = db.session.get(Employee, _int('employee_id') or 0)
    washbay = db.session.get(WashBay, _int('washbay_id') or 0)
    if not employee or not washbay:
        flash("Choose who will work on it and which bay.", category='warning')
        return _here()

    vehicle = db.session.get(Vehicle, _int('vehicle_id') or 0)
    number = normalize_plate(request.form.get('number'))
    if vehicle is None and number:
        vehicle = Vehicle.query.filter(func.upper(Vehicle.number) == number).first()

    name = (request.form.get('name') or '').strip()
    phone_raw = (request.form.get('contact') or '').strip()
    if vehicle is None:
        if not number or not 4 <= len(number) <= 8:
            flash("Enter the vehicle number (4 to 8 characters, for example CAB-1234).", category='warning')
            return _here()
        if len(name) < 2:
            flash(f"{number} is new. Enter the owner's name to register it.", category='warning')
            return _here()
        phone = normalize_phone(phone_raw) if phone_raw else None
        if phone and not re.fullmatch(r'\d{9}', phone):
            flash("Check the phone number, for example 077 123 4567.", category='warning')
            return _here()

    if vehicle is not None:
        open_invoice = InvoiceHead.query.filter(
            InvoiceHead.vehicle_id == vehicle.id, InvoiceHead.service_status < DONE).first()
        if open_invoice:
            flash(f"{vehicle.number} is already on the floor ({open_invoice.service_status_str.lower()}).",
                  category='info')
            return _here()

    start_now = request.form.get('start') == 'now'
    if start_now:
        other = _bay_taken_by(washbay.id)
        if other:
            flash(f"{washbay.name} already has {other.vehicle.number}. The new vehicle was not added: "
                  f"choose a free bay or add it to the queue.", category='warning')
            return _here()

    mileage = request.form.get('current_milage', '').replace(',', '').strip()
    mileage = int(mileage) if mileage.isdigit() else None

    try:
        if vehicle is None:
            customer = None
            if phone:
                customer = Customer.query.filter(
                    Customer.contact == phone, func.lower(Customer.name) == name.lower()).first()
            if customer is None:
                customer = safe_insert_with_sequence_check(Customer, name=name[:100], contact=phone)
            vehicle = safe_insert_with_sequence_check(Vehicle, number=number, owner_id=customer.id)
        invoice = safe_insert_with_sequence_check(
            InvoiceHead,
            customer_id=vehicle.owner_id,
            vehicle_id=vehicle.id,
            washbay_id=washbay.id,
            employee_id=employee.id,
            current_milage=mileage,
            next_milage=mileage,
            service_status=config.SERVICE_STATUS_VACUUMING if start_now else WAITING,
            payment_method='cash',
            remaining_amount=0,
        )
        _log_status(invoice, previous_log_id=None)
    except Exception:
        db.session.rollback()
        logger.exception("Could not add a vehicle from the floor board")
        flash("The vehicle could not be added. Please try again.", category='danger')
        return _here()

    where = f"into {washbay.name}" if start_now else "to the queue"
    flash(f"{vehicle.number} added {where}.", category='success')
    return _here()
