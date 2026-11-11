from sqlalchemy import and_, func, or_
from flask_login import login_required
from flask import Blueprint, render_template, request

from harithmapos import db, config
from harithmapos.timeutils import local_day_bounds_utc
from harithmapos.models import (
    Employee, InvoiceHead, InvoiceDetail, InvoiceStatusLog, Item, Payment, Vehicle, WashBay,
)
from harithmapos.template_helpers import SERVICE_STATUS_META

dashboard_blueprint = Blueprint('dashboard_blueprint', __name__)


@dashboard_blueprint.route('/app/dashboard')
@login_required
def dashboard():
    done = config.SERVICE_STATUS_DONE
    day_start, day_end = local_day_bounds_utc(tz_name=config.APP_TIMEZONE)

    # Every vehicle still in the station, oldest first.
    open_invoices = (
        InvoiceHead.query
        .filter(InvoiceHead.service_status < done)
        .order_by(InvoiceHead.created_dttm)
        .all()
    )

    # Finished today (by the shop's calendar day, not the server's).
    finished_today = InvoiceHead.invoice_statuses.any(and_(
        InvoiceStatusLog.service_status == done,
        InvoiceStatusLog.created_dttm >= day_start,
        InvoiceStatusLog.created_dttm < day_end,
    ))
    created_today = and_(InvoiceHead.created_dttm >= day_start, InvoiceHead.created_dttm < day_end)
    done_invoices = (
        InvoiceHead.query
        .filter(InvoiceHead.service_status == done, or_(finished_today, created_today))
        .order_by(InvoiceHead.update_dttm.desc())
        .all()
    )

    lanes = []
    for meta in SERVICE_STATUS_META:
        if meta['id'] == done:
            invoices = done_invoices
        else:
            invoices = [invoice for invoice in open_invoices if (invoice.service_status or 0) == meta['id']]
        lanes.append({'status': meta, 'invoices': invoices})

    # Which vehicle is physically in each bay right now.
    in_bay = {}
    for invoice in open_invoices:
        if invoice.is_in_bay:
            in_bay.setdefault(invoice.washbay_id, invoice)
    washbays = WashBay.query.order_by(WashBay.name).all()
    bays = [{'bay': washbay, 'invoice': in_bay.get(washbay.id)} for washbay in washbays]

    def payments_today(direction):
        return db.session.query(func.coalesce(func.sum(Payment.payment_amount), 0)).filter(
            Payment.payment_direction == direction,
            Payment.created_dttm >= day_start,
            Payment.created_dttm < day_end,
        ).scalar()

    unpaid_total = db.session.query(
        func.coalesce(func.sum(InvoiceHead.gross_price - func.coalesce(InvoiceHead.paid_amount, 0)), 0)
    ).filter(
        InvoiceHead.service_status == done,
        func.coalesce(InvoiceHead.gross_price, 0) > func.coalesce(InvoiceHead.paid_amount, 0),
    ).scalar()

    summary = {
        'in_station': len(open_invoices),
        'done_today': len(done_invoices),
        'collected_today': payments_today('in'),
        'paid_out_today': payments_today('out'),
        'unpaid_total': unpaid_total,
        'low_stock': Item.query.filter(
            Item.quantity.isnot(None), Item.quantity <= config.LOW_STOCK_THRESHOLD).count(),
    }

    # First-run hints: a service invoice needs a bay, an employee and something to sell.
    setup = {
        'washbays': len(washbays),
        'employees': Employee.query.count(),
        'items': Item.query.count(),
    }

    prefill_vehicle = None
    vehicle_id = request.args.get('new_service_vehicle', type=int)
    if vehicle_id:
        prefill_vehicle = db.session.get(Vehicle, vehicle_id)

    return render_template(
        'dashboard/dashboard.html',
        title='Dashboard',
        lanes=lanes,
        bays=bays,
        summary=summary,
        setup=setup,
        prefill_vehicle=prefill_vehicle,
    )


@dashboard_blueprint.route("/invoice/<token>", methods=['GET'])
def customer_invoice(token):
    """The status page a customer opens from the SMS link. No login."""
    invoice_head = InvoiceHead.verify_customer_view_token(token)
    if not invoice_head:
        return render_template(
            'error/404.html',
            title='Link expired',
            heading='This link has expired',
            message='Status links work for a few hours after the service starts. '
                    'Please ask at the counter for an update.',
        ), 404

    invoice_details = (
        InvoiceDetail.query
        .filter(InvoiceDetail.invoice_head_id == invoice_head.id)
        .order_by(InvoiceDetail.id)
        .all()
    )
    return render_template(
        'dashboard/customer_invoice.html',
        title=f"{invoice_head.vehicle.number} service status",
        invoice_head=invoice_head,
        invoice_details=invoice_details,
    )
