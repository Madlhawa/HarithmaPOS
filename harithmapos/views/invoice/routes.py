import logging

from sqlalchemy import func, or_
from flask_login import current_user, login_required
from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from harithmapos import db, config
from harithmapos import settings as app_settings
from harithmapos import job_requests
from harithmapos.billing import money
from harithmapos.timeutils import utcnow
from harithmapos.models import DOC_COMPLETED, DOC_DRAFT, DOC_VOID
from harithmapos.models import (
    InvoiceHead, InvoiceDetail, ItemInvoiceHead, ItemInvoiceDetail, Customer, Vehicle,
    WashBay, Employee, Item, InvoiceRequest,
)
from harithmapos.views.invoice.forms import (
    InvoiceHeadCreateForm, InvoiceHeadUpdateForm, ItemInvoiceHeadCreateForm,
    ItemInvoiceHeadUpdateForm, InvoiceDetailCreateForm, InvoiceStatusForm,
)
from harithmapos import documents, job_status, ledger, lines, stock
from harithmapos.permissions import owner_required

import harithmapos.views.utils as utils

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
    done = config.SERVICE_STATUS_DONE
    if status == 'open':        # job still on the floor
        invoices = invoices.filter(InvoiceHead.doc_status == DOC_DRAFT, InvoiceHead.service_status < done)
    elif status == 'tobill':    # job finished, bill not completed yet
        invoices = invoices.filter(InvoiceHead.doc_status == DOC_DRAFT, InvoiceHead.service_status == done)
    elif status == 'done':
        invoices = invoices.filter(InvoiceHead.doc_status == DOC_COMPLETED)
    elif status == 'unpaid':
        invoices = invoices.filter(
            InvoiceHead.doc_status == DOC_COMPLETED,
            func.coalesce(InvoiceHead.gross_price, 0) > func.coalesce(InvoiceHead.paid_amount, 0),
        )
    elif status == 'void':
        invoices = invoices.filter(InvoiceHead.doc_status == DOC_VOID)

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
    employee = db.session.get(Employee, form.employee_id.data) if form.employee_id.data else None
    washbay = db.session.get(WashBay, form.washbay_id.data) if form.washbay_id.data else None
    if not vehicle:
        flash("Choose the vehicle from the list.", category='danger')
        return utils.redirect_back('invoice_blueprint.invoice_head')

    open_invoice = InvoiceHead.query.filter(
        InvoiceHead.vehicle_id == vehicle.id,
        InvoiceHead.is_live,
        InvoiceHead.service_status < config.SERVICE_STATUS_DONE,
    ).first()
    if open_invoice:
        flash(f"{vehicle.number} already has an open invoice. Here it is.", category='info')
        return redirect(url_for('invoice_blueprint.invoice_head_detail', invoice_head_id=open_invoice.id))

    try:
        invoice = InvoiceHead(
            customer_id=vehicle.owner_id,
            vehicle_id=vehicle.id,
            washbay_id=washbay.id if washbay else None,
            employee_id=employee.id if employee else None,
            current_milage=form.current_milage.data,
            next_milage=form.current_milage.data,
            service_status=config.SERVICE_STATUS_WAITING,
        )
        db.session.add(invoice)
        db.session.commit()
        job_status.log(invoice, previous_log_id=None)
    except Exception:
        db.session.rollback()
        logger.exception("Could not create service invoice")
        flash("The invoice could not be created. Please try again.", category='danger')
        return utils.redirect_back('invoice_blueprint.invoice_head')
    save_start_requests(invoice)

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
        item_invoice = ItemInvoiceHead(customer_id=customer.id)
        db.session.add(item_invoice)
        db.session.commit()
    except Exception:
        db.session.rollback()
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
            # A fixed negative id, so it can never clash with the id sequence.
            general_customer = Customer(
                id=GENERAL_CUSTOMER_ID,
                name="General Customer",
                contact=None,
                address="Walk-in customer",
            )
            db.session.add(general_customer)
        item_invoice = ItemInvoiceHead(customer_id=GENERAL_CUSTOMER_ID)
        db.session.add(item_invoice)
        db.session.commit()
    except Exception:
        db.session.rollback()
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

        if invoice_head.is_void:
            flash(f"Invoice #{invoice_head.id} is void and cannot be changed.", category='warning')
            return redirect(here)

        try:
            _save_service_invoice(invoice_head, form)
        except job_status.JobError as exc:
            db.session.rollback()
            flash(str(exc), category='warning')
            return redirect(here)
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
            if not _complete(invoice_head):
                return redirect(here)
            _complete_documents(
                invoice_head, form,
                url_for('invoice_blueprint.print_invoice_head', invoice_head_id=invoice_head.id),
                f"Invoice #{invoice_head.id} completed.")
            return redirect(url_for('dashboard_blueprint.dashboard'))
        else:
            _saved_message(form)
        return redirect(here)

    # A draft is recalculated on every view so its totals can never drift from the lines;
    # a completed or void bill is fixed.
    if invoice_head.is_draft:
        invoice_details = lines.recalculate(invoice_head)
        db.session.commit()
    else:
        invoice_details = documents.lines_of(invoice_head)

    previous_visits = (
        InvoiceHead.query
        .filter(InvoiceHead.vehicle_id == invoice_head.vehicle_id, InvoiceHead.id != invoice_head.id,
                InvoiceHead.is_live)
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
    if not invoice_head.is_draft:
        flash(f"Invoice #{invoice_head.id} is {invoice_head.status_label.lower()}: its job can no longer move.",
              category='warning')
    elif form.validate_on_submit():
        try:
            changed = job_status.change(invoice_head, form.status.data)
            invoice_head.update_dttm = utcnow()
            db.session.commit()
            if changed:
                job_status.log(invoice_head)
                flash(f"{invoice_head.vehicle.number} is now {invoice_head.service_status_str.lower()}.",
                      category='success')
        except job_status.JobError as exc:
            db.session.rollback()
            flash(f"{exc} Open the invoice to choose.", category='warning')
        except Exception:
            db.session.rollback()
            logger.exception("Could not change status of invoice %s", invoice_head_id)
            flash("The status could not be changed. Please try again.", category='danger')
    else:
        utils.flash_form_errors(form)
    return utils.redirect_back('dashboard_blueprint.dashboard')


# ---------------------------------------------------------------------------
# What the customer asked for (a checklist on the service invoice)
# ---------------------------------------------------------------------------

def save_start_requests(invoice):
    """Store what the customer asked for, typed when the job was started. Never raises."""
    try:
        if job_requests.add(invoice, request.form.get('requests'), current_user):
            db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Could not save the requests for invoice %s", invoice.id)
        flash("The job was started, but the customer's requests were not saved. Add them on the invoice.",
              category='warning')


def _back_to_invoice(invoice_id):
    return utils.redirect_back('invoice_blueprint.invoice_head_detail', invoice_head_id=invoice_id)


@invoice_blueprint.route("/app/invoice/head/<int:invoice_head_id>/requests", methods=['POST'])
@login_required
def add_invoice_requests(invoice_head_id):
    invoice = db.get_or_404(InvoiceHead, invoice_head_id)
    try:
        added = job_requests.add(invoice, request.form.get('requests'), current_user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Could not add requests to invoice %s", invoice_head_id)
        flash("The request was not saved. Please try again.", category='danger')
        return _back_to_invoice(invoice_head_id)
    if not added:
        flash("Type what the customer asked for first (or it is already on the list).", category='warning')
    return _back_to_invoice(invoice_head_id)


@invoice_blueprint.route("/app/invoice/request/<int:request_id>/done", methods=['POST'])
@login_required
def tick_invoice_request(request_id):
    item = db.get_or_404(InvoiceRequest, request_id)
    job_requests.set_done(item, request.form.get('done') == '1', current_user)
    db.session.commit()
    return _back_to_invoice(item.invoice_id)


@invoice_blueprint.route("/app/invoice/request/<int:request_id>/delete", methods=['POST'])
@login_required
def delete_invoice_request(request_id):
    item = db.get_or_404(InvoiceRequest, request_id)
    invoice_id = item.invoice_id
    db.session.delete(item)
    db.session.commit()
    return _back_to_invoice(invoice_id)


@invoice_blueprint.route("/app/invoice/head/<int:invoice_head_id>/print", methods=['GET'])
@login_required
def print_invoice_head(invoice_head_id):
    invoice_head = InvoiceHead.query.get_or_404(invoice_head_id)
    invoice_details = InvoiceDetail.query.filter(InvoiceDetail.invoice_head_id == invoice_head.id).order_by(InvoiceDetail.id).all()
    return render_template(
        'invoice/print_service.html',
        title=f"Invoice #{invoice_head.id}",
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

        if not item_invoice_head.is_draft:
            # Nothing on a completed or void sale's bill can change; money is taken with Record payment.
            flash(f"Item sale #{item_invoice_head.id} is {item_invoice_head.status_label.lower()}, "
                  "so it cannot be changed.", category='warning')
            return redirect(here)

        try:
            if form.customer_id.data is not None:
                customer = db.session.get(Customer, form.customer_id.data)
                if customer:
                    item_invoice_head.customer_id = customer.id
            item_invoice_head.discount_amount = form.discount_amount.data or 0
            item_invoice_head.update_dttm = utcnow()
            lines.recalculate(item_invoice_head)
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("Could not save item invoice %s", item_invoice_head_id)
            flash("The invoice could not be saved. Please try again.", category='danger')
            return redirect(here)

        if form.complete_item_invoice.data:
            if not _complete(item_invoice_head):
                return redirect(here)
            _complete_documents(
                item_invoice_head, form,
                url_for('invoice_blueprint.print_item_invoice_head', item_invoice_head_id=item_invoice_head.id),
                f"Item invoice #{item_invoice_head.id} completed.")
            return redirect(url_for('dashboard_blueprint.dashboard'))

        _saved_message(form)
        return redirect(here)

    if item_invoice_head.is_draft:
        item_invoice_details = lines.recalculate(item_invoice_head)
        db.session.commit()
    else:
        item_invoice_details = documents.lines_of(item_invoice_head)
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
        'invoice/print_receipt.html',
        title=f"Item invoice #{item_invoice_head.id}",
        kind='item',
        head=item_invoice_head,
        details=details,
    )


# ---------------------------------------------------------------------------
# Void (owners): nothing is deleted; the document stays, marked void, and its stock goes back
# ---------------------------------------------------------------------------

def _void(document, here, back):
    try:
        documents.void(document, request.form.get('reason'), current_user)
        db.session.commit()
    except documents.DocumentError as exc:
        db.session.rollback()
        flash(str(exc), category='warning')
        return redirect(here)
    except Exception:
        db.session.rollback()
        logger.exception("Could not void %s", documents.label(document))
        flash("It could not be voided. Please try again.", category='danger')
        return redirect(here)
    flash(f"{documents.label(document)} is void. Its items are back in stock.", category='warning')
    return redirect(here)


@invoice_blueprint.route('/app/invoice/head/<int:invoice_head_id>/void', methods=['POST'])
@owner_required
def void_invoice_head(invoice_head_id):
    invoice_head = db.get_or_404(InvoiceHead, invoice_head_id)
    return _void(invoice_head, url_for('invoice_blueprint.invoice_head_detail', invoice_head_id=invoice_head.id),
                 url_for('invoice_blueprint.invoice_head'))


@invoice_blueprint.route('/app/item_invoice/head/<int:item_invoice_head_id>/void', methods=['POST'])
@owner_required
def void_item_invoice_head(item_invoice_head_id):
    sale = db.get_or_404(ItemInvoiceHead, item_invoice_head_id)
    return _void(sale, url_for('invoice_blueprint.item_invoice_head_detail', item_invoice_head_id=sale.id),
                 url_for('invoice_blueprint.item_invoice_head'))


# ---------------------------------------------------------------------------
# Lines (the rules are in harithmapos/lines.py; these read the form and report)
# ---------------------------------------------------------------------------

def _invoice_page(head):
    if isinstance(head, InvoiceHead):
        return redirect(url_for('invoice_blueprint.invoice_head_detail', invoice_head_id=head.id))
    return redirect(url_for('invoice_blueprint.item_invoice_head_detail', item_invoice_head_id=head.id))


def _apply(head, change, failure):
    """Run one change to the lines and commit, or roll back and say why."""
    try:
        change()
        db.session.commit()
    except (documents.DocumentError, stock.StockError) as exc:
        db.session.rollback()
        flash(str(exc), category='warning')
    except Exception:
        db.session.rollback()
        logger.exception("%s: %s", documents.label(head), failure)
        flash(f"{failure} Please try again.", category='danger')
    return _invoice_page(head)


def _add_line(head):
    form = InvoiceDetailCreateForm()
    if not form.validate_on_submit():
        utils.flash_form_errors(form)
        return _invoice_page(head)
    item = db.session.get(Item, form.item_id.data)
    if item is None:
        flash("Choose the item from the list.", category='danger')
        return _invoice_page(head)
    return _apply(head, lambda: lines.add_sale_line(head, item, form.quantity.data, form.discount_amount.data),
                  "The item could not be added.")


@invoice_blueprint.route("/app/invoice/detail/add/<int:invoice_head_id>", methods=['POST'])
@login_required
def add_invoice_detail(invoice_head_id):
    return _add_line(db.get_or_404(InvoiceHead, invoice_head_id))


@invoice_blueprint.route("/app/item_invoice/detail/add/<int:item_invoice_head_id>", methods=['POST'])
@login_required
def add_item_invoice_detail(item_invoice_head_id):
    return _add_line(db.get_or_404(ItemInvoiceHead, item_invoice_head_id))


def _remove_line(line_model, line_id):
    line = db.get_or_404(line_model, line_id)
    head = lines.head_of(line)
    return _apply(head, lambda: lines.remove_line(head, line), "The item could not be removed.")


def _step_line(line_model, line_id, step):
    line = db.get_or_404(line_model, line_id)
    head = lines.head_of(line)
    return _apply(head, lambda: lines.change_quantity(head, line, step), "The quantity could not be changed.")


@invoice_blueprint.route("/app/invoice/detail/delete/<int:invoice_detail_id>", methods=['POST'])
@login_required
def delete_invoice_detail(invoice_detail_id):
    return _remove_line(InvoiceDetail, invoice_detail_id)


@invoice_blueprint.route("/app/item_invoice/detail/delete/<int:item_invoice_detail_id>", methods=['POST'])
@login_required
def delete_item_invoice_detail(item_invoice_detail_id):
    return _remove_line(ItemInvoiceDetail, item_invoice_detail_id)


@invoice_blueprint.route("/app/invoice/detail/quantity/add/<int:invoice_detail_id>", methods=['POST'])
@login_required
def increase_quantity_invoice_detail(invoice_detail_id):
    return _step_line(InvoiceDetail, invoice_detail_id, 1)


@invoice_blueprint.route("/app/item_invoice/detail/quantity/add/<int:item_invoice_detail_id>", methods=['POST'])
@login_required
def increase_quantity_item_invoice_detail(item_invoice_detail_id):
    return _step_line(ItemInvoiceDetail, item_invoice_detail_id, 1)


@invoice_blueprint.route("/app/invoice/detail/quantity/remove/<int:invoice_detail_id>", methods=['POST'])
@login_required
def decrease_quantity_invoice_detail(invoice_detail_id):
    return _step_line(InvoiceDetail, invoice_detail_id, -1)


@invoice_blueprint.route("/app/item_invoice/detail/quantity/remove/<int:item_invoice_detail_id>", methods=['POST'])
@login_required
def decrease_quantity_item_invoice_detail(item_invoice_detail_id):
    return _step_line(ItemInvoiceDetail, item_invoice_detail_id, -1)


# ---------------------------------------------------------------------------
# Supporting functions
# ---------------------------------------------------------------------------

def _complete(head):
    """Draft -> completed (and the job Done). Returns False, with a message, if it cannot be."""
    try:
        job_done = documents.complete(head, current_user)
        db.session.commit()
    except documents.DocumentError as exc:
        db.session.rollback()
        flash(str(exc), category='warning')
        return False
    if job_done:
        job_status.log(head)
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

    invoice_head.update_dttm = utcnow()
    status_changed = False
    if invoice_head.is_draft:
        # The bill is still open: its discount can change, and the job can move between stages.
        invoice_head.discount_amount = form.discount_amount.data or 0
        if not form.complete_invoice.data:
            status_changed = job_status.change(invoice_head, form.service_status.data)
        lines.recalculate(invoice_head)
    db.session.commit()

    if status_changed:
        job_status.log(invoice_head)


def _complete_documents(head, form, print_url, success_message):
    """After a successful save: record the money handed over, then open the print window on the next page."""
    method = form.payment_method.data if form.payment_method.data in ledger.METHODS else 'cash'
    try:
        entry, change = ledger.take_on_completion(head, form.received_amount.data or 0, method, current_user)
        db.session.commit()
    except ledger.LedgerError as exc:
        db.session.rollback()
        flash(f"{success_message} The payment was not recorded: {exc} Use Record payment on the bill.", category='warning')
        return
    except Exception:
        db.session.rollback()
        logger.exception("Could not record the payment for %s #%s", type(head).__name__, head.id)
        flash(f"{success_message} The payment could not be recorded: use Record payment on the bill.",
              category='danger')
        return

    message = success_message
    if change > 0:
        message += f" Give back {config.CURRENCY} {change:,.2f} change."
    if head.balance > 0:
        message += f" Still to pay: {config.CURRENCY} {money(head.balance):,.2f}."
    flash(message, category='success')
    if app_settings.get('print_on_complete'):
        session['print_after'] = print_url


def _saved_message(form):
    """Save does not take money: say so if an amount was typed."""
    if form.received_amount.data:
        flash("Saved. The amount received is recorded only when you press Complete.", category='info')
    else:
        flash("Invoice saved.", category='success')


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
