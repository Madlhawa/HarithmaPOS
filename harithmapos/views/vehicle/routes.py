from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_required

from harithmapos import db
from harithmapos.models import Vehicle
from harithmapos.views.vehicle.forms import VehicleForm

vehicle_blueprint = Blueprint('vehicle_blueprint', __name__)

@vehicle_blueprint.route('/app/insert_vehicle/', methods = ['GET', 'POST'])
@login_required
def insert_vehicle():
    form = VehicleForm()
    if form.validate_on_submit():
        try:
            from utils.database import safe_insert_with_sequence_check
            vehicle = safe_insert_with_sequence_check(
                Vehicle,
                number=form.number.data,
                make=form.make.data,
                model=form.model.data,
                year=form.year.data,
                owner_id=form.owner_id.data
            )
            flash("Vehicle added successfully!", category='success')
        except Exception as e:
            flash(f"Vehicle failed to add: {str(e)}", category='danger')
    else:
        flash("Vehicle failed to add - form validation failed!", category='danger')
    return redirect(url_for('customer_blueprint.customer'))

@vehicle_blueprint.route('/app/update_vehicle/', methods = ['POST'])
@login_required
def update_vehicle():
    form = VehicleForm()
    if form.validate_on_submit():
        vehicle = db.session.get(Vehicle, request.form.get('id'))
        vehicle.number = form.number.data
        vehicle.make = form.make.data
        vehicle.model = form.model.data
        vehicle.year = form.year.data
        vehicle.owner_id = form.owner_id.data
        db.session.commit()
        flash("Vehicle is updated!", category='success')
    else:
        flash("Vehicle failed to add!", category='danger')
    return redirect(url_for('customer_blueprint.customer'))

@vehicle_blueprint.route('/app/delete_vehicle/<int:vehicle_id>', methods = ['GET', 'POST'])
@login_required
def delete_vehicle(vehicle_id):
    vehicle = Vehicle.query.get(vehicle_id)
    db.session.delete(vehicle)
    db.session.commit()
    flash("Vehicle is deleted!", category='success')
    return redirect(url_for('customer_blueprint.customer'))