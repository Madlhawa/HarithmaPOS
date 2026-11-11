import logging

from sqlalchemy import func
from flask import Blueprint, flash, abort
from flask_login import login_required

from harithmapos import db
from harithmapos.models import Customer, InvoiceHead, Vehicle
from harithmapos.timeutils import utcnow
from harithmapos.views.vehicle.forms import VehicleForm
from harithmapos.permissions import owner_required

import harithmapos.views.utils as utils
from utils.database import safe_insert_with_sequence_check

logger = logging.getLogger(__name__)

vehicle_blueprint = Blueprint('vehicle_blueprint', __name__)


def _number_taken(number, except_id=None):
    query = Vehicle.query.filter(func.upper(Vehicle.number) == number)
    if except_id is not None:
        query = query.filter(Vehicle.id != except_id)
    return query.first()


@vehicle_blueprint.route('/app/insert_vehicle/', methods=['POST'])
@login_required
def insert_vehicle():
    form = VehicleForm()
    if form.validate_on_submit():
        owner = db.session.get(Customer, form.owner_id.data)
        duplicate = _number_taken(form.number.data)
        if owner is None:
            flash("Choose the owner from the list.", category='danger')
        elif duplicate:
            flash(f"{duplicate.number} is already registered to {duplicate.owner.name}.", category='warning')
        else:
            try:
                safe_insert_with_sequence_check(
                    Vehicle,
                    number=form.number.data,
                    make=form.make.data,
                    model=form.model.data,
                    year=str(form.year.data) if form.year.data else None,
                    owner_id=owner.id
                )
                flash(f"{form.number.data} added for {owner.name}.", category='success')
            except Exception:
                logger.exception("Could not add vehicle")
                flash("The vehicle could not be added. Please try again.", category='danger')
    else:
        utils.flash_form_errors(form)
    return utils.redirect_back('customer_blueprint.customer')


@vehicle_blueprint.route('/app/vehicle/<int:vehicle_id>/update', methods=['POST'])
@login_required
def update_vehicle(vehicle_id):
    vehicle = db.session.get(Vehicle, vehicle_id) or abort(404)
    form = VehicleForm()
    if form.validate_on_submit():
        owner = db.session.get(Customer, form.owner_id.data)
        duplicate = _number_taken(form.number.data, except_id=vehicle.id)
        if owner is None:
            flash("Choose the owner from the list.", category='danger')
        elif duplicate:
            flash(f"{duplicate.number} is already registered to {duplicate.owner.name}.", category='warning')
        else:
            try:
                vehicle.number = form.number.data
                vehicle.make = form.make.data
                vehicle.model = form.model.data
                vehicle.year = str(form.year.data) if form.year.data else None
                vehicle.owner_id = owner.id
                vehicle.update_dttm = utcnow()
                db.session.commit()
                flash(f"{vehicle.number} saved.", category='success')
            except Exception:
                db.session.rollback()
                logger.exception("Could not update vehicle %s", vehicle_id)
                flash("The vehicle could not be saved. Please try again.", category='danger')
    else:
        utils.flash_form_errors(form)
    return utils.redirect_back('customer_blueprint.customer')


@vehicle_blueprint.route('/app/delete_vehicle/<int:vehicle_id>', methods=['POST'])
@owner_required
def delete_vehicle(vehicle_id):
    vehicle = db.session.get(Vehicle, vehicle_id) or abort(404)
    utils.delete_record(vehicle, vehicle.number, blockers=[
        (InvoiceHead.query.filter(InvoiceHead.vehicle_id == vehicle.id).count(), 'service invoices'),
    ])
    return utils.redirect_back('customer_blueprint.customer')
