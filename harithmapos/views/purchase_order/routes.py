import logging

from sqlalchemy import or_
from flask import Blueprint, render_template, request, redirect, url_for, flash

from harithmapos import db, config
from harithmapos.billing import money, purchase_totals, to_decimal
from harithmapos.timeutils import local_today, utcnow
from harithmapos.models import PurchaseOrderHead, PurchaseOrderDetail, Supplier, Item, Payment
from harithmapos.views.ledger import sync_document_payment
from harithmapos.views.purchase_order.forms import (
    PurchaseOrderHeadCreateForm, PurchaseOrderHeadUpdateForm, PurchaseOrderDetailCreateForm,
)
from harithmapos.permissions import owner_required

import harithmapos.views.utils as utils
from utils.database import safe_insert_with_sequence_check

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
        purchase_order = safe_insert_with_sequence_check(
            PurchaseOrderHead,
            supplier_id=supplier.id,
            supplier_invoice_id=form.supplier_invoice_id.data,
            payment_method='cash',
            remaining_amount=0,
        )
    except Exception:
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

        try:
            if form.supplier_id.data is not None:
                supplier = db.session.get(Supplier, form.supplier_id.data)
                if supplier:
                    purchase_order_head.supplier_id = supplier.id
            purchase_order_head.supplier_invoice_id = form.supplier_invoice_id.data
            purchase_order_head.payment_method = form.payment_method.data
            purchase_order_head.paid_amount = form.paid_amount.data or 0
            purchase_order_head.discount_pct = form.discount_pct.data or 0
            purchase_order_head.update_dttm = utcnow()
            _recalculate(purchase_order_head)
            if purchase_order_head.paid_amount:
                purchase_order_head.last_payment_date = local_today(config.APP_TIMEZONE)
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("Could not save purchase order %s", purchase_order_head_id)
            flash("The purchase order could not be saved. Please try again.", category='danger')
            return redirect(here)

        if form.complete_purchase_order.data:
            try:
                sync_document_payment(purchase_order_head, 'purchase_order_id', remarks='Purchase order payment')
                flash(f"Purchase order #{purchase_order_head.id} completed.", category='success')
            except Exception:
                db.session.rollback()
                logger.exception("Could not record payment for purchase order %s", purchase_order_head_id)
                flash("The purchase order is saved, but its payment could not be recorded. Press Complete again.",
                      category='danger')
                return redirect(here)
            return redirect(url_for('purchase_order_blueprint.purchase_order_head'))

        flash("Purchase order saved.", category='success')
        return redirect(here)

    purchase_order_details = _recalculate(purchase_order_head)
    db.session.commit()
    return render_template(
        'purchase_order/update.html',
        title=f"Purchase order #{purchase_order_head.id}",
        purchase_order_head=purchase_order_head,
        purchase_order_details=purchase_order_details,
    )


@purchase_order_blueprint.route('/app/purchase_order/head/<int:purchase_order_head_id>/delete', methods=['POST'])
@owner_required
def delete_purchase_order_head(purchase_order_head_id):
    purchase_order_head = PurchaseOrderHead.query.get_or_404(purchase_order_head_id)
    if Payment.query.filter(Payment.purchase_order_id == purchase_order_head.id).count():
        flash("This purchase order has payments recorded against it. Delete those on the Payments page first.",
              category='warning')
        return redirect(url_for('purchase_order_blueprint.purchase_order_head_detail',
                                purchase_order_head_id=purchase_order_head.id))
    try:
        details = PurchaseOrderDetail.query.filter(
            PurchaseOrderDetail.purchase_order_head_id == purchase_order_head.id).all()
        for detail in details:
            # The delivery is being un-done: take the stock back out.
            if detail.item is not None and detail.item.tracks_stock:
                detail.item.quantity = detail.item.quantity - detail.quantity
            db.session.delete(detail)
        db.session.delete(purchase_order_head)
        db.session.commit()
        flash("Purchase order deleted and its stock removed.", category='warning')
    except Exception:
        db.session.rollback()
        logger.exception("Could not delete purchase order %s", purchase_order_head_id)
        flash("The purchase order could not be deleted.", category='danger')
    return redirect(url_for('purchase_order_blueprint.purchase_order_head'))


@purchase_order_blueprint.route("/app/purchase_order/detail/add/<int:purchase_order_head_id>", methods=['POST'])
@owner_required
def add_purchase_order_detail(purchase_order_head_id):
    purchase_order_head = PurchaseOrderHead.query.get_or_404(purchase_order_head_id)
    here = redirect(url_for('purchase_order_blueprint.purchase_order_head_detail',
                            purchase_order_head_id=purchase_order_head_id))

    form = PurchaseOrderDetailCreateForm()
    if not form.validate_on_submit():
        utils.flash_form_errors(form)
        return here

    item = db.session.get(Item, form.item_id.data)
    if item is None:
        flash("Choose the item from the list.", category='danger')
        return here
    if not item.tracks_stock:
        flash(f"{item.name} is set up as a service with no stock. "
              "Give it a stock quantity on the Items page before buying it in.", category='warning')
        return here

    quantity = form.quantity.data
    unit_cost = form.unit_cost.data if form.unit_cost.data is not None else to_decimal(item.unit_cost)
    try:
        detail = PurchaseOrderDetail(
            purchase_order_head_id=purchase_order_head.id,
            item_id=item.id,
            quantity=quantity,
            total_cost=money(unit_cost * quantity),
            total_price=money(to_decimal(item.unit_price) * quantity),
            discount_pct=0,
        )
        db.session.add(detail)
        item.quantity = item.quantity + quantity
        # Remember what the item costs now, so profit on later sales is right.
        item.unit_cost = money(unit_cost)
        item.update_dttm = utcnow()
        db.session.flush()
        _recalculate(purchase_order_head)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Could not add an item to purchase order %s", purchase_order_head_id)
        flash("The item could not be added. Please try again.", category='danger')
    return here


@purchase_order_blueprint.route("/app/purchase_order/detail/delete/<int:purchase_order_detail_id>", methods=['POST'])
@owner_required
def delete_purchase_order_detail(purchase_order_detail_id):
    purchase_order_detail = PurchaseOrderDetail.query.get_or_404(purchase_order_detail_id)
    purchase_order_head = PurchaseOrderHead.query.get_or_404(purchase_order_detail.purchase_order_head_id)
    try:
        item = purchase_order_detail.item
        if item is not None and item.tracks_stock:
            item.quantity = item.quantity - purchase_order_detail.quantity
        db.session.delete(purchase_order_detail)
        db.session.flush()
        _recalculate(purchase_order_head)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Could not remove purchase order line %s", purchase_order_detail_id)
        flash("The item could not be removed. Please try again.", category='danger')
    return redirect(url_for('purchase_order_blueprint.purchase_order_head_detail',
                            purchase_order_head_id=purchase_order_head.id))


@purchase_order_blueprint.route("/app/purchase_order/detail/quantity/add/<int:purchase_order_detail_id>", methods=['POST'])
@owner_required
def increase_quantity_purchase_order_detail(purchase_order_detail_id):
    return _change_line_quantity(purchase_order_detail_id, 1)


@purchase_order_blueprint.route("/app/purchase_order/detail/quantity/remove/<int:purchase_order_detail_id>", methods=['POST'])
@owner_required
def decrease_quantity_purchase_order_detail(purchase_order_detail_id):
    return _change_line_quantity(purchase_order_detail_id, -1)


# supporting functions

def _change_line_quantity(purchase_order_detail_id, step):
    detail = PurchaseOrderDetail.query.get_or_404(purchase_order_detail_id)
    purchase_order_head = PurchaseOrderHead.query.get_or_404(detail.purchase_order_head_id)
    here = redirect(url_for('purchase_order_blueprint.purchase_order_head_detail',
                            purchase_order_head_id=purchase_order_head.id))

    if step < 0 and detail.quantity <= 1:
        flash("Quantity is already at the minimum. Remove the item instead.", category='warning')
        return here
    try:
        old_quantity = to_decimal(detail.quantity)
        new_quantity = old_quantity + step
        # Keep this line's own unit cost and price; the item's may have changed since.
        unit_cost = to_decimal(detail.total_cost) / old_quantity
        unit_price = to_decimal(detail.total_price) / old_quantity
        detail.quantity = new_quantity
        detail.total_cost = money(unit_cost * new_quantity)
        detail.total_price = money(unit_price * new_quantity)
        detail.update_dttm = utcnow()
        item = detail.item
        if item is not None and item.tracks_stock:
            item.quantity = item.quantity + step
        db.session.flush()
        _recalculate(purchase_order_head)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Could not change purchase order line %s", purchase_order_detail_id)
        flash("The quantity could not be changed. Please try again.", category='danger')
    return here


def _recalculate(purchase_order_head):
    """Recompute the head totals from its lines. Returns the lines. Does not commit."""
    details = (
        PurchaseOrderDetail.query
        .filter(PurchaseOrderDetail.purchase_order_head_id == purchase_order_head.id)
        .order_by(PurchaseOrderDetail.id)
        .all()
    )
    totals = purchase_totals(details, purchase_order_head.discount_pct, purchase_order_head.paid_amount)
    # total_cost is not a column on the head; it is set here for the screen to show.
    purchase_order_head.total_cost = totals['total_cost']
    purchase_order_head.total_price = totals['total_price']
    purchase_order_head.gross_price = totals['gross_price']
    purchase_order_head.remaining_amount = totals['remaining_amount']
    return details


def update_total_values(purchase_order_head):
    _recalculate(purchase_order_head)
    db.session.commit()
