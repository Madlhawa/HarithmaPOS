from flask_login import login_required
from flask import Blueprint, render_template, request, redirect, url_for, flash

from harithmapos import db
from harithmapos.models import InvoiceHead, Customer, Vehical, WashBay, Employee
from harithmapos.invoice.forms import InvoiceHeadCreateForm, InvoiceHeadUpdateForm

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

    per_page = 10
    page = request.args.get('page',1,type=int)
    query = request.args.get("query",None)

    if query:
        invoice_heads = InvoiceHead.query.order_by(InvoiceHead.update_dttm.desc()).filter(InvoiceHead.name.icontains(query)).paginate(page=page, per_page=per_page)
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

@invoice_head_blueprint.route("/invoice/head/<int:invoice_head_id>/update", methods=['GET', 'POST'])
@login_required
def update_invoice_head(invoice_head_id):
    invoice_head_update_form = InvoiceHeadUpdateForm()
    if invoice_head_update_form.validate_on_submit():
        invoice_head = InvoiceHead.query.get_or_404(invoice_head_id)
        invoice_head.name = invoice_head_update_form.name.data
        invoice_head.contact = invoice_head_update_form.contact.data
        invoice_head.address = invoice_head_update_form.address.data
        db.session.commit()
        flash("Suppler is updated!", category='success')
    else:
        flash("Suppler failed to add!", category='danger')
    return redirect(url_for('invoice_head_blueprint.invoice_head'))

@invoice_head_blueprint.route('/invoice/head/<int:invoice_head_id>/delete', methods = ['GET', 'POST'])
@login_required
def delete_invoice_head(invoice_head_id):
    invoice_head = InvoiceHead.query.get_or_404(invoice_head_id)
    db.session.delete(invoice_head)
    db.session.commit()
    flash("InvoiceHead is deleted!", category='success')
    return redirect(url_for('invoice_head_blueprint.invoice_head'))
