from flask_login import login_required
from flask import Blueprint, request, jsonify

from harithmapos.models import Payment, InvoiceHead, ItemInvoiceHead, PurchaseOrderHead,Customer, Employee, Vehicle, WashBay, Item

search_blueprint = Blueprint('search_blueprint', __name__)

@search_blueprint.route("/app/search/vehicles", methods=["GET"])
@login_required
def search_vehicles():
    query = request.args.get("q", "").strip().lower()
    if query.isdigit():
        vehicles = Vehicle.query.filter((Vehicle.id == int(query)) | (Vehicle.number.ilike(f"%{query}%"))).all()
    else:
        vehicles = Vehicle.query.filter(Vehicle.number.ilike(f"%{query}%")).all()
    return jsonify([{"id": vehicle.id, "number": vehicle.number} for vehicle in vehicles])


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

@search_blueprint.route("/app/search/customers", methods=["GET"])
@login_required
def search_customers():
    query = request.args.get("q", "").strip().lower()
    if query.isdigit():
        customers = Customer.query.filter((Customer.id == int(query)) | (Customer.name.ilike(f"%{query}%"))).all()
    else:
        customers = Customer.query.filter(Customer.name.ilike(f"%{query}%")).all()
    return jsonify([{"id": customer.id, "name": customer.name} for customer in customers])

@search_blueprint.route("/app/search/invoices", methods=["GET"])
@login_required
def search_invoices():
    query = request.args.get("q", "").strip().lower()
    if query.isdigit():
        invoices = InvoiceHead.query.filter((InvoiceHead.id == int(query)) | (InvoiceHead.customer.has(Customer.name.ilike(f"%{query}%")))).all()
    else:
        invoices = InvoiceHead.query.filter(InvoiceHead.customer.has(Customer.name.ilike(f"%{query}%"))).all()
    return jsonify([{"id": invoice.id, "name": f"Invoice #{invoice.id} - {invoice.customer.name} ({invoice.vehicle.number})"} for invoice in invoices])

@search_blueprint.route("/app/search/items", methods=["GET"])
@login_required
def search_Items():
    query = request.args.get("q", "").strip().lower()
    if query.isdigit():
        Items = Item.query.filter((Item.id == int(query)) | (Item.name.ilike(f"%{query}%"))).all()
    else:
        Items = Item.query.filter(Item.name.ilike(f"%{query}%")).all()
    return jsonify([{"id": item.id, "name": item.name, "price":item.unit_price, "discount_pct":item.discount_pct, "unit_of_measure":item.unit_of_measure} for item in Items])