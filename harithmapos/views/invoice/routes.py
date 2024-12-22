import json

from sqlalchemy import func
from datetime import datetime
from flask_login import login_required
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

from harithmapos import db, config
from harithmapos.models import InvoiceHead, InvoiceDetail, ItemInvoiceHead, ItemInvoiceDetail, Customer, Vehical, WashBay, Employee, Item, Payment
from harithmapos.views.invoice.forms import InvoiceHeadCreateForm, InvoiceHeadUpdateForm, ItemInvoiceHeadCreateForm, ItemInvoiceHeadUpdateForm, InvoiceDetailCreateForm

from harithmapos.views.invoice import utils 

invoice_blueprint = Blueprint('invoice_blueprint', __name__)

@invoice_blueprint.route("/invoice/head", methods=['GET', 'POST'])
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
        invoice_heads = InvoiceHead.query.join(Vehical).order_by(InvoiceHead.update_dttm.desc()).filter(Vehical.number.ilike(f"%{query}%")).paginate(page=page, per_page=per_page)
        # invoice_heads = InvoiceHead.query.order_by(InvoiceHead.update_dttm.desc()).filter(InvoiceHead.customer_id.icontains(query)).paginate(page=page, per_page=per_page)
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

@invoice_blueprint.route("/item_invoice/head", methods=['GET', 'POST'])
@login_required
def item_invoice_head():
    item_invoice_head_create_form = ItemInvoiceHeadCreateForm()
    item_invoice_head_update_form = ItemInvoiceHeadUpdateForm()

    customers = Customer.query.all()

    per_page = 20
    page = request.args.get('page',1,type=int)
    query = request.args.get("query",None)

    if query:
        item_invoice_heads = ItemInvoiceHead.query.order_by(ItemInvoiceHead.update_dttm.desc()).filter(ItemInvoiceHead.created_dttm == query).paginate(page=page, per_page=per_page)
    else:
        item_invoice_heads = ItemInvoiceHead.query.order_by(ItemInvoiceHead.update_dttm.desc()).paginate(page=page, per_page=per_page)
    return render_template(
        'invoice/item_head.html', 
        title='Item Invoice', 
        item_invoice_head_create_form=item_invoice_head_create_form, 
        item_invoice_head_update_form=item_invoice_head_update_form,
        item_invoice_heads=item_invoice_heads,
        customers=customers,
        query=query
    )

@invoice_blueprint.route("/invoice/head/create", methods=['GET', 'POST'])
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
        vehical = Vehical.query.get(form.vehical_id.data)
        invoice = InvoiceHead(
            customer_id=vehical.owner.id,
            vehical_id=form.vehical_id.data,
            washbay_id=form.washbay_id.data,
            employee_id=form.employee_id.data,
            current_milage=form.current_milage.data
        )
        db.session.add(invoice)
        db.session.commit()

        token = invoice.get_customer_view_token()
        msg = f"Hi {vehical.owner.name}, Your vehical {vehical.number}'s service has been started. For more details please view: {url_for('invoice_blueprint.invoice_customer_view', token=token, _external=True)}"
        utils.send_sms(vehical.owner.contact, msg)
        
        return redirect(url_for('invoice_blueprint.invoice_head_detail', invoice_head_id=invoice.id))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error: {field} - {error}", category='danger')
    return redirect(url_for('invoice_blueprint.invoice_head'))

@invoice_blueprint.route("/item_invoice/head/create", methods=['GET', 'POST'])
@login_required
def insert_item_invoice_head():
    form = ItemInvoiceHeadCreateForm()
    if request.method == 'GET':
        customers = Customer.query.all()
        return render_template(
            'invoice/item_create.html', 
            title='Create Item Invoice',
            form=form,
            customers=customers,
        )
    elif form.validate_on_submit():
        customer = Customer.query.get(form.customer.data)
        item_invoice = ItemInvoiceHead(
            customer_id=customer.id
        )
        db.session.add(item_invoice)
        db.session.commit()
        return redirect(url_for('invoice_blueprint.item_invoice_head_detail', item_invoice_head_id=item_invoice.id))
    else:
        flash("Error: Item Invoice create failed!", category='danger')
    return redirect(url_for('invoice_blueprint.item_invoice_head'))

@invoice_blueprint.route("/invoice/head/<int:invoice_head_id>", methods=['GET', 'POST'])
@login_required
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
        if invoice_head_update_form.update_invoice.data or invoice_head_update_form.complete_invoice.data:
            vehical = Vehical.query.get(utils.get_id(invoice_head_update_form.vehical.data))

            invoice_head.customer_id=vehical.owner.id
            invoice_head.vehical_id=utils.get_id(invoice_head_update_form.vehical.data)
            invoice_head.washbay_id=utils.get_id(invoice_head_update_form.washbay.data)
            invoice_head.employee_id=utils.get_id(invoice_head_update_form.employee.data)
            invoice_head.current_milage=invoice_head_update_form.current_milage.data
            invoice_head.next_milage=invoice_head_update_form.next_milage.data
            invoice_head.service_status=invoice_head_update_form.service_status.data
            invoice_head.payment_method=invoice_head_update_form.payment_method.data
            invoice_head.paid_amount=invoice_head_update_form.paid_amount.data
            invoice_head.discount_pct=invoice_head_update_form.discount_pct.data
            invoice_head.remaining_amount = invoice_head.gross_price-invoice_head.paid_amount
            invoice_head.update_dttm = datetime.now()

            if invoice_details:
                update_total_values(invoice_head)
            
            if invoice_head.paid_amount:
                invoice_head.last_payment_date = datetime.now()

            if invoice_head_update_form.complete_invoice.data:
                invoice_head.service_status = 5
                payment = Payment(
                    invoice_id = invoice_head_id,
                    payment_method = "cash",
                    payment_direction = "in",
                    payment_amount = invoice_head.paid_amount,
                    payment_type = 'general',
                    remarks = 'Initial Payment',
                )
                db.session.add(payment)
                db.session.commit()
                service_invoice_json = convert_service_invoice_to_json(invoice_head)
                utils.send_print_invoice(service_invoice_json,'harithmaq')
                return redirect(url_for('dashboard_blueprint.dashboard'))

        elif invoice_head_update_form.cancel_invoice.data:
            db.session.delete(invoice_head)
            db.session.commit()
            flash("Invoice deleted.", category='warning')
            return redirect(url_for('invoice_blueprint.invoice_head'))

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
            invoice_details=invoice_details,
            service_status_form_list=config.SERVICE_STATUS_FORM_LIST,
            payment_method_form_list=config.PAYMENT_METHOD_FORM_LIST,
        )

@invoice_blueprint.route("/item_invoice/head/<int:item_invoice_head_id>", methods=['GET', 'POST'])
@login_required
def item_invoice_head_detail(item_invoice_head_id):
    item_invoice_head_update_form = ItemInvoiceHeadUpdateForm()
    item_invoice_detail_create_form = InvoiceDetailCreateForm()

    items = Item.query.all()
    customers = Customer.query.all()

    item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_head_id)
    item_invoice_details = ItemInvoiceDetail.query.filter(ItemInvoiceDetail.item_invoice_head_id==item_invoice_head_id)

    if item_invoice_head_update_form.validate_on_submit():
        if item_invoice_head_update_form.update_item_invoice.data:
            customer = Customer.query.get(int(utils.get_id(item_invoice_head_update_form.customer.data)))

            item_invoice_head.customer_id=customer.id
            item_invoice_head.payment_method=item_invoice_head_update_form.payment_method.data
            item_invoice_head.paid_amount=item_invoice_head_update_form.paid_amount.data
            item_invoice_head.discount_pct=item_invoice_head_update_form.discount_pct.data
            item_invoice_head.update_dttm = datetime.now()

            if item_invoice_details:
                update_total_values(item_invoice_head)
            
            if item_invoice_head.paid_amount:
                item_invoice_head.last_payment_date = datetime.now()
                item_invoice_head.remaining_amount = item_invoice_head.gross_price-item_invoice_head.paid_amount        

            db.session.commit()

        elif item_invoice_head_update_form.complete_item_invoice.data:
            item_invoice_json = convert_item_invoice_to_json(item_invoice_head)
            utils.send_print_invoice(item_invoice_json,'harithmaq')

    elif request.method == 'POST':
        flash("Item Invoice update failed!", category='danger')

    return render_template(
            'invoice/item_update.html', 
            title='Item Invoice', 
            item_invoice_head=item_invoice_head,
            item_invoice_head_update_form=item_invoice_head_update_form,
            item_invoice_detail_create_form=item_invoice_detail_create_form,
            items=items,
            customers=customers,
            item_invoice_details=item_invoice_details
        )

@invoice_blueprint.route('/invoice/head/<int:invoice_head_id>/delete', methods = ['GET', 'POST'])
@login_required
def delete_invoice_head(invoice_head_id):
    invoice_head = InvoiceHead.query.get_or_404(invoice_head_id)
    db.session.delete(invoice_head)
    db.session.commit()
    flash("InvoiceHead is deleted!", category='success')
    return redirect(url_for('invoice_blueprint.invoice_head'))

@invoice_blueprint.route('/item_invoice/head/<int:item_invoice_head_id>/delete', methods = ['GET', 'POST'])
@login_required
def delete_item_invoice_head(item_invoice_head_id):
    item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_head_id)
    db.session.delete(item_invoice_head)
    db.session.commit()
    flash("Success: Invoice is deleted!", category='success')
    return redirect(url_for('invoice_blueprint.item_invoice_head'))

@invoice_blueprint.route("/invoice/detail/add/<int:invoice_head_id>", methods=['GET', 'POST'])
@login_required
def add_invoice_detail(invoice_head_id):
    invoice_detail_create_form = InvoiceDetailCreateForm()
    if invoice_detail_create_form.validate_on_submit():
        item_id = invoice_detail_create_form.item_id.data
        quantity = invoice_detail_create_form.quantity.data

        item = Item.query.get_or_404(item_id)
        invoice_head = InvoiceHead.query.get_or_404(invoice_head_id)

        item.quantity -= quantity

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

        update_total_values(invoice_head)

        print(f"{invoice_head.total_cost=}")

    else:
        flash("Invoice Item failed to add!", category='danger')
    return redirect(url_for('invoice_blueprint.invoice_head_detail',invoice_head_id=invoice_head_id))

@invoice_blueprint.route("/item_invoice/detail/add/<int:item_invoice_head_id>", methods=['GET', 'POST'])
@login_required
def add_item_invoice_detail(item_invoice_head_id):
    item_invoice_detail_create_form = InvoiceDetailCreateForm()
    if item_invoice_detail_create_form.validate_on_submit():
        item_id = utils.get_id(item_invoice_detail_create_form.item.data)
        quantity = item_invoice_detail_create_form.quantity.data

        item = Item.query.get_or_404(item_id)
        item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_head_id)

        item.quantity -= quantity

        item_invoice_detail = ItemInvoiceDetail(
            item_invoice_head_id = item_invoice_head_id,
            item_id = item_id,
            quantity = quantity,
            total_cost = item.unit_cost*quantity,
            total_price = item.unit_price*quantity,
            discount_pct = 0
        )

        db.session.add(item_invoice_detail)
        db.session.commit()

        update_total_values(item_invoice_head)

        print(f"{item_invoice_head.total_cost=}")

    else:
        flash("Item Invoice Item failed to add!", category='danger')
    return redirect(url_for('invoice_blueprint.item_invoice_head_detail',item_invoice_head_id=item_invoice_head_id))

@invoice_blueprint.route("/invoice/detail/delete/<int:invoice_detail_id>", methods=['GET', 'POST'])
@login_required
def delete_invoice_detail(invoice_detail_id):
    invoice_detail = InvoiceDetail.query.get_or_404(invoice_detail_id)
    invoice_head = InvoiceHead.query.get_or_404(invoice_detail.invoice_head_id)
    item = Item.query.get_or_404(invoice_detail.item.id)

    item.quantity += invoice_detail.quantity

    db.session.delete(invoice_detail)
    db.session.commit()
    update_total_values(invoice_head)

    return redirect(url_for('invoice_blueprint.invoice_head_detail',invoice_head_id=invoice_detail.invoice_head_id))

@invoice_blueprint.route("/item_invoice/detail/delete/<int:item_invoice_detail_id>", methods=['GET', 'POST'])
@login_required
def delete_item_invoice_detail(item_invoice_detail_id):
    item_invoice_detail = ItemInvoiceDetail.query.get_or_404(item_invoice_detail_id)
    item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_detail.item_invoice_head_id)
    item = Item.query.get_or_404(item_invoice_detail.item.id)

    item.quantity += item_invoice_detail.quantity

    db.session.delete(item_invoice_detail)
    db.session.commit()
    update_total_values(item_invoice_head)

    return redirect(url_for('invoice_blueprint.item_invoice_head_detail',item_invoice_head_id=item_invoice_detail.item_invoice_head_id))

@invoice_blueprint.route("/invoice/detail/quantity/add/<int:invoice_detail_id>", methods=['GET', 'POST'])
@login_required
def increase_quantity_invoice_detail(invoice_detail_id):

    invoice_detail = InvoiceDetail.query.get_or_404(invoice_detail_id)
    invoice_head = InvoiceHead.query.get_or_404(invoice_detail.invoice_head_id)
    item = Item.query.get_or_404(invoice_detail.item.id)

    item.quantity -= 1

    invoice_detail.quantity += 1
    invoice_detail.total_cost = invoice_detail.item.unit_cost*invoice_detail.quantity
    invoice_detail.total_price = invoice_detail.item.unit_price*invoice_detail.quantity

    db.session.commit()
    update_total_values(invoice_head)
    return redirect(url_for('invoice_blueprint.invoice_head_detail',invoice_head_id=invoice_detail.invoice_head_id))

@invoice_blueprint.route("/item_invoice/detail/quantity/add/<int:item_invoice_detail_id>", methods=['GET', 'POST'])
@login_required
def increase_quantity_item_invoice_detail(item_invoice_detail_id):

    item_invoice_detail = ItemInvoiceDetail.query.get_or_404(item_invoice_detail_id)
    item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_detail.item_invoice_head_id)
    item = Item.query.get_or_404(item_invoice_detail.item.id)

    item.quantity -= 1

    item_invoice_detail.quantity += 1
    item_invoice_detail.total_cost = item_invoice_detail.item.unit_cost*item_invoice_detail.quantity
    item_invoice_detail.total_price = item_invoice_detail.item.unit_price*item_invoice_detail.quantity

    db.session.commit()
    update_total_values(item_invoice_head)
    return redirect(url_for('invoice_blueprint.item_invoice_head_detail',item_invoice_head_id=item_invoice_detail.item_invoice_head_id))

@invoice_blueprint.route("/invoice/detail/quantity/remove/<int:invoice_detail_id>", methods=['GET', 'POST'])
@login_required
def decrease_quantity_invoice_detail(invoice_detail_id):
    invoice_detail = InvoiceDetail.query.get_or_404(invoice_detail_id)
    invoice_head = InvoiceHead.query.get_or_404(invoice_detail.invoice_head_id)
    item = Item.query.get_or_404(invoice_detail.item.id)

    if invoice_detail.quantity > 1:
        item.quantity += 1
        invoice_detail.quantity -= 1
        invoice_detail.total_cost = invoice_detail.item.unit_cost*invoice_detail.quantity
        invoice_detail.total_price = invoice_detail.item.unit_price*invoice_detail.quantity
    else:
        flash("Quantity should be at leaset one!", category='warning')

    db.session.commit()
    update_total_values(invoice_head)

    return redirect(url_for('invoice_blueprint.invoice_head_detail',invoice_head_id=invoice_detail.invoice_head_id))

@invoice_blueprint.route("/item_invoice/detail/quantity/remove/<int:item_invoice_detail_id>", methods=['GET', 'POST'])
@login_required
def decrease_quantity_item_invoice_detail(item_invoice_detail_id):
    item_invoice_detail = ItemInvoiceDetail.query.get_or_404(item_invoice_detail_id)
    item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_detail.item_invoice_head_id)
    item = Item.query.get_or_404(item_invoice_detail.item.id)

    if item_invoice_detail.quantity > 1:
        item.quantity += 1
        item_invoice_detail.quantity -= 1
        item_invoice_detail.total_cost = item_invoice_detail.item.unit_cost*item_invoice_detail.quantity
        item_invoice_detail.total_price = item_invoice_detail.item.unit_price*item_invoice_detail.quantity
    else:
        flash("Quantity should be at leaset one!", category='warning')

    db.session.commit()
    update_total_values(item_invoice_head)

    return redirect(url_for('invoice_blueprint.item_invoice_head_detail',item_invoice_head_id=item_invoice_detail.item_invoice_head_id))

@invoice_blueprint.route("/invoice/customer/view/<token>", methods=['GET', 'POST'])
def invoice_customer_view(token):

    invoice_head = InvoiceHead.verify_customer_view_token(token)
    if not invoice_head:
        flash('Invalid or expired token.', category='warning')
        return render_template('error/404.html')

    invoice_details = InvoiceDetail.query.filter(InvoiceDetail.invoice_head_id==invoice_head.id)

    return render_template(
            'invoice/customer_view.html', 
            title='Invoice', 
            invoice_head=invoice_head,
            invoice_details=invoice_details,
            service_status_form_list=config.SERVICE_STATUS_FORM_LIST,
            payment_method_form_list=config.PAYMENT_METHOD_FORM_LIST,
        )


# supporting fuctions
def update_total_values(invoice_head):
    if isinstance(invoice_head,InvoiceHead):
        invoice_head.total_cost = db.session.query(func.sum(InvoiceDetail.total_cost)).filter(InvoiceDetail.invoice_head_id == invoice_head.id).one()[0]
        invoice_head.total_price = db.session.query(func.sum(InvoiceDetail.total_price)).filter(InvoiceDetail.invoice_head_id == invoice_head.id).one()[0]
    else:
        invoice_head.total_cost = db.session.query(func.sum(ItemInvoiceDetail.total_cost)).filter(ItemInvoiceDetail.item_invoice_head_id == invoice_head.id).one()[0]
        invoice_head.total_price = db.session.query(func.sum(ItemInvoiceDetail.total_price)).filter(ItemInvoiceDetail.item_invoice_head_id == invoice_head.id).one()[0]
    invoice_head.gross_price = (invoice_head.total_price - (invoice_head.total_price*(invoice_head.discount_pct/100))) if invoice_head.discount_pct else invoice_head.total_price

    invoice_head.total_cost = invoice_head.total_cost if invoice_head.total_cost else 0
    invoice_head.total_price = invoice_head.total_price if invoice_head.total_price else 0
    invoice_head.gross_price = invoice_head.gross_price if invoice_head.gross_price else 0

    db.session.commit()

def convert_item_invoice_to_json(item_invoice):
    invoice_dictionary = {
        "invoice_number": item_invoice.id,  
        "invoice_type": 2,
        "total_price": item_invoice.total_price,
        "discount_pct": item_invoice.discount_pct,
        "gross_price": item_invoice.gross_price,
        "paid_amount": item_invoice.paid_amount,
        "invoice_details": []
    }

    for detail in item_invoice.invoice_details:
        item_detail = {
            'item_name': detail.item.name,
            'unit_price': detail.item.unit_price,  # Assuming unit price is calculated as total price divided by quantity
            'quantity': detail.quantity,
            'total_price': detail.total_price
        }
        invoice_dictionary['invoice_details'].append(item_detail)

    return json.dumps(invoice_dictionary, cls=utils.DecimalEncoder)

def convert_service_invoice_to_json(service_invoice):
    invoice_dictionary = {
        "invoice_number": service_invoice.id,  
        "invoice_type": 1,
        "customer_name": service_invoice.customer.name,
        "employee_name": service_invoice.employee.name,
        "vehical_number": service_invoice.vehical.number,
        "wash_bay": service_invoice.washbay.name,
        "current_milage": service_invoice.current_milage,
        "next_milage": service_invoice.next_milage,
        "total_price": service_invoice.total_price,
        "discount_pct": service_invoice.discount_pct,
        "gross_price": service_invoice.gross_price,
        "paid_amount": service_invoice.paid_amount,
        "invoice_details": []
    }

    for detail in service_invoice.invoice_details:
        item_detail = {
            'item_name': detail.item.name,
            'unit_price': detail.item.unit_price,  # Assuming unit price is calculated as total price divided by quantity
            'quantity': detail.quantity,
            'total_price': detail.total_price
        }
        invoice_dictionary['invoice_details'].append(item_detail)

    return json.dumps(invoice_dictionary, cls=utils.DecimalEncoder)