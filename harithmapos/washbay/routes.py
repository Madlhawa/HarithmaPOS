from flask_login import login_required
from flask import Blueprint, render_template, request, redirect, url_for, flash

from harithmapos import db
from harithmapos.models import WashBay
from harithmapos.washbay.forms import WashBayCreateForm, WashBayUpdateForm

washbay_blueprint = Blueprint('washbay_blueprint', __name__)

@washbay_blueprint.route("/washbay", methods=['GET', 'POST'])
@login_required
def washbay():
    washbay_create_form = WashBayCreateForm()
    washbay_update_form = WashBayUpdateForm()

    per_page = 10
    page = request.args.get('page',1,type=int)
    query = request.args.get("query",None)

    if query:
        washbays = WashBay.query.order_by(WashBay.create_dttm.desc()).filter(WashBay.name.icontains(query)).paginate(page=page, per_page=per_page)
    else:
        washbays = WashBay.query.order_by(WashBay.create_dttm.desc()).paginate(page=page, per_page=per_page)
    return render_template(
        'washbay.html', 
        title='WashBay', 
        washbay_create_form=washbay_create_form, 
        washbay_update_form=washbay_update_form,
        washbays=washbays,
        query=query
    )

@washbay_blueprint.route("/washbay/create", methods=['GET', 'POST'])
@login_required
def insert_washbay():
    washbay_create_form = WashBayCreateForm()
    if washbay_create_form.validate_on_submit():
        washbay = WashBay(
            name = washbay_create_form.name.data,
            remarks = washbay_create_form.remarks.data,
            capacity = washbay_create_form.capacity.data
        )
        db.session.add(washbay)
        db.session.commit()
        flash("WashBay added successfully!", category='success')
    else:
        flash("WashBay failed to add!", category='danger')
    return redirect(url_for('washbay_blueprint.washbay'))

@washbay_blueprint.route("/washbay/<int:washbay_id>/update", methods=['GET', 'POST'])
@login_required
def update_washbay(washbay_id):
    washbay_update_form = WashBayUpdateForm()
    if washbay_update_form.validate_on_submit():
        washbay = WashBay.query.get_or_404(washbay_id)
        washbay.name = washbay_update_form.name.data
        washbay.remarks = washbay_update_form.remarks.data
        washbay.capacity = washbay_update_form.capacity.data
        db.session.commit()
        flash("Suppler is updated!", category='success')
    else:
        flash("Suppler failed to add!", category='danger')
    return redirect(url_for('washbay_blueprint.washbay'))

@washbay_blueprint.route('/washbay/<int:washbay_id>/delete', methods = ['GET', 'POST'])
@login_required
def delete_washbay(washbay_id):
    washbay = WashBay.query.get_or_404(washbay_id)
    db.session.delete(washbay)
    db.session.commit()
    flash("WashBay is deleted!", category='success')
    return redirect(url_for('washbay_blueprint.washbay'))
