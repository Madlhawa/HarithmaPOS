import logging

from flask import Blueprint, render_template, request, flash

from harithmapos import db
from harithmapos.models import InvoiceHead, WashBay
from harithmapos.views.washbay.forms import WashBayCreateForm, WashBayUpdateForm
from harithmapos.permissions import owner_required

import harithmapos.views.utils as utils
from utils.database import safe_insert_with_sequence_check

logger = logging.getLogger(__name__)

washbay_blueprint = Blueprint('washbay_blueprint', __name__)

PER_PAGE = 25


@washbay_blueprint.route("/app/washbay", methods=['GET'])
@owner_required
def washbay():
    page = request.args.get('page', 1, type=int)
    query = (request.args.get('query') or '').strip()

    washbays = WashBay.query
    if query:
        washbays = washbays.filter(WashBay.name.ilike(f"%{query}%"))
    washbays = washbays.order_by(WashBay.name).paginate(page=page, per_page=PER_PAGE)
    return render_template('washbay.html', title='Wash bays', washbays=washbays, query=query)


@washbay_blueprint.route("/app/washbay/create", methods=['POST'])
@owner_required
def insert_washbay():
    form = WashBayCreateForm()
    if form.validate_on_submit():
        try:
            safe_insert_with_sequence_check(
                WashBay,
                name=form.name.data,
                remarks=form.remarks.data,
                capacity=form.capacity.data
            )
            flash(f"{form.name.data} added.", category='success')
        except Exception:
            logger.exception("Could not add wash bay")
            flash("The wash bay could not be added. Please try again.", category='danger')
    else:
        utils.flash_form_errors(form)
    return utils.redirect_back('washbay_blueprint.washbay')


@washbay_blueprint.route("/app/washbay/<int:washbay_id>/update", methods=['POST'])
@owner_required
def update_washbay(washbay_id):
    washbay = WashBay.query.get_or_404(washbay_id)
    form = WashBayUpdateForm()
    if form.validate_on_submit():
        try:
            washbay.name = form.name.data
            washbay.remarks = form.remarks.data
            washbay.capacity = form.capacity.data
            db.session.commit()
            flash(f"{washbay.name} saved.", category='success')
        except Exception:
            db.session.rollback()
            logger.exception("Could not update wash bay %s", washbay_id)
            flash("The wash bay could not be saved. Please try again.", category='danger')
    else:
        utils.flash_form_errors(form)
    return utils.redirect_back('washbay_blueprint.washbay')


@washbay_blueprint.route('/app/washbay/<int:washbay_id>/delete', methods=['POST'])
@owner_required
def delete_washbay(washbay_id):
    washbay = WashBay.query.get_or_404(washbay_id)
    utils.delete_record(washbay, washbay.name, blockers=[
        (InvoiceHead.query.filter(InvoiceHead.washbay_id == washbay.id).count(), 'service invoices'),
    ])
    return utils.redirect_back('washbay_blueprint.washbay')
