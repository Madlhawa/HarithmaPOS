from flask_login import login_required
from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime

from harithmapos import db
from harithmapos.models import Payment, InvoiceHead, ItemInvoiceHead, PurchaseOrderHead,Customer, Employee
from harithmapos.views.payment.forms import PaymentCreateForm, PaymentUpdateForm

payment_blueprint = Blueprint('payment_blueprint', __name__)

@payment_blueprint.route("/payment", methods=['GET', 'POST'])
@login_required
def payment():
    payment_create_form = PaymentCreateForm()
    payment_update_form = PaymentUpdateForm()

    invoices = InvoiceHead.query.all()
    item_invoices = ItemInvoiceHead.query.all()
    purchase_orders = PurchaseOrderHead.query.all()
    customers = Customer.query.all()
    employees = Employee.query.all()

    per_page = 10
    page = request.args.get('page',1,type=int)
    query = request.args.get("query",None)

    if query:
        payments = Payment.query.order_by(Payment.update_dttm.desc()).paginate(page=page, per_page=per_page)
    else:
        payments = Payment.query.order_by(Payment.update_dttm.desc()).paginate(page=page, per_page=per_page)
    return render_template(
        'payment.html', 
        title='Payment', 
        payment_create_form=payment_create_form, 
        payment_update_form=payment_update_form,
        payments=payments,
        query=query,
        invoices=invoices,
        item_invoices=item_invoices,
        purchase_orders=purchase_orders,
        customers=customers,
        employees=employees
    )

@payment_blueprint.route("/payment/create", methods=['GET', 'POST'])
@login_required
def insert_payment():
    payment_create_form = PaymentCreateForm()
    if payment_create_form.validate_on_submit():
        payment = Payment(
            invoice_id = payment_create_form.invoice_id.data if payment_create_form.invoice_id.data != '' else None,
            item_invoice_id = payment_create_form.item_invoice_id.data if payment_create_form.item_invoice_id.data != '' else None,
            purchase_order_id = payment_create_form.purchase_order_id.data if payment_create_form.purchase_order_id.data != '' else None,
            customer_id = payment_create_form.customer_id.data if payment_create_form.customer_id.data != '' else None,
            employee_id = payment_create_form.employee_id.data if payment_create_form.employee_id.data != '' else None,
            payment_method = payment_create_form.payment_method.data,
            payment_direction = payment_create_form.payment_direction.data,
            payment_amount = payment_create_form.payment_amount.data,
            payment_type = payment_create_form.payment_type.data,
            remarks = payment_create_form.remarks.data,
        )
        db.session.add(payment)
        db.session.commit()

        if payment.invoice_id:
            invoice_head = InvoiceHead.query.get_or_404(payment.invoice_id)
            invoice_head.remaining_amount -= payment.payment_amount
            invoice_head.paid_amount += payment.payment_amount
            invoice_head.last_payment_date = datetime.utcnow()
            db.session.commit()

        flash("Payment added successfully!", category='success')
    else:
        flash("Payment failed to add!", category='danger')
    return redirect(url_for('payment_blueprint.payment'))

@payment_blueprint.route("/payment/<int:payment_id>/update", methods=['GET', 'POST'])
@login_required
def update_payment(payment_id):
    payment_update_form = PaymentUpdateForm()
    if payment_update_form.validate_on_submit():
        payment = Payment.query.get_or_404(payment_id)
        payment.invoice_id = payment_update_form.invoice_id.data
        payment.item_invoice_id = payment_update_form.item_invoice_id.data
        payment.purchase_order_id = payment_update_form.purchase_order_id.data
        payment.customer_id = payment_update_form.customer_id.data
        payment.employee_id = payment_update_form.employee_id.data
        payment.payment_method = payment_update_form.payment_method.data
        payment.payment_direction = payment_update_form.payment_direction.data
        payment.payment_amount = payment_update_form.payment_amount.data
        payment.payment_type = payment_update_form.payment_type.data
        payment.remarks = payment_update_form.remarks.data
        db.session.commit()
        flash("Suppler is updated!", category='success')
    else:
        flash("Suppler failed to add!", category='danger')
    return redirect(url_for('payment_blueprint.payment'))

@payment_blueprint.route('/payment/<int:payment_id>/delete', methods = ['GET', 'POST'])
@login_required
def delete_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)

    if payment.invoice_id:
        invoice_head = InvoiceHead.query.get_or_404(payment.invoice_id)
        invoice_head.remaining_amount += payment.payment_amount
        invoice_head.paid_amount -= payment.payment_amount
        db.session.commit()

    db.session.delete(payment)
    db.session.commit()
    flash("Payment is deleted!", category='success')
    return redirect(url_for('payment_blueprint.payment'))
