import logging

from flask import Blueprint, render_template, request, flash

from harithmapos import db
from harithmapos.models import Supplier
from harithmapos.timeutils import utcnow
from harithmapos.views.supplier.forms import SupplierCreateForm, SupplierUpdateForm
from harithmapos.permissions import owner_required

import harithmapos.views.utils as utils

logger = logging.getLogger(__name__)

supplier_blueprint = Blueprint('supplier_blueprint', __name__)

PER_PAGE = 25


@supplier_blueprint.route("/app/supplier", methods=['GET'])
@owner_required
def supplier():
    page = request.args.get('page', 1, type=int)
    query = (request.args.get('query') or '').strip()

    show = 'archived' if request.args.get('show') == 'archived' else ''
    suppliers = Supplier.query.filter(Supplier.is_archived if show else ~Supplier.is_archived)
    if query:
        suppliers = suppliers.filter(Supplier.name.ilike(f"%{query}%"))
    suppliers = suppliers.order_by(Supplier.name).paginate(page=page, per_page=PER_PAGE)
    return render_template('supplier.html', title='Suppliers', suppliers=suppliers, query=query, show=show)


@supplier_blueprint.route("/app/supplier/create", methods=['POST'])
@owner_required
def insert_supplier():
    form = SupplierCreateForm()
    if form.validate_on_submit():
        try:
            db.session.add(Supplier(
                name=form.name.data,
                contact=form.contact.data,
                address=form.address.data,
            ))
            db.session.commit()
            flash(f"{form.name.data} added.", category='success')
        except Exception:
            db.session.rollback()
            logger.exception("Could not add supplier")
            flash("The supplier could not be added. Please try again.", category='danger')
    else:
        utils.flash_form_errors(form)
    return utils.redirect_back('supplier_blueprint.supplier')


@supplier_blueprint.route("/app/supplier/<int:supplier_id>/update", methods=['POST'])
@owner_required
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


@supplier_blueprint.route('/app/supplier/<int:supplier_id>/archive', methods=['POST'])
@owner_required
def archive_supplier(supplier_id):
    supplier = db.get_or_404(Supplier, supplier_id)
    utils.archive_record(supplier, supplier.name)
    return utils.redirect_back('supplier_blueprint.supplier')


@supplier_blueprint.route('/app/supplier/<int:supplier_id>/restore', methods=['POST'])
@owner_required
def restore_supplier(supplier_id):
    supplier = db.get_or_404(Supplier, supplier_id)
    utils.restore_record(supplier, supplier.name)
    return utils.redirect_back('supplier_blueprint.supplier')
