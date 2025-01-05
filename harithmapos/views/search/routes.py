from flask_login import login_required
from flask import Blueprint, request, jsonify

from harithmapos.models import Payment, InvoiceHead, ItemInvoiceHead, PurchaseOrderHead,Customer, Employee, Vehical, WashBay, Item

search_blueprint = Blueprint('search_blueprint', __name__)

@search_blueprint.route("/app/search/vehicals", methods=["GET"])
@login_required
def search_vehicals():
    query = request.args.get("q", "").strip().lower()
    if query.isdigit():
        vehicals = Vehical.query.filter((Vehical.id == int(query)) | (Vehical.number.ilike(f"%{query}%"))).all()
    else:
        vehicals = Vehical.query.filter(Vehical.number.ilike(f"%{query}%")).all()
    return jsonify([{"id": vehical.id, "number": vehical.number} for vehical in vehicals])


@search_blueprint.route("/app/search/employees", methods=["GET"])
@login_required
def search_employees():
    query = request.args.get("q", "").strip().lower()
    if query.isdigit():
        employees = Employee.query.filter((Employee.id == int(query)) | (Employee.name.ilike(f"%{query}%"))).all()
    else:
        employees = Employee.query.filter(Employee.name.ilike(f"%{query}%")).all()
    return jsonify([{"id": employee.id, "name": employee.name} for employee in employees])


@search_blueprint.route("/app/search/washbays", methods=["GET"])
@login_required
def search_washbays():
    query = request.args.get("q", "").strip().lower()
    if query.isdigit():
        washbays = WashBay.query.filter((WashBay.id == int(query)) | (WashBay.name.ilike(f"%{query}%"))).all()
    else:
        washbays = WashBay.query.filter(WashBay.name.ilike(f"%{query}%")).all()
    return jsonify([{"id": washbay.id, "name": washbay.name} for washbay in washbays])

@search_blueprint.route("/app/search/items", methods=["GET"])
@login_required
def search_Items():
    query = request.args.get("q", "").strip().lower()
    if query.isdigit():
        Items = Item.query.filter((Item.id == int(query)) | (Item.name.ilike(f"%{query}%"))).all()
    else:
        Items = Item.query.filter(Item.name.ilike(f"%{query}%")).all()
    return jsonify([{"id": item.id, "name": item.name, "price":item.unit_price, "discount_pct":item.discount_pct} for item in Items])