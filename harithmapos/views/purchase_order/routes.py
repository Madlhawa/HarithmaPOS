from sqlalchemy import func
from datetime import datetime
from flask_login import login_required
from flask import Blueprint, render_template, request, redirect, url_for, flash

from harithmapos import db
from harithmapos.models import PurchaseOrderHead, PurchaseOrderDetail, Supplier, Vehical, WashBay, Employee, Item
from harithmapos.views.purchase_order.forms import PurchaseOrderHeadCreateForm, PurchaseOrderHeadUpdateForm, PurchaseOrderDetailCreateForm

from harithmapos.views.purchase_order.utils import get_id

purchase_order_blueprint = Blueprint('purchase_order_blueprint', __name__)

@purchase_order_blueprint.route("/purchase_order/search", methods=['GET', 'POST'])
@login_required
def purchase_order_head_search():
    query = request.args.get(query)
    print(query)

    if query:
        results = Supplier.query.filter(Supplier.name.icontains(query))
    else:
        results = []
    
    return render_template(
        'purchase_order_head.html', 
        title='Purchase Order',
        results = results,
        query=query
    )

@purchase_order_blueprint.route("/purchase_order/head", methods=['GET', 'POST'])
@login_required
def purchase_order_head():
    purchase_order_head_create_form = PurchaseOrderHeadCreateForm()
    purchase_order_head_update_form = PurchaseOrderHeadUpdateForm()

    suppliers = Supplier.query.all()

    per_page = 20
    page = request.args.get('page',1,type=int)
    query = request.args.get("query",None)

    if query:
        purchase_order_heads = PurchaseOrderHead.query.order_by(PurchaseOrderHead.update_dttm.desc()).filter(PurchaseOrderHead.supplier_id.icontains(query)).paginate(page=page, per_page=per_page)
    else:
        purchase_order_heads = PurchaseOrderHead.query.order_by(PurchaseOrderHead.update_dttm.desc()).paginate(page=page, per_page=per_page)
    return render_template(
        'purchase_order/head.html', 
        title='PurchaseOrderHead', 
        purchase_order_head_create_form=purchase_order_head_create_form, 
        purchase_order_head_update_form=purchase_order_head_update_form,
        purchase_order_heads=purchase_order_heads,
        suppliers=suppliers,
        query=query
    )

@purchase_order_blueprint.route("/purchase_order/head/create", methods=['GET', 'POST'])
@login_required
def insert_purchase_order_head():
    form = PurchaseOrderHeadCreateForm()
    if request.method == 'GET':
        supplier = Supplier.query.all()
        return render_template(
            'purchase_order/create.html', 
            title='Create PurchaseOrder',
            form=form,
            supplier=supplier
        )
    elif form.validate_on_submit():
        purchase_order = PurchaseOrderHead(
            supplier_id=form.supplier.data,
            supplier_invoice_id=form.supplier_invoice_id.data
        )
        db.session.add(purchase_order)
        db.session.commit()
        return redirect(url_for('purchase_order_blueprint.purchase_order_head_detail', purchase_order_head_id=purchase_order.id))
    else:
        flash("Error: PurchaseOrder create failed!", category='danger')
    return redirect(url_for('purchase_order_blueprint.purchase_order_head'))

@purchase_order_blueprint.route("/purchase_order/head/<int:purchase_order_head_id>", methods=['GET', 'POST'])
@login_required
def purchase_order_head_detail(purchase_order_head_id):
    purchase_order_head_update_form = PurchaseOrderHeadUpdateForm()
    purchase_order_detail_create_form = PurchaseOrderDetailCreateForm()

    suppliers = Supplier.query.all()

    purchase_order_head = PurchaseOrderHead.query.get_or_404(purchase_order_head_id)
    purchase_order_details = PurchaseOrderDetail.query.filter(PurchaseOrderDetail.purchase_order_head_id==purchase_order_head_id)

    if purchase_order_head_update_form.validate_on_submit():
        if purchase_order_head_update_form.update_purchase_order.data:
            
            purchase_order_head.supplier_id=int(purchase_order_head_update_form.supplier.data.split('|')[0].strip())
            purchase_order_head.supplier_invoice_id=purchase_order_head_update_form.supplier_invoice_id.data
            purchase_order_head.payment_method=purchase_order_head_update_form.payment_method.data
            purchase_order_head.paid_amount=purchase_order_head_update_form.paid_amount.data
            purchase_order_head.discount_pct=purchase_order_head_update_form.discount_pct.data

            if purchase_order_details:
                update_total_values(purchase_order_head)
            
            if purchase_order_head.paid_amount:
                purchase_order_head.last_payment_date = datetime.now()
                purchase_order_head.remaining_amount = purchase_order_head.gross_price-purchase_order_head.paid_amount        

            db.session.commit()

        elif purchase_order_head_update_form.complete_purchase_order.data:
            pass

    elif request.method == 'POST':
        flash("PurchaseOrder update failed!", category='danger')

    return render_template(
            'purchase_order/update.html', 
            title='PurchaseOrder', 
            purchase_order_head=purchase_order_head,
            purchase_order_head_update_form=purchase_order_head_update_form,
            purchase_order_detail_create_form=purchase_order_detail_create_form,
            suppliers=suppliers,
            purchase_order_details=purchase_order_details
        )

@purchase_order_blueprint.route('/purchase_order/head/<int:purchase_order_head_id>/delete', methods = ['GET', 'POST'])
@login_required
def delete_purchase_order_head(purchase_order_head_id):
    purchase_order_head = PurchaseOrderHead.query.get_or_404(purchase_order_head_id)
    db.session.delete(purchase_order_head)
    db.session.commit()
    flash("PurchaseOrderHead is deleted!", category='success')
    return redirect(url_for('purchase_order_blueprint.purchase_order_head'))

@purchase_order_blueprint.route("/purchase_order/detail/add/<int:purchase_order_head_id>", methods=['GET', 'POST'])
@login_required
def add_purchase_order_detail(purchase_order_head_id):
    purchase_order_detail_create_form = PurchaseOrderDetailCreateForm()
    if purchase_order_detail_create_form.validate_on_submit():
        item_id = get_id(purchase_order_detail_create_form.item.data)
        quantity = purchase_order_detail_create_form.quantity.data

        item = Item.query.get_or_404(item_id)
        purchase_order_head = PurchaseOrderHead.query.get_or_404(purchase_order_head_id)

        item.quantity += quantity

        purchase_order_detail = PurchaseOrderDetail(
            purchase_order_head_id = purchase_order_head_id,
            item_id = item_id,
            quantity = quantity,
            total_cost = item.unit_cost*quantity,
            total_price = item.unit_price*quantity,
            discount_pct = 0
        )

        db.session.add(purchase_order_detail)
        db.session.commit()

        update_total_values(purchase_order_head)

        print(f"{purchase_order_head.total_cost=}")

    else:
        flash("PurchaseOrder Item failed to add!", category='danger')
    return redirect(url_for('purchase_order_blueprint.purchase_order_head_detail',purchase_order_head_id=purchase_order_head_id))

@purchase_order_blueprint.route("/purchase_order/detail/delete/<int:purchase_order_detail_id>", methods=['GET', 'POST'])
@login_required
def delete_purchase_order_detail(purchase_order_detail_id):
    purchase_order_detail = PurchaseOrderDetail.query.get_or_404(purchase_order_detail_id)
    purchase_order_head = PurchaseOrderHead.query.get_or_404(purchase_order_detail.purchase_order_head_id)
    item = Item.query.get_or_404(purchase_order_detail.item.id)

    item.quantity -= purchase_order_detail.quantity

    db.session.delete(purchase_order_detail)
    db.session.commit()
    update_total_values(purchase_order_head)

    return redirect(url_for('purchase_order_blueprint.purchase_order_head_detail',purchase_order_head_id=purchase_order_detail.purchase_order_head_id))

@purchase_order_blueprint.route("/purchase_order/detail/quantity/add/<int:purchase_order_detail_id>", methods=['GET', 'POST'])
@login_required
def increase_quantity_purchase_order_detail(purchase_order_detail_id):

    purchase_order_detail = PurchaseOrderDetail.query.get_or_404(purchase_order_detail_id)
    purchase_order_head = PurchaseOrderHead.query.get_or_404(purchase_order_detail.purchase_order_head_id)
    item = Item.query.get_or_404(purchase_order_detail.item.id)

    item.quantity += 1

    purchase_order_detail.quantity += 1
    purchase_order_detail.total_cost = purchase_order_detail.item.unit_cost*purchase_order_detail.quantity
    purchase_order_detail.total_price = purchase_order_detail.item.unit_price*purchase_order_detail.quantity

    db.session.commit()
    update_total_values(purchase_order_head)
    return redirect(url_for('purchase_order_blueprint.purchase_order_head_detail',purchase_order_head_id=purchase_order_detail.purchase_order_head_id))

@purchase_order_blueprint.route("/purchase_order/detail/quantity/remove/<int:purchase_order_detail_id>", methods=['GET', 'POST'])
@login_required
def decrease_quantity_purchase_order_detail(purchase_order_detail_id):
    purchase_order_detail = PurchaseOrderDetail.query.get_or_404(purchase_order_detail_id)
    purchase_order_head = PurchaseOrderHead.query.get_or_404(purchase_order_detail.purchase_order_head_id)
    item = Item.query.get_or_404(purchase_order_detail.item.id)

    if purchase_order_detail.quantity > 1:
        item.quantity -= 1
        purchase_order_detail.quantity -= 1
        purchase_order_detail.total_cost = purchase_order_detail.item.unit_cost*purchase_order_detail.quantity
        purchase_order_detail.total_price = purchase_order_detail.item.unit_price*purchase_order_detail.quantity
    else:
        flash("Quantity should be at leaset one!", category='warning')

    db.session.commit()
    update_total_values(purchase_order_head)

    return redirect(url_for('purchase_order_blueprint.purchase_order_head_detail',purchase_order_head_id=purchase_order_detail.purchase_order_head_id))



# supporting fuctions
def update_total_values(purchase_order_head):
    purchase_order_head.total_cost = db.session.query(func.sum(PurchaseOrderDetail.total_cost)).filter(PurchaseOrderDetail.purchase_order_head_id == purchase_order_head.id).one()[0]
    purchase_order_head.total_price = db.session.query(func.sum(PurchaseOrderDetail.total_price)).filter(PurchaseOrderDetail.purchase_order_head_id == purchase_order_head.id).one()[0]
    purchase_order_head.gross_price = (purchase_order_head.total_price - (purchase_order_head.total_price*(purchase_order_head.discount_pct/100))) if purchase_order_head.discount_pct else purchase_order_head.total_price

    purchase_order_head.total_cost = purchase_order_head.total_cost if purchase_order_head.total_cost else 0
    purchase_order_head.total_price = purchase_order_head.total_price if purchase_order_head.total_price else 0
    purchase_order_head.gross_price = purchase_order_head.gross_price if purchase_order_head.gross_price else 0

    db.session.commit()