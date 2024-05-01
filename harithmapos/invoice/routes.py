from flask_login import login_required
from flask import Blueprint, render_template, request, redirect, url_for, flash

from harithmapos import db
from harithmapos.models import InvoiceHead, InvoiceDetail, Customer, Vehical, WashBay, Employee, Item
from harithmapos.invoice.forms import InvoiceHeadCreateForm, InvoiceHeadUpdateForm, InvoiceDetailCreateForm

from harithmapos.invoice.utils import get_id

invoice_head_blueprint = Blueprint('invoice_head_blueprint', __name__)

@invoice_head_blueprint.route("/invoice/search", methods=['GET', 'POST'])
@login_required
def invoice_head_search():
    query = request.args.get(query)
    print(query)

    if query:
        results = Customer.query.filter(Customer.name.icontains(query))
    else:
        results = []
    
    return render_template(
        'invoice_head.html', 
        title='InvoiceHead',
        results = results,
        query=query
    )

@invoice_head_blueprint.route("/invoice/head", methods=['GET', 'POST'])
@login_required
def invoice_head():
    invoice_head_create_form = InvoiceHeadCreateForm()
    invoice_head_update_form = InvoiceHeadUpdateForm()

    vehicals = Vehical.query.all()
    employees = Employee.query.all()
    washbays = WashBay.query.all()

    per_page = 20
    page = request.args.get('page',1,type=int)
    query = request.args.get("query",None)

    if query:
        invoice_heads = InvoiceHead.query.order_by(InvoiceHead.update_dttm.desc()).filter(InvoiceHead.customer_id.icontains(query)).paginate(page=page, per_page=per_page)
    else:
        invoice_heads = InvoiceHead.query.order_by(InvoiceHead.update_dttm.desc()).paginate(page=page, per_page=per_page)
    return render_template(
        'invoice/head.html', 
        title='InvoiceHead', 
        invoice_head_create_form=invoice_head_create_form, 
        invoice_head_update_form=invoice_head_update_form,
        invoice_heads=invoice_heads,
        vehicals=vehicals,
        employees=employees,
        washbays=washbays,
        query=query
    )

@invoice_head_blueprint.route("/invoice/head/create", methods=['GET', 'POST'])
@login_required
def insert_invoice_head():
    form = InvoiceHeadCreateForm()
    if request.method == 'GET':
        vehicals = Vehical.query.all()
        employees = Employee.query.all()
        washbays = WashBay.query.all()
        return render_template(
            'invoice/create.html', 
            title='Create Invoice',
            form=form,
            vehicals=vehicals,
            employees=employees,
            washbays=washbays,
        )
    elif form.validate_on_submit():
        vehical = Vehical.query.get(form.vehical.data)
        invoice = InvoiceHead(
            customer_id=vehical.owner.id,
            vehical_id=form.vehical.data,
            washbay_id=form.washbay.data,
            employee_id=form.employee.data,
            current_milage=form.current_milage.data
        )
        db.session.add(invoice)
        db.session.commit()
        return redirect(url_for('invoice_head_blueprint.invoice_head'))

@invoice_head_blueprint.route("/invoice/head/<int:invoice_head_id>", methods=['GET', 'POST'])
def invoice_head_detail(invoice_head_id):
    invoice_head_update_form = InvoiceHeadUpdateForm()
    invoice_detail_create_form = InvoiceDetailCreateForm()

    items = Item.query.all()
    vehicals = Vehical.query.all()
    employees = Employee.query.all()
    washbays = WashBay.query.all()

    invoice_head = InvoiceHead.query.get_or_404(invoice_head_id)
    invoice_details = InvoiceDetail.query.filter(InvoiceDetail.invoice_head_id==invoice_head_id)

    if invoice_head_update_form.validate_on_submit():
        vehical = Vehical.query.get(int(invoice_head_update_form.vehical.data.split('|')[0].strip()))

        invoice_head.customer_id=vehical.owner.id
        invoice_head.vehical_id=int(invoice_head_update_form.vehical.data.split('|')[0].strip())
        invoice_head.washbay_id=int(invoice_head_update_form.washbay.data.split('|')[0].strip())
        invoice_head.employee_id=int(invoice_head_update_form.employee.data.split('|')[0].strip())
        invoice_head.current_milage=invoice_head_update_form.current_milage.data
        invoice_head.next_milage=invoice_head_update_form.next_milage.data
        invoice_head.service_status=invoice_head_update_form.service_status.data
        invoice_head.discount_pct=invoice_head_update_form.discount_pct.data
        invoice_head.payment_method=invoice_head_update_form.payment_method.data
        invoice_head.paid_amount=invoice_head_update_form.paid_amount.data

        db.session.commit()
    elif request.method == 'POST':
        flash("Invoice update failed!", category='danger')

    return render_template(
            'invoice/update.html', 
            title='Invoice', 
            invoice_head=invoice_head,
            invoice_head_update_form=invoice_head_update_form,
            invoice_detail_create_form=invoice_detail_create_form,
            items=items,
            vehicals=vehicals,
            employees=employees,
            washbays=washbays,
            invoice_details=invoice_details
        )

@invoice_head_blueprint.route('/invoice/head/<int:invoice_head_id>/delete', methods = ['GET', 'POST'])
@login_required
def delete_invoice_head(invoice_head_id):
    invoice_head = InvoiceHead.query.get_or_404(invoice_head_id)
    db.session.delete(invoice_head)
    db.session.commit()
    flash("InvoiceHead is deleted!", category='success')
    return redirect(url_for('invoice_head_blueprint.invoice_head'))

@invoice_head_blueprint.route("/invoice/detail/add/<int:invoice_head_id>", methods=['GET', 'POST'])
def add_invoice_detail(invoice_head_id):
    invoice_detail_create_form = InvoiceDetailCreateForm()
    if invoice_detail_create_form.validate_on_submit():
        item_id = get_id(invoice_detail_create_form.item.data)
        quantity = invoice_detail_create_form.quantity.data
        item = Item.query.get_or_404(item_id)
        invoice_detail = InvoiceDetail(
            invoice_head_id = invoice_head_id,
            item_id = item_id,
            quantity = quantity,
            total_cost = item.unit_cost*quantity,
            total_price = item.unit_price*quantity,
            discount_pct = 0
        )
        db.session.add(invoice_detail)
        db.session.commit()
    else:
        flash("Invoice Item failed to add!", category='danger')
    return redirect(url_for('invoice_head_blueprint.invoice_head_detail',invoice_head_id=invoice_head_id))

@invoice_head_blueprint.route("/invoice/detail/delete/<int:invoice_detail_id>", methods=['GET', 'POST'])
def delete_invoice_detail(invoice_detail_id):
    invoice_detail = InvoiceDetail.query.get_or_404(invoice_detail_id)
    db.session.delete(invoice_detail)
    db.session.commit()
    return redirect(url_for('invoice_head_blueprint.invoice_head_detail',invoice_head_id=invoice_detail.invoice_head_id))

@invoice_head_blueprint.route("/invoice/detail/quantity/add/<int:invoice_detail_id>", methods=['GET', 'POST'])
def increase_quantity_invoice_detail(invoice_detail_id):
    invoice_detail = InvoiceDetail.query.get_or_404(invoice_detail_id)
    invoice_detail.quantity += 1
    invoice_detail.total_cost = invoice_detail.item.unit_cost*invoice_detail.quantity
    invoice_detail.total_price = invoice_detail.item.unit_price*invoice_detail.quantity
    db.session.commit()
    return redirect(url_for('invoice_head_blueprint.invoice_head_detail',invoice_head_id=invoice_detail.invoice_head_id))

@invoice_head_blueprint.route("/invoice/detail/quantity/remove/<int:invoice_detail_id>", methods=['GET', 'POST'])
def decrease_quantity_invoice_detail(invoice_detail_id):
    invoice_detail = InvoiceDetail.query.get_or_404(invoice_detail_id)
    if invoice_detail.quantity > 1:
        invoice_detail.quantity -= 1
        invoice_detail.total_cost = invoice_detail.item.unit_cost*invoice_detail.quantity
        invoice_detail.total_price = invoice_detail.item.unit_price*invoice_detail.quantity
    else:
        flash("Quantity should be at leaset one!", category='warning')
    db.session.commit()
    return redirect(url_for('invoice_head_blueprint.invoice_head_detail',invoice_head_id=invoice_detail.invoice_head_id))