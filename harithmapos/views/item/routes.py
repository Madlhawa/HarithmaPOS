from flask_login import login_required
from flask import Blueprint, render_template, request, redirect, url_for, flash

from harithmapos import db
from harithmapos.models import Item
from harithmapos.views.item.forms import ItemCreateForm, ItemUpdateForm

item_blueprint = Blueprint('item_blueprint', __name__)

@item_blueprint.route("/app/item", methods=['GET', 'POST'])
@login_required
def item():
    item_create_form = ItemCreateForm()
    item_update_form = ItemUpdateForm()

    per_page = 20
    page = request.args.get('page',1,type=int)
    query = request.args.get("query",None)

    if query:
        items = Item.query.order_by(Item.update_dttm.desc()).filter(Item.name.icontains(query)).paginate(page=page, per_page=per_page)
    else:
        items = Item.query.order_by(Item.update_dttm.desc()).paginate(page=page, per_page=per_page)
    return render_template(
        'item.html', 
        title='Item', 
        item_create_form=item_create_form, 
        item_update_form=item_update_form,
        items=items,
        query=query
    )

@item_blueprint.route("/app/item/create", methods=['GET', 'POST'])
@login_required
def insert_item():
    item_create_form = ItemCreateForm()
    if item_create_form.validate_on_submit():
        item = Item(
            name = item_create_form.name.data,
            description = item_create_form.description.data,
            unit_of_measure = item_create_form.unit_of_measure.data,
            quantity = item_create_form.quantity.data,
            unit_cost = item_create_form.unit_cost.data,
            unit_price = item_create_form.unit_price.data,
            discount_pct = item_create_form.discount_pct.data
        )
        db.session.add(item)
        db.session.commit()
        flash("Item added successfully!", category='success')
    else:
        flash("Item failed to add!", category='danger')
    return redirect(url_for('item_blueprint.item'))

@item_blueprint.route("/app/item/<int:item_id>/update", methods=['GET', 'POST'])
@login_required
def update_item(item_id):
    item_update_form = ItemUpdateForm()
    if item_update_form.validate_on_submit():
        item = Item.query.get_or_404(item_id)
        item.name = item_update_form.name.data
        item.description = item_update_form.description.data
        item.unit_of_measure = item_update_form.unit_of_measure.data
        item.quantity = item_update_form.quantity.data
        item.unit_cost = item_update_form.unit_cost.data
        item.unit_price = item_update_form.unit_price.data
        item.discount_pct = item_update_form.discount_pct.data
        db.session.commit()
        flash("Suppler is updated!", category='success')
    else:
        flash("Suppler failed to add!", category='danger')
    return redirect(url_for('item_blueprint.item'))

@item_blueprint.route('/app/item/<int:item_id>/delete', methods = ['GET', 'POST'])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Item is deleted!", category='success')
    return redirect(url_for('item_blueprint.item'))
