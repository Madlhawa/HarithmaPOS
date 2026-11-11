import logging

from flask_login import login_required
from flask import Blueprint, render_template, request, flash

from harithmapos import db
from harithmapos.models import PurchaseOrderHead, Supplier
from harithmapos.timeutils import utcnow
from harithmapos.views.supplier.forms import SupplierCreateForm, SupplierUpdateForm

import harithmapos.views.utils as utils
from utils.database import safe_insert_with_sequence_check

logger = logging.getLogger(__name__)

supplier_blueprint = Blueprint('supplier_blueprint', __name__)

PER_PAGE = 25


@supplier_blueprint.route("/app/supplier", methods=['GET'])
@login_required
def supplier():
    page = request.args.get('page', 1, type=int)
    query = (request.args.get('query') or '').strip()

    suppliers = Supplier.query
    if query:
        suppliers = suppliers.filter(Supplier.name.ilike(f"%{query}%"))
    suppliers = suppliers.order_by(Supplier.name).paginate(page=page, per_page=PER_PAGE)
    return render_template('supplier.html', title='Suppliers', suppliers=suppliers, query=query)


@supplier_blueprint.route("/app/supplier/create", methods=['POST'])
@login_required
def insert_supplier():
    form = SupplierCreateForm()
    if form.validate_on_submit():
        try:
            safe_insert_with_sequence_check(
                Supplier,
                name=form.name.data,
                contact=form.contact.data,
                address=form.address.data
            )
            flash(f"{form.name.data} added.", category='success')
        except Exception:
            logger.exception("Could not add supplier")
            flash("The supplier could not be added. Please try again.", category='danger')
    else:
        utils.flash_form_errors(form)
    return utils.redirect_back('supplier_blueprint.supplier')


@supplier_blueprint.route("/app/supplier/<int:supplier_id>/update", methods=['POST'])
@login_required
def update_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    form = SupplierUpdateForm()
    if form.validate_on_submit():
        try:
            supplier.name = form.name.data
            supplier.contact = form.contact.data
            supplier.address = form.address.data
            supplier.update_dttm = utcnow()
            db.session.commit()
            flash(f"{supplier.name} saved.", category='success')
        except Exception:
            db.session.rollback()
            logger.exception("Could not update supplier %s", supplier_id)
            flash("The supplier could not be saved. Please try again.", category='danger')
    else:
        utils.flash_form_errors(form)
    return utils.redirect_back('supplier_blueprint.supplier')


@supplier_blueprint.route('/app/supplier/<int:supplier_id>/delete', methods=['POST'])
@login_required
def delete_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    utils.delete_record(supplier, supplier.name, blockers=[
        (PurchaseOrderHead.query.filter(PurchaseOrderHead.supplier_id == supplier.id).count(), 'purchase orders'),
    ])
    return utils.redirect_back('supplier_blueprint.supplier')
