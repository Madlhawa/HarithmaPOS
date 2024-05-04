from sqlalchemy import func
from datetime import datetime
from flask_login import login_required
from flask import Blueprint, render_template, request, redirect, url_for, flash

from harithmapos import db
from harithmapos.models import InvoiceHead, InvoiceDetail, Customer, Vehical, WashBay, Employee, Item
from harithmapos.views.invoice.forms import InvoiceHeadCreateForm, InvoiceHeadUpdateForm, InvoiceDetailCreateForm

from harithmapos.views.invoice.utils import get_id

dashboard_blueprint = Blueprint('dashboard_blueprint', __name__)

@dashboard_blueprint.route('/dashboard')
def dashboard():
    results = WashBay.query.all()
    return render_template(
        'dashboard.html',
        title='InvoiceHead',
        results = results,
    )