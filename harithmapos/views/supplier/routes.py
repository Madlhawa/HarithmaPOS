from flask_login import login_required
from flask import Blueprint, render_template, request, redirect, url_for, flash

from harithmapos import db
from harithmapos.models import Supplier
from harithmapos.views.supplier.forms import SupplierCreateForm, SupplierUpdateForm

supplier_blueprint = Blueprint('supplier_blueprint', __name__)

@supplier_blueprint.route("/supplier", methods=['GET', 'POST'])
@login_required
def supplier():
    supplier_create_form = SupplierCreateForm()
    supplier_update_form = SupplierUpdateForm()

    per_page = 10
    page = request.args.get('page',1,type=int)
    query = request.args.get("query",None)

    if query:
        suppliers = Supplier.query.order_by(Supplier.update_dttm.desc()).filter(Supplier.name.icontains(query)).paginate(page=page, per_page=per_page)
    else:
        suppliers = Supplier.query.order_by(Supplier.update_dttm.desc()).paginate(page=page, per_page=per_page)
    return render_template(
        'supplier.html', 
        title='Supplier', 
        supplier_create_form=supplier_create_form, 
        supplier_update_form=supplier_update_form,
        suppliers=suppliers,
        query=query
    )

@supplier_blueprint.route("/supplier/create", methods=['GET', 'POST'])
@login_required
def insert_supplier():
    supplier_create_form = SupplierCreateForm()
    if supplier_create_form.validate_on_submit():
        supplier = Supplier(
            name = supplier_create_form.name.data,
            contact = supplier_create_form.contact.data,
            address = supplier_create_form.address.data
        )
        db.session.add(supplier)
        db.session.commit()
        flash("Supplier added successfully!", category='success')
    else:
        flash("Supplier failed to add!", category='danger')
    return redirect(url_for('supplier_blueprint.supplier'))

@supplier_blueprint.route("/supplier/<int:supplier_id>/update", methods=['GET', 'POST'])
@login_required
def update_supplier(supplier_id):
    supplier_update_form = SupplierUpdateForm()
    if supplier_update_form.validate_on_submit():
        supplier = Supplier.query.get_or_404(supplier_id)
        supplier.name = supplier_update_form.name.data
        supplier.contact = supplier_update_form.contact.data
        supplier.address = supplier_update_form.address.data
        db.session.commit()
        flash("Suppler is updated!", category='success')
    else:
        flash("Suppler failed to add!", category='danger')
    return redirect(url_for('supplier_blueprint.supplier'))

@supplier_blueprint.route('/supplier/<int:supplier_id>/delete', methods = ['GET', 'POST'])
@login_required
def delete_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    db.session.delete(supplier)
    db.session.commit()
    flash("Supplier is deleted!", category='success')
    return redirect(url_for('supplier_blueprint.supplier'))
