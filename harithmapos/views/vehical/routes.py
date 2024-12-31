from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_required

from harithmapos import db
from harithmapos.models import Vehical
from harithmapos.views.vehical.forms import VehicalForm

vehical_blueprint = Blueprint('vehical_blueprint', __name__)

@vehical_blueprint.route('/app/insert_vehical/', methods = ['GET', 'POST'])
@login_required
def insert_vehical():
    form = VehicalForm()
    if form.validate_on_submit():
        vehical = Vehical( 
            number = form.number.data,
            make = form.make.data,
            model = form.model.data,
            year = form.year.data,
            owner_id = form.owner_id.data
        )
        db.session.add(vehical)
        db.session.commit()
        flash("Vehical added successfully!", category='success')
    else:
        flash("Vehical failed to add!", category='danger')
    return redirect(url_for('customer_blueprint.customer'))

@vehical_blueprint.route('/app/update_vehical/', methods = ['POST'])
@login_required
def update_vehical():
    form = VehicalForm()
    if form.validate_on_submit():
        vehical = db.session.get(Vehical, request.form.get('id'))
        vehical.number = form.number.data
        vehical.make = form.make.data
        vehical.model = form.model.data
        vehical.year = form.year.data
        vehical.owner_id = form.owner_id.data
        db.session.commit()
        flash("Vehical is updated!", category='success')
    else:
        flash("Vehical failed to add!", category='danger')
    return redirect(url_for('customer_blueprint.customer'))

@vehical_blueprint.route('/app/delete_vehical/<id>', methods = ['GET', 'POST'])
@login_required
def delete_vehical(id):
    vehical = Vehical.query.get(id)
    db.session.delete(vehical)
    db.session.commit()
    flash("Vehical is deleted!", category='success')
    return redirect(url_for('customer_blueprint.customer'))