import logging

from sqlalchemy import or_
from flask_login import login_required
from flask import Blueprint, render_template, request, flash

from harithmapos import db, stock
from harithmapos import settings as app_settings
from harithmapos.models import Item, StockMovement
from harithmapos.timeutils import utcnow
from harithmapos.views.item.forms import ItemCreateForm, ItemUpdateForm
from harithmapos.permissions import owner_required

import harithmapos.views.utils as utils

logger = logging.getLogger(__name__)

item_blueprint = Blueprint('item_blueprint', __name__)

PER_PAGE = 25


@item_blueprint.route("/app/item", methods=['GET'])
@login_required
def item():
    page = request.args.get('page', 1, type=int)
    query = (request.args.get('query') or '').strip()
    stock = request.args.get('stock', '')

    items = Item.query.filter(Item.is_archived if stock == 'archived' else ~Item.is_archived)
    if query:
        pattern = f"%{query}%"
        conditions = [Item.name.ilike(pattern), Item.description.ilike(pattern)]
        if query.isdigit():
            conditions.append(Item.id == int(query))
        items = items.filter(or_(*conditions))
    if stock == 'low':
        items = items.filter(Item.quantity.isnot(None), Item.quantity <= app_settings.low_stock_threshold())
    elif stock == 'services':
        items = items.filter(Item.quantity.is_(None))

    items = items.order_by(Item.name).paginate(page=page, per_page=PER_PAGE)
    return render_template('item.html', title='Items', items=items, query=query, stock=stock)


def _apply_form(item, form):
    item.name = form.name.data
    item.description = form.description.data
    item.unit_of_measure = form.unit_of_measure.data
    # An empty quantity means "not stock-tracked" (a service or labour charge).
    stock.set_count(item, form.quantity.data)
    item.unit_cost = form.unit_cost.data
    item.unit_price = form.unit_price.data
    item.discount_pct = form.discount_pct.data or 0


@item_blueprint.route("/app/item/create", methods=['POST'])
@owner_required
def insert_item():
    form = ItemCreateForm()
    if form.validate_on_submit():
        try:
            item = Item(
                name=form.name.data,
                description=form.description.data,
                unit_of_measure=form.unit_of_measure.data,
                unit_cost=form.unit_cost.data,
                unit_price=form.unit_price.data,
                discount_pct=form.discount_pct.data or 0,
            )
            stock.set_count(item, form.quantity.data)     # saves it, with its opening stock
            db.session.commit()
            flash(f"{form.name.data} added.", category='success')
        except Exception:
            db.session.rollback()
            logger.exception("Could not add item")
            flash("The item could not be added. Please try again.", category='danger')
    else:
        utils.flash_form_errors(form)
    return utils.redirect_back('item_blueprint.item')


@item_blueprint.route("/app/item/<int:item_id>/update", methods=['POST'])
@owner_required
def update_item(item_id):
    item = Item.query.get_or_404(item_id)
    form = ItemUpdateForm()
    if form.validate_on_submit():
        try:
            _apply_form(item, form)
            item.update_dttm = utcnow()
            db.session.commit()
            flash(f"{item.name} saved.", category='success')
        except Exception:
            db.session.rollback()
            logger.exception("Could not update item %s", item_id)
            flash("The item could not be saved. Please try again.", category='danger')
    else:
        utils.flash_form_errors(form)
    return utils.redirect_back('item_blueprint.item')


@item_blueprint.route('/app/item/<int:item_id>/archive', methods=['POST'])
@owner_required
def archive_item(item_id):
    item = db.get_or_404(Item, item_id)
    utils.archive_record(item, item.name)
    return utils.redirect_back('item_blueprint.item')


@item_blueprint.route('/app/item/<int:item_id>/restore', methods=['POST'])
@owner_required
def restore_item(item_id):
    item = db.get_or_404(Item, item_id)
    utils.restore_record(item, item.name)
    return utils.redirect_back('item_blueprint.item')


@item_blueprint.route('/app/item/<int:item_id>/stock', methods=['GET'])
@login_required
def item_stock(item_id):
    """Every change to an item's stock, newest first."""
    item = db.get_or_404(Item, item_id)
    page = request.args.get('page', 1, type=int)
    movements = (StockMovement.query.filter_by(item_id=item.id)
                 .order_by(StockMovement.id.desc())
                 .paginate(page=page, per_page=50))
    return render_template('item_stock.html', title=f"Stock of {item.name}", item=item,
                           movements=movements, kinds=stock.KINDS)
