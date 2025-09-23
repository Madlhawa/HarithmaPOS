from sqlalchemy import func
from datetime import datetime
from flask_login import login_required
from flask import Blueprint, render_template, request, redirect, url_for, flash
import pytz

from harithmapos import db, config
from harithmapos.models import InvoiceHead, InvoiceDetail, Customer, Vehicle, WashBay, Employee, Item
from harithmapos.views.invoice.forms import InvoiceHeadCreateForm, InvoiceHeadUpdateForm, InvoiceDetailCreateForm

from harithmapos.views.invoice.utils import get_id

dashboard_blueprint = Blueprint('dashboard_blueprint', __name__)

@dashboard_blueprint.route('/app/dashboard')
@login_required
def dashboard():
    invoice_head_create_form = InvoiceHeadCreateForm()

    results = WashBay.query.all()
    waiting_invoices = InvoiceHead.query.filter(InvoiceHead.service_status==0).all()
    polishing_invoices = InvoiceHead.query.filter(InvoiceHead.service_status==4).all()
    done_invoices = InvoiceHead.query.filter(InvoiceHead.service_status==5).filter(db.func.date(InvoiceHead.created_dttm) == datetime.now().date()).all()

    active_wash_bays = [washbay for washbay in results if washbay.active_invoice ]
    inactive_wash_bays = [washbay for washbay in results if not washbay.active_invoice ]

    return render_template(
        'dashboard/dashboard.html',
        title='InvoiceHead',
        invoice_head_create_form=invoice_head_create_form,
        results = results,
        active_wash_bays=active_wash_bays,
        inactive_wash_bays=inactive_wash_bays,
        waiting_invoices=waiting_invoices,
        polishing_invoices=polishing_invoices,
        done_invoices=done_invoices,
        service_status_form_list=config.SERVICE_STATUS_FORM_LIST,
        service_status_list=config.SERVICE_STATUS_LIST
    )

@dashboard_blueprint.route("/invoice/<token>", methods=['GET', 'POST'])
def customer_invoice(token):

    invoice_head = InvoiceHead.verify_customer_view_token(token)
    if not invoice_head:
        flash('Invalid or expired token.', category='warning')
        return render_template('error/404.html')

    invoice_details = InvoiceDetail.query.filter(InvoiceDetail.invoice_head_id==invoice_head.id)

    return render_template(
            'dashboard/customer_invoice.html', 
            title='Invoice', 
            invoice_head=invoice_head,
            invoice_details=invoice_details,
            service_status_form_list=config.SERVICE_STATUS_FORM_LIST,
            payment_method_form_list=config.PAYMENT_METHOD_FORM_LIST,
        )

# supporting functions
@dashboard_blueprint.app_template_filter('to_ist')
def to_ist_filter(dt):
    from_zone = pytz.timezone('UTC')
    to_zone = pytz.timezone('Asia/Kolkata')
    dt = from_zone.localize(dt)
    converted_dt = dt.astimezone(to_zone)
    return converted_dt.strftime('%b-%d %I:%M %p')

@dashboard_blueprint.app_template_filter('elapsed_time')
def elapsed_time_filter(dt):
    current_time = datetime.utcnow()
    elapsed = current_time - dt
    hours = int(elapsed.total_seconds() // 3600)
    minutes = int((elapsed.total_seconds() % 3600) // 60)
    return f"{hours} hrs, {minutes} mins"

@dashboard_blueprint.app_template_filter('format_quantity')
def format_quantity(value):
    if value is None:
        return ''
    return f"{float(value):g}"  # Removes trailing zeros and shows decimals only if necessary