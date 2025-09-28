import json

from sqlalchemy import func, desc
from datetime import datetime
from flask_login import login_required
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

from harithmapos import db, config
from harithmapos.models import InvoiceHead, InvoiceDetail, ItemInvoiceHead, ItemInvoiceDetail, Customer, Vehicle, WashBay, Employee, Item, Payment, InvoiceStatusLog
from harithmapos.views.invoice.forms import InvoiceHeadCreateForm, InvoiceHeadUpdateForm, ItemInvoiceHeadCreateForm, ItemInvoiceHeadUpdateForm, InvoiceDetailCreateForm

from harithmapos.views.invoice import utils 

invoice_blueprint = Blueprint('invoice_blueprint', __name__)

@invoice_blueprint.route("/app/invoice/head", methods=['GET', 'POST'])
@login_required
def invoice_head():
    invoice_head_create_form = InvoiceHeadCreateForm()
    invoice_head_update_form = InvoiceHeadUpdateForm()

    vehicles = Vehicle.query.all()
    employees = Employee.query.all()
    washbays = WashBay.query.all()

    per_page = 20
    page = request.args.get('page',1,type=int)
    query = request.args.get("query",None)

    if query:
        invoice_heads = InvoiceHead.query.join(Vehicle).order_by(InvoiceHead.update_dttm.desc()).filter(Vehicle.number.ilike(f"%{query}%")).paginate(page=page, per_page=per_page)
        # invoice_heads = InvoiceHead.query.order_by(InvoiceHead.update_dttm.desc()).filter(InvoiceHead.customer_id.icontains(query)).paginate(page=page, per_page=per_page)
    else:
        invoice_heads = InvoiceHead.query.order_by(InvoiceHead.update_dttm.desc()).paginate(page=page, per_page=per_page)
    return render_template(
        'invoice/head.html', 
        title='InvoiceHead', 
        invoice_head_create_form=invoice_head_create_form, 
        invoice_head_update_form=invoice_head_update_form,
        invoice_heads=invoice_heads,
        vehicles=vehicles,
        employees=employees,
        washbays=washbays,
        query=query
    )

@invoice_blueprint.route("/app/item_invoice/head", methods=['GET', 'POST'])
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

@invoice_blueprint.route("/app/invoice/head/create", methods=['GET', 'POST'])
@login_required
def insert_invoice_head():
    form = InvoiceHeadCreateForm()
    if request.method == 'GET':
        vehicles = Vehicle.query.all()
        employees = Employee.query.all()
        washbays = WashBay.query.all()
        return render_template(
            'invoice/create.html', 
            title='Create Invoice',
            form=form,
            vehicles=vehicles,
            employees=employees,
            washbays=washbays,
        )
    elif form.validate_on_submit():
        try:
            from utils.database import safe_insert_with_sequence_check
            vehicle = Vehicle.query.get(form.vehicle_id.data)
            invoice = safe_insert_with_sequence_check(
                InvoiceHead,
                customer_id=vehicle.owner.id,
                vehicle_id=form.vehicle_id.data,
                washbay_id=form.washbay_id.data,
                employee_id=form.employee_id.data,
                current_milage=form.current_milage.data,
                next_milage=form.current_milage.data,
                payment_method='cash'
            )

            invoice_status_log = safe_insert_with_sequence_check(
                InvoiceStatusLog,
                invoice_id=invoice.id,
                service_status=invoice.service_status,
                employee_id=invoice.employee_id
            )
            
            return redirect(url_for('invoice_blueprint.invoice_head_detail', invoice_head_id=invoice.id))
        except Exception as e:
            flash(f"Error: Invoice creation failed: {str(e)}", category='danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error: {field} - {error}", category='danger')
    return redirect(url_for('invoice_blueprint.invoice_head'))

@invoice_blueprint.route("/app/item_invoice/head/create", methods=['GET', 'POST'])
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
        try:
            from utils.database import safe_insert_with_sequence_check
            # Use customer_id if available, otherwise parse from customer field
            customer_id = request.form.get('customer_id')
            if customer_id:
                customer = Customer.query.get(int(customer_id))
            else:
                customer = Customer.query.get(int(utils.get_id(form.customer.data)))
            
            item_invoice = safe_insert_with_sequence_check(
                ItemInvoiceHead,
                customer_id=customer.id
            )
            return redirect(url_for('invoice_blueprint.item_invoice_head_detail', item_invoice_head_id=item_invoice.id))
        except Exception as e:
            flash(f"Error: Item Invoice create failed: {str(e)}", category='danger')
    else:
        flash("Error: Item Invoice create failed - form validation failed!", category='danger')
    return redirect(url_for('invoice_blueprint.item_invoice_head'))

@invoice_blueprint.route("/app/item_invoice/head/create/quick", methods=['GET'])
@login_required
def create_quick_item_invoice():
    """Create a quick item invoice with General Customer and redirect to update page"""
    try:
        # Check if General Customer exists, if not create it
        general_customer = Customer.query.filter_by(id=-1).first()
        if not general_customer:
            general_customer = Customer(
                id=-1,
                name="General Customer",
                contact="0000000000",
                address="Walk-in Customer",
                email="general@harithma.com"
            )
            db.session.add(general_customer)
            db.session.commit()
        
        # Create item invoice with General Customer
        from utils.database import safe_insert_with_sequence_check
        item_invoice = safe_insert_with_sequence_check(
            ItemInvoiceHead,
            customer_id=general_customer.id
        )
        
        # Redirect directly to the update page
        return redirect(url_for('invoice_blueprint.item_invoice_head_detail', item_invoice_head_id=item_invoice.id))
        
    except Exception as e:
        flash(f"Error: Quick Item Invoice create failed: {str(e)}", category='danger')
        return redirect(url_for('dashboard_blueprint.dashboard'))

@invoice_blueprint.route("/app/invoice/head/<int:invoice_head_id>", methods=['GET', 'POST'])
@login_required
def invoice_head_detail(invoice_head_id):
    invoice_head_update_form = InvoiceHeadUpdateForm()
    invoice_detail_create_form = InvoiceDetailCreateForm()

    items = Item.query.all()
    employees = Employee.query.all()
    washbays = WashBay.query.all()

    invoice_head = InvoiceHead.query.get_or_404(invoice_head_id)
    invoice_details = InvoiceDetail.query.filter(InvoiceDetail.invoice_head_id==invoice_head_id)
    previous_invoice_status = InvoiceStatusLog.query.filter(InvoiceStatusLog.invoice_id == invoice_head.id, InvoiceStatusLog.service_status == invoice_head.service_status).order_by(desc(InvoiceStatusLog.created_dttm)).first()
    previous_invoice_status_id = previous_invoice_status.id if previous_invoice_status else None
    previous_service_status_id = previous_invoice_status.service_status if previous_invoice_status else 0

    if invoice_head_update_form.validate_on_submit():
        if not invoice_head_update_form.cancel_invoice.data:
            # Use hidden field values if available, otherwise try to parse the display text
            employee_id = request.form.get('employee_id')
            washbay_id = request.form.get('washbay_id')
            
            if employee_id:
                invoice_head.employee_id = int(employee_id)
            else:
                try:
                    invoice_head.employee_id = utils.get_id(invoice_head_update_form.employee.data)
                except (ValueError, AttributeError):
                    # If parsing fails, keep the current employee
                    pass
            
            if washbay_id:
                invoice_head.washbay_id = int(washbay_id)
            else:
                try:
                    invoice_head.washbay_id = utils.get_id(invoice_head_update_form.washbay.data)
                except (ValueError, AttributeError):
                    # If parsing fails, keep the current washbay
                    pass
            invoice_head.current_milage=invoice_head_update_form.current_milage.data
            invoice_head.next_milage_in=invoice_head_update_form.next_milage_in.data
            invoice_head.service_status=invoice_head_update_form.service_status.data
            invoice_head.payment_method=invoice_head_update_form.payment_method.data
            invoice_head.paid_amount=invoice_head_update_form.paid_amount.data
            invoice_head.discount_amount=invoice_head_update_form.discount_amount.data
            invoice_head.remaining_amount = invoice_head.gross_price-invoice_head.paid_amount
            invoice_head.update_dttm = datetime.now()

            if invoice_head_update_form.next_milage_in.data:
                invoice_head.next_milage = invoice_head.next_milage_in + invoice_head.current_milage

            if str(previous_service_status_id).strip() != str(invoice_head.service_status).strip():
                from utils.database import safe_insert_with_sequence_check
                invoice_status_log = safe_insert_with_sequence_check(
                    InvoiceStatusLog,
                    previous_invoice_status_log_id=previous_invoice_status_id,
                    invoice_id=invoice_head.id,
                    service_status=invoice_head.service_status,
                    employee_id=invoice_head.employee_id
                )
            
            if invoice_head.paid_amount:
                invoice_head.last_payment_date = datetime.now()
            
            # Commit all changes after all updates are complete
            db.session.commit()

            if invoice_head_update_form.send_service_start_msg.data:
                invoice_head.service_start_msg_sent_ind = True
                db.session.commit()

                token = invoice_head.get_customer_view_token()
                msg = f"Hi {invoice_head.vehicle.owner.name}, Your vehicle {invoice_head.vehicle.number}'s service has been started. For more details please view: {url_for('dashboard_blueprint.customer_invoice', token=token, _external=True)}"
                utils.send_sms(invoice_head.vehicle.owner.contact, msg)

            elif invoice_head_update_form.send_service_complete_msg.data:
                invoice_head.service_complete_msg_sent_ind = True
                db.session.commit()
                
                token = invoice_head.get_customer_view_token()
                msg = f"Hi {invoice_head.vehicle.owner.name}, Your vehicle {invoice_head.vehicle.number}'s service has been completed."
                utils.send_sms(invoice_head.vehicle.owner.contact, msg)

            elif invoice_head_update_form.complete_invoice.data:
                invoice_head.service_status = 4
                from utils.database import safe_insert_with_sequence_check
                payment = safe_insert_with_sequence_check(
                    Payment,
                    invoice_id=invoice_head_id,
                    payment_method="cash",
                    payment_direction="in",
                    payment_amount=invoice_head.paid_amount,
                    payment_type='general',
                    remarks='Initial Payment',
                )
                update_total_values(invoice_head)
                service_invoice_json = convert_service_invoice_to_json(invoice_head)
                utils.send_print_invoice(service_invoice_json,'harithmaq')
                return redirect(url_for('dashboard_blueprint.dashboard'))

        else:
            db.session.delete(invoice_head)
            db.session.commit()
            flash("Invoice deleted.", category='warning')
            return redirect(url_for('invoice_blueprint.invoice_head'))

    elif request.method == 'POST':
        flash("Invoice update failed!", category='danger')

    if invoice_head.service_complete_msg_sent_ind:
        invoice_head_update_form.send_service_start_msg.render_kw = {'disabled': 'disabled'}
        invoice_head_update_form.send_service_complete_msg.render_kw = {'disabled': 'disabled'}
    elif invoice_head.service_start_msg_sent_ind:
        invoice_head_update_form.send_service_start_msg.render_kw = {'disabled': 'disabled'}
        invoice_head_update_form.send_service_complete_msg.render_kw = {}
    else:
        invoice_head_update_form.send_service_start_msg.render_kw = {}
        invoice_head_update_form.send_service_complete_msg.render_kw = {'disabled': 'disabled'}

    update_total_values(invoice_head)
    return render_template(
            'invoice/update.html', 
            title='Invoice', 
            invoice_head=invoice_head,
            invoice_head_update_form=invoice_head_update_form,
            invoice_detail_create_form=invoice_detail_create_form,
            items=items,
            employees=employees,
            washbays=washbays,
            invoice_details=invoice_details,
            service_status_form_list=config.SERVICE_STATUS_FORM_LIST,
            payment_method_form_list=config.PAYMENT_METHOD_FORM_LIST,
        )

@invoice_blueprint.route("/app/item_invoice/head/<int:item_invoice_head_id>", methods=['GET', 'POST'])
@login_required
def item_invoice_head_detail(item_invoice_head_id):
    item_invoice_head_update_form = ItemInvoiceHeadUpdateForm()
    item_invoice_detail_create_form = InvoiceDetailCreateForm()

    items = Item.query.all()
    customers = Customer.query.all()

    item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_head_id)
    item_invoice_details = ItemInvoiceDetail.query.filter(ItemInvoiceDetail.item_invoice_head_id==item_invoice_head_id)

    if item_invoice_head_update_form.validate_on_submit():
        # Use hidden field value if available, otherwise try to parse the display text
        customer_id = request.form.get('customer_id')
        
        if customer_id:
            item_invoice_head.customer_id = int(customer_id)
        else:
            try:
                customer = Customer.query.get(int(utils.get_id(item_invoice_head_update_form.customer.data)))
                item_invoice_head.customer_id = customer.id
            except (ValueError, AttributeError):
                # If parsing fails, keep the current customer
                pass
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

        if item_invoice_head_update_form.complete_item_invoice.data:
            item_invoice_json = convert_item_invoice_to_json(item_invoice_head)
            utils.send_print_invoice(item_invoice_json,'harithmaq')
            return redirect(url_for('dashboard_blueprint.dashboard'))

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
            item_invoice_details=item_invoice_details,
            payment_method_form_list=config.PAYMENT_METHOD_FORM_LIST
        )

@invoice_blueprint.route('/app/invoice/head/<int:invoice_head_id>/delete', methods = ['GET', 'POST'])
@login_required
def delete_invoice_head(invoice_head_id):
    invoice_head = InvoiceHead.query.get_or_404(invoice_head_id)
    db.session.delete(invoice_head)
    db.session.commit()
    flash("InvoiceHead is deleted!", category='success')
    return redirect(url_for('invoice_blueprint.invoice_head'))

@invoice_blueprint.route('/app/item_invoice/head/<int:item_invoice_head_id>/delete', methods = ['GET', 'POST'])
@login_required
def delete_item_invoice_head(item_invoice_head_id):
    item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_head_id)
    db.session.delete(item_invoice_head)
    db.session.commit()
    flash("Success: Invoice is deleted!", category='success')
    return redirect(url_for('invoice_blueprint.item_invoice_head'))

@invoice_blueprint.route("/app/invoice/detail/add/<int:invoice_head_id>", methods=['GET', 'POST'])
@login_required
def add_invoice_detail(invoice_head_id):
    invoice_detail_create_form = InvoiceDetailCreateForm()
    if invoice_detail_create_form.validate_on_submit():
        item_id = invoice_detail_create_form.item_id.data
        quantity = invoice_detail_create_form.quantity.data
        discount_amount = invoice_detail_create_form.discount_amount.data or 0

        item = Item.query.get_or_404(item_id)
        invoice_head = InvoiceHead.query.get_or_404(invoice_head_id)

        item.quantity -= quantity
        item_discount_amount = item.discount_pct*item.unit_price*quantity/100
        total_item_cost = item.unit_cost*quantity
        total_item_price = item.unit_price*quantity
        total_item_discount = (discount_amount or 0)+item_discount_amount
        total_gross_price = total_item_price-total_item_discount

        invoice_detail = InvoiceDetail(
            invoice_head_id = invoice_head_id,
            item_id = item_id,
            quantity = quantity,
            total_cost = total_item_cost,
            total_price = total_item_price,
            discount_amount = total_item_discount or 0,
            gross_price = total_gross_price
        )

        try:
            from utils.database import safe_insert_with_sequence_check
            safe_insert_with_sequence_check(
                InvoiceDetail,
                invoice_head_id=invoice_head_id,
                item_id=item_id,
                quantity=quantity,
                total_cost=total_item_cost,
                total_price=total_item_price,
                discount_amount=total_item_discount or 0,
                gross_price=total_gross_price
            )
            update_total_values(invoice_head)
        except Exception as e:
            flash(f"Invoice Item failed to add: {str(e)}", category='danger')
    else:
        flash("Invoice Item failed to add - form validation failed!", category='danger')
    return redirect(url_for('invoice_blueprint.invoice_head_detail',invoice_head_id=invoice_head_id))

@invoice_blueprint.route("/app/item_invoice/detail/add/<int:item_invoice_head_id>", methods=['GET', 'POST'])
@login_required
def add_item_invoice_detail(item_invoice_head_id):
    item_invoice_detail_create_form = InvoiceDetailCreateForm()
    if item_invoice_detail_create_form.validate_on_submit():
        item_id = utils.get_id(item_invoice_detail_create_form.item.data)
        quantity = item_invoice_detail_create_form.quantity.data
        discount_amount = item_invoice_detail_create_form.discount_amount.data

        item = Item.query.get_or_404(item_id)
        item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_head_id)

        item.quantity -= quantity
        item_discount_amount = item.discount_pct*item.unit_price*quantity/100
        total_item_cost = item.unit_cost*quantity
        total_item_price = item.unit_price*quantity
        total_item_discount = (discount_amount or 0)+item_discount_amount
        total_gross_price = total_item_price-total_item_discount

        try:
            from utils.database import safe_insert_with_sequence_check
            safe_insert_with_sequence_check(
                ItemInvoiceDetail,
                item_invoice_head_id=item_invoice_head_id,
                item_id=item_id,
                quantity=quantity,
                total_cost=total_item_cost,
                total_price=total_item_price,
                discount_amount=(discount_amount or 0)+item_discount_amount,
                gross_price=total_gross_price
            )
            update_total_values(item_invoice_head)
        except Exception as e:
            flash(f"Item Invoice Item failed to add: {str(e)}", category='danger')

        print(f"{item_invoice_head.total_cost=}")

    else:
        flash("Item Invoice Item failed to add!", category='danger')
    return redirect(url_for('invoice_blueprint.item_invoice_head_detail',item_invoice_head_id=item_invoice_head_id))

@invoice_blueprint.route("/app/invoice/detail/delete/<int:invoice_detail_id>", methods=['GET', 'POST'])
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

@invoice_blueprint.route("/app/item_invoice/detail/delete/<int:item_invoice_detail_id>", methods=['GET', 'POST'])
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

@invoice_blueprint.route("/app/invoice/detail/quantity/add/<int:invoice_detail_id>", methods=['GET', 'POST'])
@login_required
def increase_quantity_invoice_detail(invoice_detail_id):

    invoice_detail = InvoiceDetail.query.get_or_404(invoice_detail_id)
    invoice_head = InvoiceHead.query.get_or_404(invoice_detail.invoice_head_id)
    item = Item.query.get_or_404(invoice_detail.item.id)

    item.quantity -= 1
    invoice_detail.quantity += 1
    db.session.commit()

    update_invoice_detail_values(invoice_detail)
    update_total_values(invoice_head)

    return redirect(url_for('invoice_blueprint.invoice_head_detail',invoice_head_id=invoice_detail.invoice_head_id))

@invoice_blueprint.route("/app/item_invoice/detail/quantity/add/<int:item_invoice_detail_id>", methods=['GET', 'POST'])
@login_required
def increase_quantity_item_invoice_detail(item_invoice_detail_id):

    item_invoice_detail = ItemInvoiceDetail.query.get_or_404(item_invoice_detail_id)
    item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_detail.item_invoice_head_id)
    item = Item.query.get_or_404(item_invoice_detail.item.id)

    item.quantity -= 1
    item_invoice_detail.quantity += 1
    db.session.commit()

    update_invoice_detail_values(item_invoice_detail)
    update_total_values(item_invoice_head)

    return redirect(url_for('invoice_blueprint.item_invoice_head_detail',item_invoice_head_id=item_invoice_detail.item_invoice_head_id))

@invoice_blueprint.route("/app/invoice/detail/quantity/remove/<int:invoice_detail_id>", methods=['GET', 'POST'])
@login_required
def decrease_quantity_invoice_detail(invoice_detail_id):
    invoice_detail = InvoiceDetail.query.get_or_404(invoice_detail_id)
    invoice_head = InvoiceHead.query.get_or_404(invoice_detail.invoice_head_id)
    item = Item.query.get_or_404(invoice_detail.item.id)

    if invoice_detail.quantity > 1:
        item.quantity += 1
        invoice_detail.quantity -= 1
        db.session.commit()
    else:
        flash("Quantity should be at leaset one!", category='warning')

    update_invoice_detail_values(invoice_detail)
    update_total_values(invoice_head)

    return redirect(url_for('invoice_blueprint.invoice_head_detail',invoice_head_id=invoice_detail.invoice_head_id))

@invoice_blueprint.route("/app/item_invoice/detail/quantity/remove/<int:item_invoice_detail_id>", methods=['GET', 'POST'])
@login_required
def decrease_quantity_item_invoice_detail(item_invoice_detail_id):
    item_invoice_detail = ItemInvoiceDetail.query.get_or_404(item_invoice_detail_id)
    item_invoice_head = ItemInvoiceHead.query.get_or_404(item_invoice_detail.item_invoice_head_id)
    item = Item.query.get_or_404(item_invoice_detail.item.id)

    if item_invoice_detail.quantity > 1:
        item.quantity += 1
        item_invoice_detail.quantity -= 1
        db.session.commit()
    else:
        flash("Quantity should be at leaset one!", category='warning')

    update_invoice_detail_values(item_invoice_detail)
    update_total_values(item_invoice_head)

    return redirect(url_for('invoice_blueprint.item_invoice_head_detail',item_invoice_head_id=item_invoice_detail.item_invoice_head_id))

# supporting fuctions

@invoice_blueprint.app_template_filter('format_quantity')
def format_quantity(value):
    if value is None:
        return ''
    return f"{float(value):g}"  # Removes trailing zeros and shows decimals only if necessary


def update_total_values(invoice_head):
    if isinstance(invoice_head,InvoiceHead):
        total_item_cost = db.session.query(func.sum(InvoiceDetail.total_cost)).filter(InvoiceDetail.invoice_head_id == invoice_head.id).one()[0]
        total_item_price = db.session.query(func.sum(InvoiceDetail.total_price)).filter(InvoiceDetail.invoice_head_id == invoice_head.id).one()[0]
        total_item_discount = (db.session.query(func.sum(InvoiceDetail.discount_amount)).filter(InvoiceDetail.invoice_head_id == invoice_head.id).one()[0] or 0)
        total_item_gross_price = db.session.query(func.sum(InvoiceDetail.gross_price)).filter(InvoiceDetail.invoice_head_id == invoice_head.id).one()[0]
    else:
        total_item_cost = db.session.query(func.sum(ItemInvoiceDetail.total_cost)).filter(ItemInvoiceDetail.item_invoice_head_id == invoice_head.id).one()[0]
        total_item_price = db.session.query(func.sum(ItemInvoiceDetail.total_price)).filter(ItemInvoiceDetail.item_invoice_head_id == invoice_head.id).one()[0]
        total_item_discount = (db.session.query(func.sum(ItemInvoiceDetail.discount_amount)).filter(ItemInvoiceDetail.item_invoice_head_id == invoice_head.id).one()[0] or 0)
        total_item_gross_price = db.session.query(func.sum(ItemInvoiceDetail.gross_price)).filter(ItemInvoiceDetail.item_invoice_head_id == invoice_head.id).one()[0]

    total_discount = (total_item_discount or 0) + (invoice_head.discount_amount or 0)
    total_gross_price = (total_item_gross_price or 0) - (invoice_head.discount_amount or 0)

    invoice_head.total_cost = total_item_cost or 0
    invoice_head.total_price = total_item_price or 0
    invoice_head.total_discount = total_discount
    invoice_head.gross_price = total_gross_price

    db.session.commit()

def update_invoice_detail_values(invoice_detail):
    total_discount = (invoice_detail.discount_amount or 0)+(invoice_detail.item.discount_pct*invoice_detail.item.unit_price*invoice_detail.quantity/100 or 0)

    invoice_detail.total_cost = invoice_detail.item.unit_cost*invoice_detail.quantity
    invoice_detail.total_price = invoice_detail.item.unit_price*invoice_detail.quantity
    invoice_detail.gross_price = invoice_detail.total_price-total_discount

    db.session.commit()

def convert_item_invoice_to_json(item_invoice):
    invoice_dictionary = {
        "invoice_number": item_invoice.id,  
        "invoice_type": 2,
        "total_price": item_invoice.total_price,
        "discount_amount": item_invoice.discount_amount,
        "gross_price": item_invoice.gross_price,
        "paid_amount": item_invoice.paid_amount,
        "invoice_details": []
    }

    for detail in item_invoice.invoice_details:
        item_detail = {
            'item_name': detail.item.name,
            'unit_price': detail.item.unit_price,  # Assuming unit price is calculated as total price divided by quantity
            'quantity': detail.quantity,
            'total_price': detail.total_price,
            'discount_pct': detail.item.discount_pct
        }
        invoice_dictionary['invoice_details'].append(item_detail)

    return json.dumps(invoice_dictionary, cls=utils.DecimalEncoder)

def convert_service_invoice_to_json(service_invoice):
    invoice_dictionary = {
        "invoice_number": service_invoice.id,  
        "invoice_type": 1,
        "customer_name": service_invoice.customer.name,
        "employee_name": service_invoice.employee.name,
        "vehicle_number": service_invoice.vehicle.number,
        "wash_bay": service_invoice.washbay.name,
        "current_milage": service_invoice.current_milage,
        "next_milage": service_invoice.next_milage,
        "total_price": service_invoice.total_price,
        "total_discount": service_invoice.total_discount,
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