import json
import logging

from sqlalchemy import func, or_
from flask_login import login_required
from flask import Blueprint, render_template, request, redirect, url_for, flash

from harithmapos import db, config
from harithmapos import settings as app_settings
from harithmapos.billing import invoice_totals, line_amounts, to_decimal
from harithmapos.timeutils import local_today, utcnow
from harithmapos.models import (
    InvoiceHead, InvoiceDetail, ItemInvoiceHead, ItemInvoiceDetail, Customer, Vehicle,
    WashBay, Employee, Item, Payment, InvoiceStatusLog,
)
from harithmapos.views.invoice.forms import (
    InvoiceHeadCreateForm, InvoiceHeadUpdateForm, ItemInvoiceHeadCreateForm,
    ItemInvoiceHeadUpdateForm, InvoiceDetailCreateForm, InvoiceStatusForm,
)
from harithmapos.views.ledger import sync_document_payment
from harithmapos.permissions import owner_required, user_is_owner, OWNER_ONLY_MESSAGE

import harithmapos.views.utils as utils
from utils.database import safe_insert_with_sequence_check

logger = logging.getLogger(__name__)

invoice_blueprint = Blueprint('invoice_blueprint', __name__)

PER_PAGE = 20
GENERAL_CUSTOMER_ID = -1


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------

@invoice_blueprint.route("/app/invoice/head", methods=['GET'])
@login_required
def invoice_head():
    page = request.args.get('page', 1, type=int)
    query = (request.args.get('query') or '').strip()
    status = request.args.get('status', '')

    invoices = InvoiceHead.query
    if query:
        pattern = f"%{query}%"
        conditions = [Vehicle.number.ilike(pattern), Customer.name.ilike(pattern)]
        if query.isdigit():
            conditions.append(InvoiceHead.id == int(query))
        invoices = (
            invoices
            .join(Vehicle, InvoiceHead.vehicle_id == Vehicle.id)
            .join(Customer, InvoiceHead.customer_id == Customer.id)
            .filter(or_(*conditions))
        )
    if status == 'open':
        invoices = invoices.filter(InvoiceHead.service_status < config.SERVICE_STATUS_DONE)
    elif status == 'done':
        invoices = invoices.filter(InvoiceHead.service_status == config.SERVICE_STATUS_DONE)
    elif status == 'unpaid':
        invoices = invoices.filter(
            func.coalesce(InvoiceHead.gross_price, 0) > func.coalesce(InvoiceHead.paid_amount, 0)
        )

    invoice_heads = invoices.order_by(InvoiceHead.id.desc()).paginate(page=page, per_page=PER_PAGE)
    return render_template(
        'invoice/head.html',
        title='Service invoices',
        invoice_heads=invoice_heads,
        query=query,
        status=status,
    )


@invoice_blueprint.route("/app/item_invoice/head", methods=['GET'])
@login_required
def item_invoice_head():
    page = request.args.get('page', 1, type=int)
    query = (request.args.get('query') or '').strip()

    invoices = ItemInvoiceHead.query
    if query:
        conditions = [Customer.name.ilike(f"%{query}%")]
        if query.isdigit():
            conditions.append(ItemInvoiceHead.id == int(query))
        invoices = (
            invoices
            .outerjoin(Customer, ItemInvoiceHead.customer_id == Customer.id)
            .filter(or_(*conditions))
        )

    item_invoice_heads = invoices.order_by(ItemInvoiceHead.id.desc()).paginate(page=page, per_page=PER_PAGE)
    return render_template(
        'invoice/item_head.html',
        title='Item invoices',
        item_invoice_heads=item_invoice_heads,
        query=query,
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@invoice_blueprint.route("/app/invoice/head/create", methods=['GET', 'POST'])
@login_required
def insert_invoice_head():
    form = InvoiceHeadCreateForm()
    if request.method == 'GET':
        washbay = db.session.get(WashBay, request.args.get('washbay_id', type=int) or 0)
        vehicle = db.session.get(Vehicle, request.args.get('vehicle_id', type=int) or 0)
        return render_template(
            'invoice/create.html',
            title='New service invoice',
            washbay=washbay,
            vehicle=vehicle,
        )

    if not form.validate_on_submit():
        utils.flash_form_errors(form)
        return utils.redirect_back('invoice_blueprint.invoice_head')

    vehicle = db.session.get(Vehicle, form.vehicle_id.data)
    employee = db.session.get(Employee, form.employee_id.data)
    washbay = db.session.get(WashBay, form.washbay_id.data)
    if not (vehicle and employee and washbay):
        flash("Choose the vehicle, employee and wash bay from the lists.", category='danger')
        return utils.redirect_back('invoice_blueprint.invoice_head')

    open_invoice = InvoiceHead.query.filter(
        InvoiceHead.vehicle_id == vehicle.id,
        InvoiceHead.service_status < config.SERVICE_STATUS_DONE,
    ).first()
    if open_invoice:
        flash(f"{vehicle.number} already has an open invoice. Here it is.", category='info')
        return redirect(url_for('invoice_blueprint.invoice_head_detail', invoice_head_id=open_invoice.id))

    try:
        invoice = safe_insert_with_sequence_check(
            InvoiceHead,
            customer_id=vehicle.owner_id,
            vehicle_id=vehicle.id,
            washbay_id=washbay.id,
            employee_id=employee.id,
            current_milage=form.current_milage.data,
            next_milage=form.current_milage.data,
            service_status=config.SERVICE_STATUS_WAITING,
            payment_method='cash',
            remaining_amount=0,
        )
        _log_status(invoice, previous_log_id=None)
    except Exception:
        logger.exception("Could not create service invoice")
        flash("The invoice could not be created. Please try again.", category='danger')
        return utils.redirect_back('invoice_blueprint.invoice_head')

    return redirect(url_for('invoice_blueprint.invoice_head_detail', invoice_head_id=invoice.id))


@invoice_blueprint.route("/app/item_invoice/head/create", methods=['GET', 'POST'])
@login_required
def insert_item_invoice_head():
    form = ItemInvoiceHeadCreateForm()
    if request.method == 'GET':
        return render_template('invoice/item_create.html', title='New item invoice')

    if not form.validate_on_submit():
        utils.flash_form_errors(form)
        return utils.redirect_back('invoice_blueprint.item_invoice_head')

    customer = db.session.get(Customer, form.customer_id.data)
    if customer is None:
        flash("Choose the customer from the list.", category='danger')
        return utils.redirect_back('invoice_blueprint.item_invoice_head')

    try:
        item_invoice = safe_insert_with_sequence_check(
            ItemInvoiceHead, customer_id=customer.id, payment_method='cash', remaining_amount=0)
    except Exception:
        logger.exception("Could not create item invoice")
        flash("The invoice could not be created. Please try again.", category='danger')
        return utils.redirect_back('invoice_blueprint.item_invoice_head')
    return redirect(url_for('invoice_blueprint.item_invoice_head_detail', item_invoice_head_id=item_invoice.id))


@invoice_blueprint.route("/app/item_invoice/head/create/quick", methods=['POST'])
@login_required
def create_quick_item_invoice():
    """Start an item invoice for a walk-in customer and go straight to adding items."""
    try:
        general_customer = db.session.get(Customer, GENERAL_CUSTOMER_ID)
        if not general_customer:
            general_customer = safe_insert_with_sequence_check(
                Customer,
                id=GENERAL_CUSTOMER_ID,
                name="General Customer",
                contact=None,
                address="Walk-in customer",
            )
        item_invoice = safe_insert_with_sequence_check(
            ItemInvoiceHead, customer_id=general_customer.id, payment_method='cash', remaining_amount=0)
    except Exception:
        logger.exception("Could not create quick item invoice")
        flash("The invoice could not be created. Please try again.", category='danger')
        return redirect(url_for('dashboard_blueprint.dashboard'))
    return redirect(url_for('invoice_blueprint.item_invoice_head_detail', item_invoice_head_id=item_invoice.id))


# ---------------------------------------------------------------------------
# Service invoice screen
# ---------------------------------------------------------------------------

@invoice_blueprint.route("/app/invoice/head/<int:invoice_head_id>", methods=['GET', 'POST'])
@login_required
def invoice_head_detail(invoice_head_id):
    form = InvoiceHeadUpdateForm()
    invoice_head = InvoiceHead.query.get_or_404(invoice_head_id)
    here = url_for('invoice_blueprint.invoice_head_detail', invoice_head_id=invoice_head.id)

    if request.method == 'POST':
        if not form.validate_on_submit():
            utils.flash_form_errors(form)
            return redirect(here)

        if form.cancel_invoice.data:
            if not user_is_owner():
                flash(OWNER_ONLY_MESSAGE, category='warning')
                return redirect(here)
            if _delete_service_invoice(invoice_head):
                return redirect(url_for('invoice_blueprint.invoice_head'))
            return redirect(here)

        try:
            _save_service_invoice(invoice_head, form)
        except Exception:
            db.session.rollback()
            logger.exception("Could not save service invoice %s", invoice_head_id)
            flash("The invoice could not be saved. Please try again.", category='danger')
            return redirect(here)

        if form.send_service_start_msg.data:
            _notify_customer(invoice_head, started=True)
        elif form.send_service_complete_msg.data:
            _notify_customer(invoice_head, started=False)
        elif form.complete_invoice.data:
            _complete_documents(
                invoice_head, 'invoice_id', convert_service_invoice_to_json,
                f"Invoice #{invoice_head.id} completed.")
            return redirect(url_for('dashboard_blueprint.dashboard'))
        else:
            flash("Invoice saved.", category='success')
        return redirect(here)

    # Recalculate on every view so totals can never drift from the lines.
    invoice_details = _recalculate(invoice_head, InvoiceDetail, InvoiceDetail.invoice_head_id)
    db.session.commit()

    previous_visits = (
        InvoiceHead.query
        .filter(InvoiceHead.vehicle_id == invoice_head.vehicle_id, InvoiceHead.id != invoice_head.id)
        .order_by(InvoiceHead.created_dttm.desc())
        .limit(5)
        .all()
    )
    return render_template(
        'invoice/update.html',
        title=f"Invoice #{invoice_head.id}",
        invoice_head=invoice_head,
        invoice_details=invoice_details,
        previous_visits=previous_visits,
    )


@invoice_blueprint.route("/app/invoice/head/<int:invoice_head_id>/status", methods=['POST'])
@login_required
def set_invoice_status(invoice_head_id):
    """One-tap status change from the dashboard."""
    invoice_head = InvoiceHead.query.get_or_404(invoice_head_id)
    form = InvoiceStatusForm()
    if form.validate_on_submit():
        try:
            changed = _change_status(invoice_head, form.status.data)
            invoice_head.update_dttm = utcnow()
            db.session.commit()
            if changed:
                _log_status(invoice_head)
                flash(f"{invoice_head.vehicle.number} is now {invoice_head.service_status_str.lower()}.",
                      category='success')
        except Exception:
            db.session.rollback()
            logger.exception("Could not change status of invoice %s", invoice_head_id)
            flash("The status could not be changed. Please try again.", category='danger')
    else:
        utils.flash_form_errors(form)
    return utils.redirect_back('dashboard_blueprint.dashboard')


@invoice_blueprint.route("/app/invoice/head/<int:invoice_head_id>/print", methods=['GET'])
@login_required
def print_invoice_head(invoice_head_id):
    invoice_head = InvoiceHead.query.get_or_404(invoice_head_id)
    invoice_details = InvoiceDetail.query.filter(InvoiceDetail.invoice_head_id == invoice_head.id).order_by(InvoiceDetail.id).all()
    return render_template(
        'invoice/print.html',
        title=f"Invoice #{invoice_head.id}",
        kind='service',
        head=invoice_head,
        details=invoice_details,
    )


# ---------------------------------------------------------------------------
# Item invoice screen
# ---------------------------------------------------------------------------

@invoice_blueprint.route("/app/item_invoice/head/<int:item_invoice_head_id>", methods=['GET', 'POST'])
@login_required
def item_invoice_head_detail(item_invoice_head_id):
    form = ItemInvoiceHeadUpdateForm()
    item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_head_id)
    here = url_for('invoice_blueprint.item_invoice_head_detail', item_invoice_head_id=item_invoice_head.id)

    if request.method == 'POST':
        if not form.validate_on_submit():
            utils.flash_form_errors(form)
            return redirect(here)

        try:
            if form.customer_id.data is not None:
                customer = db.session.get(Customer, form.customer_id.data)
                if customer:
                    item_invoice_head.customer_id = customer.id
            item_invoice_head.payment_method = form.payment_method.data
            item_invoice_head.paid_amount = form.paid_amount.data or 0
            item_invoice_head.discount_amount = form.discount_amount.data or 0
            item_invoice_head.update_dttm = utcnow()
            _recalculate(item_invoice_head, ItemInvoiceDetail, ItemInvoiceDetail.item_invoice_head_id)
            if item_invoice_head.paid_amount:
                item_invoice_head.last_payment_date = local_today(config.APP_TIMEZONE)
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("Could not save item invoice %s", item_invoice_head_id)
            flash("The invoice could not be saved. Please try again.", category='danger')
            return redirect(here)

        if form.complete_item_invoice.data:
            _complete_documents(
                item_invoice_head, 'item_invoice_id', convert_item_invoice_to_json,
                f"Item invoice #{item_invoice_head.id} completed.")
            return redirect(url_for('dashboard_blueprint.dashboard'))

        flash("Invoice saved.", category='success')
        return redirect(here)

    item_invoice_details = _recalculate(item_invoice_head, ItemInvoiceDetail, ItemInvoiceDetail.item_invoice_head_id)
    db.session.commit()
    return render_template(
        'invoice/item_update.html',
        title=f"Item invoice #{item_invoice_head.id}",
        item_invoice_head=item_invoice_head,
        item_invoice_details=item_invoice_details,
    )


@invoice_blueprint.route("/app/item_invoice/head/<int:item_invoice_head_id>/print", methods=['GET'])
@login_required
def print_item_invoice_head(item_invoice_head_id):
    item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_head_id)
    details = ItemInvoiceDetail.query.filter(
        ItemInvoiceDetail.item_invoice_head_id == item_invoice_head.id).order_by(ItemInvoiceDetail.id).all()
    return render_template(
        'invoice/print.html',
        title=f"Item invoice #{item_invoice_head.id}",
        kind='item',
        head=item_invoice_head,
        details=details,
    )


# ---------------------------------------------------------------------------
# Delete (POST only: a link that deletes can be triggered by accident)
# ---------------------------------------------------------------------------

@invoice_blueprint.route('/app/invoice/head/<int:invoice_head_id>/delete', methods=['POST'])
@owner_required
def delete_invoice_head(invoice_head_id):
    invoice_head = InvoiceHead.query.get_or_404(invoice_head_id)
    _delete_service_invoice(invoice_head)
    return redirect(url_for('invoice_blueprint.invoice_head'))


@invoice_blueprint.route('/app/item_invoice/head/<int:item_invoice_head_id>/delete', methods=['POST'])
@owner_required
def delete_item_invoice_head(item_invoice_head_id):
    item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_head_id)
    if Payment.query.filter(Payment.item_invoice_id == item_invoice_head.id).count():
        flash("This invoice has payments recorded against it. Delete those on the Payments page first.",
              category='warning')
        return redirect(url_for('invoice_blueprint.item_invoice_head_detail', item_invoice_head_id=item_invoice_head.id))
    try:
        details = ItemInvoiceDetail.query.filter(ItemInvoiceDetail.item_invoice_head_id == item_invoice_head.id).all()
        _return_lines_to_stock(details)
        db.session.delete(item_invoice_head)
        db.session.commit()
        flash("Item invoice deleted and its items returned to stock.", category='warning')
    except Exception:
        db.session.rollback()
        logger.exception("Could not delete item invoice %s", item_invoice_head_id)
        flash("The invoice could not be deleted.", category='danger')
    return redirect(url_for('invoice_blueprint.item_invoice_head'))


# ---------------------------------------------------------------------------
# Lines
# ---------------------------------------------------------------------------

@invoice_blueprint.route("/app/invoice/detail/add/<int:invoice_head_id>", methods=['POST'])
@login_required
def add_invoice_detail(invoice_head_id):
    invoice_head = InvoiceHead.query.get_or_404(invoice_head_id)
    _add_line(invoice_head, InvoiceDetail, 'invoice_head_id', InvoiceDetail.invoice_head_id)
    return redirect(url_for('invoice_blueprint.invoice_head_detail', invoice_head_id=invoice_head_id))


@invoice_blueprint.route("/app/item_invoice/detail/add/<int:item_invoice_head_id>", methods=['POST'])
@login_required
def add_item_invoice_detail(item_invoice_head_id):
    item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_head_id)
    _add_line(item_invoice_head, ItemInvoiceDetail, 'item_invoice_head_id', ItemInvoiceDetail.item_invoice_head_id)
    return redirect(url_for('invoice_blueprint.item_invoice_head_detail', item_invoice_head_id=item_invoice_head_id))


@invoice_blueprint.route("/app/invoice/detail/delete/<int:invoice_detail_id>", methods=['POST'])
@login_required
def delete_invoice_detail(invoice_detail_id):
    invoice_detail = InvoiceDetail.query.get_or_404(invoice_detail_id)
    invoice_head = InvoiceHead.query.get_or_404(invoice_detail.invoice_head_id)
    _remove_line(invoice_head, invoice_detail, InvoiceDetail, InvoiceDetail.invoice_head_id)
    return redirect(url_for('invoice_blueprint.invoice_head_detail', invoice_head_id=invoice_head.id))


@invoice_blueprint.route("/app/item_invoice/detail/delete/<int:item_invoice_detail_id>", methods=['POST'])
@login_required
def delete_item_invoice_detail(item_invoice_detail_id):
    item_invoice_detail = ItemInvoiceDetail.query.get_or_404(item_invoice_detail_id)
    item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_detail.item_invoice_head_id)
    _remove_line(item_invoice_head, item_invoice_detail, ItemInvoiceDetail, ItemInvoiceDetail.item_invoice_head_id)
    return redirect(url_for('invoice_blueprint.item_invoice_head_detail', item_invoice_head_id=item_invoice_head.id))


@invoice_blueprint.route("/app/invoice/detail/quantity/add/<int:invoice_detail_id>", methods=['POST'])
@login_required
def increase_quantity_invoice_detail(invoice_detail_id):
    invoice_detail = InvoiceDetail.query.get_or_404(invoice_detail_id)
    invoice_head = InvoiceHead.query.get_or_404(invoice_detail.invoice_head_id)
    _change_line_quantity(invoice_head, invoice_detail, 1, InvoiceDetail, InvoiceDetail.invoice_head_id)
    return redirect(url_for('invoice_blueprint.invoice_head_detail', invoice_head_id=invoice_head.id))


@invoice_blueprint.route("/app/item_invoice/detail/quantity/add/<int:item_invoice_detail_id>", methods=['POST'])
@login_required
def increase_quantity_item_invoice_detail(item_invoice_detail_id):
    item_invoice_detail = ItemInvoiceDetail.query.get_or_404(item_invoice_detail_id)
    item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_detail.item_invoice_head_id)
    _change_line_quantity(item_invoice_head, item_invoice_detail, 1, ItemInvoiceDetail, ItemInvoiceDetail.item_invoice_head_id)
    return redirect(url_for('invoice_blueprint.item_invoice_head_detail', item_invoice_head_id=item_invoice_head.id))


@invoice_blueprint.route("/app/invoice/detail/quantity/remove/<int:invoice_detail_id>", methods=['POST'])
@login_required
def decrease_quantity_invoice_detail(invoice_detail_id):
    invoice_detail = InvoiceDetail.query.get_or_404(invoice_detail_id)
    invoice_head = InvoiceHead.query.get_or_404(invoice_detail.invoice_head_id)
    _change_line_quantity(invoice_head, invoice_detail, -1, InvoiceDetail, InvoiceDetail.invoice_head_id)
    return redirect(url_for('invoice_blueprint.invoice_head_detail', invoice_head_id=invoice_head.id))


@invoice_blueprint.route("/app/item_invoice/detail/quantity/remove/<int:item_invoice_detail_id>", methods=['POST'])
@login_required
def decrease_quantity_item_invoice_detail(item_invoice_detail_id):
    item_invoice_detail = ItemInvoiceDetail.query.get_or_404(item_invoice_detail_id)
    item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_detail.item_invoice_head_id)
    _change_line_quantity(item_invoice_head, item_invoice_detail, -1, ItemInvoiceDetail, ItemInvoiceDetail.item_invoice_head_id)
    return redirect(url_for('invoice_blueprint.item_invoice_head_detail', item_invoice_head_id=item_invoice_head.id))


# ---------------------------------------------------------------------------
# Supporting functions
# ---------------------------------------------------------------------------

def _recalculate(head, detail_model, head_column):
    """Recompute the head totals from its lines. Returns the lines. Does not commit."""
    details = detail_model.query.filter(head_column == head.id).order_by(detail_model.id).all()
    totals = invoice_totals(details, bill_discount=head.discount_amount, paid=head.paid_amount)
    head.total_cost = totals['total_cost']
    head.total_price = totals['total_price']
    head.total_discount = totals['total_discount']
    head.discount_amount = totals['discount_amount']
    head.gross_price = totals['gross_price']
    head.remaining_amount = totals['remaining_amount']
    return details


def update_total_values(invoice_head):
    """Recompute and save the totals of a service or item invoice."""
    if isinstance(invoice_head, InvoiceHead):
        _recalculate(invoice_head, InvoiceDetail, InvoiceDetail.invoice_head_id)
    else:
        _recalculate(invoice_head, ItemInvoiceDetail, ItemInvoiceDetail.item_invoice_head_id)
    db.session.commit()


def _set_line_amounts(detail, extra_discount=None):
    """Fill a line's cost / price / discount columns from its item and quantity."""
    if extra_discount is None:
        extra_discount = detail.additional_discount
    amounts = line_amounts(
        detail.quantity, detail.item.unit_cost, detail.item.unit_price,
        detail.item.discount_pct, extra_discount)
    detail.total_cost = amounts['total_cost']
    detail.total_price = amounts['total_price']
    detail.discount_amount = amounts['discount_amount']
    detail.additional_discount = amounts['additional_discount']
    detail.gross_price = amounts['gross_price']


def _add_line(head, detail_model, head_field, head_column):
    form = InvoiceDetailCreateForm()
    if not form.validate_on_submit():
        utils.flash_form_errors(form)
        return False

    item = db.session.get(Item, form.item_id.data)
    if item is None:
        flash("Choose the item from the list.", category='danger')
        return False

    quantity = form.quantity.data
    if item.tracks_stock and item.quantity < quantity:
        flash(f"Not enough stock of {item.name}: {_qty_text(item.quantity)} left, {_qty_text(quantity)} asked for.",
              category='danger')
        return False

    try:
        amounts = line_amounts(quantity, item.unit_cost, item.unit_price, item.discount_pct, form.discount_amount.data)
        detail = detail_model(item_id=item.id, quantity=quantity, **amounts)
        setattr(detail, head_field, head.id)
        db.session.add(detail)
        if item.tracks_stock:
            item.quantity = item.quantity - quantity
        db.session.flush()
        _recalculate(head, detail_model, head_column)
        head.update_dttm = utcnow()
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Could not add an item to an invoice")
        flash("The item could not be added. Please try again.", category='danger')
        return False
    return True


def _remove_line(head, detail, detail_model, head_column):
    try:
        item = detail.item
        if item is not None and item.tracks_stock:
            item.quantity = item.quantity + detail.quantity
        db.session.delete(detail)
        db.session.flush()
        _recalculate(head, detail_model, head_column)
        head.update_dttm = utcnow()
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Could not remove an invoice line")
        flash("The item could not be removed. Please try again.", category='danger')
        return False
    return True


def _change_line_quantity(head, detail, step, detail_model, head_column):
    item = detail.item
    if step < 0 and detail.quantity <= 1:
        flash("Quantity is already at the minimum. Remove the item instead.", category='warning')
        return False
    if step > 0 and item.tracks_stock and item.quantity < step:
        flash(f"No more {item.name} in stock.", category='danger')
        return False
    try:
        if item.tracks_stock:
            item.quantity = item.quantity - step
        detail.quantity = detail.quantity + step
        detail.update_dttm = utcnow()
        _set_line_amounts(detail)
        db.session.flush()
        _recalculate(head, detail_model, head_column)
        head.update_dttm = utcnow()
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Could not change an invoice line quantity")
        flash("The quantity could not be changed. Please try again.", category='danger')
        return False
    return True


def update_invoice_detail_values(invoice_detail):
    """Recompute and save one line after its quantity changed."""
    _set_line_amounts(invoice_detail)
    db.session.commit()


def _return_lines_to_stock(details):
    """Put the quantities of deleted lines back on the shelf, then delete the lines."""
    for detail in details:
        item = detail.item
        if item is not None and item.tracks_stock:
            item.quantity = item.quantity + detail.quantity
        db.session.delete(detail)


def _latest_status_log_id(invoice_head):
    latest = (
        InvoiceStatusLog.query
        .filter(InvoiceStatusLog.invoice_id == invoice_head.id)
        .order_by(InvoiceStatusLog.id.desc())
        .first()
    )
    return latest.id if latest else None


def _log_status(invoice_head, previous_log_id='lookup'):
    """Write a status history row. Runs in its own transaction and never raises."""
    try:
        if previous_log_id == 'lookup':
            previous_log_id = _latest_status_log_id(invoice_head)
        safe_insert_with_sequence_check(
            InvoiceStatusLog,
            previous_invoice_status_log_id=previous_log_id,
            invoice_id=invoice_head.id,
            service_status=invoice_head.service_status,
            employee_id=invoice_head.employee_id,
        )
    except Exception:
        logger.exception("Could not write status log for invoice %s", invoice_head.id)


def _change_status(invoice_head, new_status):
    """Set the status. Returns True if it actually changed. Does not commit."""
    if new_status is None:
        return False
    new_status = int(new_status)
    if new_status == (invoice_head.service_status or 0):
        return False
    invoice_head.service_status = new_status
    return True


def _save_service_invoice(invoice_head, form):
    """Apply the right-hand panel of the service invoice screen and commit."""
    if form.employee_id.data is not None:
        employee = db.session.get(Employee, form.employee_id.data)
        if employee:
            invoice_head.employee_id = employee.id
    if form.washbay_id.data is not None:
        washbay = db.session.get(WashBay, form.washbay_id.data)
        if washbay:
            invoice_head.washbay_id = washbay.id

    current = form.current_milage.data
    interval = form.next_milage_in.data
    invoice_head.current_milage = current
    invoice_head.next_milage_in = interval
    if current is not None and interval:
        invoice_head.next_milage = current + interval
    else:
        invoice_head.next_milage = current

    invoice_head.payment_method = form.payment_method.data
    invoice_head.paid_amount = form.paid_amount.data or 0
    invoice_head.discount_amount = form.discount_amount.data or 0
    invoice_head.update_dttm = utcnow()

    new_status = config.SERVICE_STATUS_DONE if form.complete_invoice.data else form.service_status.data
    status_changed = _change_status(invoice_head, new_status)

    _recalculate(invoice_head, InvoiceDetail, InvoiceDetail.invoice_head_id)
    if invoice_head.paid_amount:
        invoice_head.last_payment_date = local_today(config.APP_TIMEZONE)
    db.session.commit()

    if status_changed:
        _log_status(invoice_head)


def _complete_documents(head, link_field, to_json, success_message):
    """After a successful save: record the payment and queue the receipt."""
    try:
        sync_document_payment(head, link_field)
    except Exception:
        db.session.rollback()
        logger.exception("Could not record payment for %s %s", link_field, head.id)
        flash("The invoice is saved, but its payment could not be recorded. Press Complete again.",
              category='danger')
        return

    if not utils.printer_enabled():
        flash(f"{success_message} Use Print on the invoice screen for a receipt.", category='success')
        return

    printed = False
    try:
        printed = utils.send_print_invoice(to_json(head))
    except Exception:
        logger.exception("Could not build the receipt for %s %s", link_field, head.id)

    if printed:
        flash(success_message, category='success')
    else:
        flash(f"{success_message} The receipt printer could not be reached: "
              "use Print on the invoice screen instead.", category='warning')


def _notify_customer(invoice_head, started):
    """Send the 'service started' or 'service completed' SMS and remember that it went out."""
    customer = invoice_head.vehicle.owner
    token = invoice_head.get_customer_view_token()
    link = url_for('dashboard_blueprint.customer_invoice', token=token, _external=True)
    template = app_settings.get('sms_start_message' if started else 'sms_done_message')
    try:
        message = app_settings.render_sms(
            template, customer=customer.name, vehicle=invoice_head.vehicle.number,
            business=app_settings.get('business_name'), link=link)
    except (KeyError, ValueError, IndexError):
        flash("The SMS text in Settings has a mistake in it. Ask an owner to fix it.", category='danger')
        return False

    try:
        utils.send_sms(customer.contact, message, raise_errors=True)
    except utils.ServiceError as exc:
        flash(f"The SMS could not be sent. {exc}", category='danger')
        return False

    if started:
        invoice_head.service_start_msg_sent_ind = True
    else:
        invoice_head.service_complete_msg_sent_ind = True
    db.session.commit()
    flash(f"SMS sent to {customer.name}.", category='success')
    return True


def _delete_service_invoice(invoice_head):
    """Delete a service invoice, returning its items to stock. Returns True on success."""
    if Payment.query.filter(Payment.invoice_id == invoice_head.id).count():
        flash("This invoice has payments recorded against it. Delete those on the Payments page first.",
              category='warning')
        return False
    try:
        details = InvoiceDetail.query.filter(InvoiceDetail.invoice_head_id == invoice_head.id).all()
        _return_lines_to_stock(details)
        InvoiceStatusLog.query.filter(InvoiceStatusLog.invoice_id == invoice_head.id).delete(synchronize_session=False)
        db.session.delete(invoice_head)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Could not delete service invoice %s", invoice_head.id)
        flash("The invoice could not be deleted.", category='danger')
        return False
    flash("Invoice deleted and its items returned to stock.", category='warning')
    return True


def _qty_text(value):
    """Quantity without trailing zeros, for messages."""
    text = f"{to_decimal(value):f}"
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text or '0'


def convert_item_invoice_to_json(item_invoice):
    invoice_dictionary = {
        "invoice_number": item_invoice.id,
        "invoice_type": 2,
        "total_price": item_invoice.total_price,
        "discount_amount": item_invoice.discount_amount,
        "gross_price": item_invoice.gross_price,
        "paid_amount": item_invoice.paid_amount,
        "invoice_details": []
    }

    for detail in item_invoice.invoice_details:
        item_detail = {
            'item_name': detail.item.name,
            'unit_price': detail.item.unit_price,
            'quantity': detail.quantity,
            'total_price': detail.total_price,
            'discount_pct': detail.item.discount_pct
        }
        invoice_dictionary['invoice_details'].append(item_detail)

    return json.dumps(invoice_dictionary, cls=utils.DecimalEncoder)


def convert_service_invoice_to_json(service_invoice):
    invoice_dictionary = {
        "invoice_number": service_invoice.id,
        "invoice_type": 1,
        "customer_name": service_invoice.customer.name,
        "employee_name": service_invoice.employee.name,
        "vehicle_number": service_invoice.vehicle.number,
        "wash_bay": service_invoice.washbay.name,
        "current_milage": service_invoice.current_milage,
        "next_milage": service_invoice.next_milage,
        "total_price": service_invoice.total_price,
        "total_discount": service_invoice.total_discount,
        "gross_price": service_invoice.gross_price,
        "paid_amount": service_invoice.paid_amount,
        "invoice_details": []
    }

    for detail in service_invoice.invoice_details:
        item_detail = {
            'item_name': detail.item.name,
            'unit_price': detail.item.unit_price,
            'quantity': detail.quantity,
            'total_price': detail.total_price
        }
        invoice_dictionary['invoice_details'].append(item_detail)

    return json.dumps(invoice_dictionary, cls=utils.DecimalEncoder)
