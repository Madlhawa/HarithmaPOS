import logging

from sqlalchemy import or_
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user

from harithmapos import db, config
from harithmapos.billing import money, to_decimal
from harithmapos.timeutils import utcnow
from harithmapos.models import PurchaseOrderHead, PurchaseOrderDetail, Supplier, Item
from harithmapos import documents, ledger, lines, stock
from harithmapos.views.purchase_order.forms import (
    PurchaseOrderHeadCreateForm, PurchaseOrderHeadUpdateForm, PurchaseOrderDetailCreateForm,
)
from harithmapos.permissions import owner_required

import harithmapos.views.utils as utils

logger = logging.getLogger(__name__)

purchase_order_blueprint = Blueprint('purchase_order_blueprint', __name__)

PER_PAGE = 20


@purchase_order_blueprint.route("/app/purchase_order/head", methods=['GET'])
@owner_required
def purchase_order_head():
    page = request.args.get('page', 1, type=int)
    query = (request.args.get('query') or '').strip()

    orders = PurchaseOrderHead.query
    if query:
        pattern = f"%{query}%"
        conditions = [Supplier.name.ilike(pattern), PurchaseOrderHead.supplier_invoice_id.ilike(pattern)]
        if query.isdigit():
            conditions.append(PurchaseOrderHead.id == int(query))
        orders = (
            orders
            .join(Supplier, PurchaseOrderHead.supplier_id == Supplier.id)
            .filter(or_(*conditions))
        )
    purchase_order_heads = orders.order_by(PurchaseOrderHead.id.desc()).paginate(page=page, per_page=PER_PAGE)
    return render_template(
        'purchase_order/head.html',
        title='Purchase orders',
        purchase_order_heads=purchase_order_heads,
        query=query,
    )


@purchase_order_blueprint.route("/app/purchase_order/head/create", methods=['GET', 'POST'])
@owner_required
def insert_purchase_order_head():
    form = PurchaseOrderHeadCreateForm()
    if request.method == 'GET':
        return render_template('purchase_order/create.html', title='New purchase order')

    if not form.validate_on_submit():
        utils.flash_form_errors(form)
        return utils.redirect_back('purchase_order_blueprint.purchase_order_head')

    supplier = db.session.get(Supplier, form.supplier_id.data)
    if supplier is None:
        flash("Choose the supplier from the list.", category='danger')
        return utils.redirect_back('purchase_order_blueprint.purchase_order_head')

    try:
        purchase_order = PurchaseOrderHead(
            supplier_id=supplier.id,
            supplier_invoice_id=form.supplier_invoice_id.data,
        )
        db.session.add(purchase_order)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Could not create purchase order")
        flash("The purchase order could not be created. Please try again.", category='danger')
        return utils.redirect_back('purchase_order_blueprint.purchase_order_head')
    return redirect(url_for('purchase_order_blueprint.purchase_order_head_detail',
                            purchase_order_head_id=purchase_order.id))


@purchase_order_blueprint.route("/app/purchase_order/head/<int:purchase_order_head_id>", methods=['GET', 'POST'])
@owner_required
def purchase_order_head_detail(purchase_order_head_id):
    form = PurchaseOrderHeadUpdateForm()
    purchase_order_head = PurchaseOrderHead.query.get_or_404(purchase_order_head_id)
    here = url_for('purchase_order_blueprint.purchase_order_head_detail',
                   purchase_order_head_id=purchase_order_head.id)

    if request.method == 'POST':
        if not form.validate_on_submit():
            utils.flash_form_errors(form)
            return redirect(here)

        if purchase_order_head.is_void:
            flash(f"Purchase order #{purchase_order_head.id} is void and cannot be changed.", category='warning')
            return redirect(here)

        try:
            purchase_order_head.supplier_invoice_id = form.supplier_invoice_id.data   # a reference: always editable
            purchase_order_head.update_dttm = utcnow()
            if purchase_order_head.is_draft:
                if form.supplier_id.data is not None:
                    supplier = db.session.get(Supplier, form.supplier_id.data)
                    if supplier:
                        purchase_order_head.supplier_id = supplier.id
                purchase_order_head.discount_pct = form.discount_pct.data or 0
                lines.recalculate(purchase_order_head)
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("Could not save purchase order %s", purchase_order_head_id)
            flash("The purchase order could not be saved. Please try again.", category='danger')
            return redirect(here)

        if form.complete_purchase_order.data:
            try:
                documents.complete(purchase_order_head, current_user)
                db.session.commit()
            except documents.DocumentError as exc:
                db.session.rollback()
                flash(str(exc), category='warning')
                return redirect(here)
            _pay_on_completion(purchase_order_head, form)
            return redirect(url_for('purchase_order_blueprint.purchase_order_head'))

        if form.paid_now.data:
            flash("Saved. The amount paid is recorded only when you press Complete.", category='info')
        else:
            flash("Purchase order saved.", category='success')
        return redirect(here)

    purchase_order_details = lines.recalculate(purchase_order_head)
    db.session.commit()
    return render_template(
        'purchase_order/update.html',
        title=f"Purchase order #{purchase_order_head.id}",
        purchase_order_head=purchase_order_head,
        purchase_order_details=purchase_order_details,
    )


@purchase_order_blueprint.route('/app/purchase_order/head/<int:purchase_order_head_id>/void', methods=['POST'])
@owner_required
def void_purchase_order_head(purchase_order_head_id):
    order = db.get_or_404(PurchaseOrderHead, purchase_order_head_id)
    here = url_for('purchase_order_blueprint.purchase_order_head_detail', purchase_order_head_id=order.id)
    try:
        documents.void(order, request.form.get('reason'), current_user)
        db.session.commit()
    except documents.DocumentError as exc:
        db.session.rollback()
        flash(str(exc), category='warning')
        return redirect(here)
    except Exception:
        db.session.rollback()
        logger.exception("Could not void purchase order %s", order.id)
        flash("It could not be voided. Please try again.", category='danger')
        return redirect(here)
    flash(f"Purchase order #{order.id} is void. Its items came back off stock.", category='warning')
    return redirect(here)


def _order_page(order_id):
    return redirect(url_for('purchase_order_blueprint.purchase_order_head_detail', purchase_order_head_id=order_id))


def _apply(order, change, failure):
    """Run one change to the lines and commit, or roll back and say why."""
    try:
        change()
        db.session.commit()
    except (documents.DocumentError, stock.StockError) as exc:
        db.session.rollback()
        flash(str(exc), category='warning')
    except Exception:
        db.session.rollback()
        logger.exception("Purchase order #%s: %s", order.id, failure)
        flash(f"{failure} Please try again.", category='danger')
    return _order_page(order.id)


@purchase_order_blueprint.route("/app/purchase_order/detail/add/<int:purchase_order_head_id>", methods=['POST'])
@owner_required
def add_purchase_order_detail(purchase_order_head_id):
    order = db.get_or_404(PurchaseOrderHead, purchase_order_head_id)
    form = PurchaseOrderDetailCreateForm()
    if not form.validate_on_submit():
        utils.flash_form_errors(form)
        return _order_page(order.id)
    item = db.session.get(Item, form.item_id.data)
    if item is None:
        flash("Choose the item from the list.", category='danger')
        return _order_page(order.id)
    return _apply(order, lambda: lines.add_purchase_line(order, item, form.quantity.data, form.unit_cost.data),
                  "The item could not be added.")


@purchase_order_blueprint.route("/app/purchase_order/detail/delete/<int:purchase_order_detail_id>", methods=['POST'])
@owner_required
def delete_purchase_order_detail(purchase_order_detail_id):
    line = db.get_or_404(PurchaseOrderDetail, purchase_order_detail_id)
    order = lines.head_of(line)
    return _apply(order, lambda: lines.remove_line(order, line), "The item could not be removed.")


@purchase_order_blueprint.route("/app/purchase_order/detail/quantity/add/<int:purchase_order_detail_id>", methods=['POST'])
@owner_required
def increase_quantity_purchase_order_detail(purchase_order_detail_id):
    return _step_line(purchase_order_detail_id, 1)


@purchase_order_blueprint.route("/app/purchase_order/detail/quantity/remove/<int:purchase_order_detail_id>", methods=['POST'])
@owner_required
def decrease_quantity_purchase_order_detail(purchase_order_detail_id):
    return _step_line(purchase_order_detail_id, -1)


def _step_line(purchase_order_detail_id, step):
    line = db.get_or_404(PurchaseOrderDetail, purchase_order_detail_id)
    order = lines.head_of(line)
    return _apply(order, lambda: lines.change_quantity(order, line, step), "The quantity could not be changed.")


def _pay_on_completion(order, form):
    """Record what was paid to the supplier when the order was completed."""
    paid = money(to_decimal(form.paid_now.data or 0))
    label = f"Purchase order #{order.id} completed."
    if paid <= 0:
        flash(label, category='success')
        return
    method = form.payment_method.data if form.payment_method.data in ledger.METHODS else 'cash'
    try:
        ledger.pay_document(order, paid, method, user=current_user)
        db.session.commit()
    except ledger.LedgerError as exc:
        db.session.rollback()
        flash(f"{label} The payment was not recorded: {exc} Use Pay supplier on the order.", category='warning')
        return
    except Exception:
        db.session.rollback()
        logger.exception("Could not record the payment for purchase order %s", order.id)
        flash(f"{label} The payment could not be recorded: use Pay supplier on the order.", category='danger')
        return
    left = money(order.balance)
    flash(label + (f" Still to pay: {config.CURRENCY} {left:,.2f}." if left > 0 else " Paid in full."), category='success')
