"""JSON lookups behind the search-as-you-type boxes.

Every result has an id, a label (what goes into the box when it is picked)
and optional sub / meta text shown in the list.
"""

from sqlalchemy import or_
from flask_login import login_required
from flask import Blueprint, request, jsonify

from harithmapos.models import InvoiceHead, Customer, Employee, Vehicle, WashBay, Item, Supplier
from harithmapos.template_helpers import money_filter, quantity_filter
from harithmapos.textutils import format_phone, normalize_phone
from harithmapos.permissions import user_is_owner

search_blueprint = Blueprint('search_blueprint', __name__)

MAX_RESULTS = 20


def _query_text():
    return request.args.get("q", "").strip()


def _name_search(model, query):
    """Rows of a simple named model matching the text (or the id, if a number was typed)."""
    rows = model.query
    if query:
        conditions = [model.name.ilike(f"%{query}%")]
        if query.isdigit():
            conditions.append(model.id == int(query))
        rows = rows.filter(or_(*conditions))
    return rows.order_by(model.name).limit(MAX_RESULTS).all()


@search_blueprint.route("/app/search/vehicles", methods=["GET"])
@login_required
def search_vehicles():
    query = _query_text()
    vehicles = Vehicle.query
    if query:
        pattern = f"%{query}%"
        vehicles = vehicles.join(Customer, Vehicle.owner_id == Customer.id).filter(or_(
            Vehicle.number.ilike(pattern),
            Customer.name.ilike(pattern),
            Customer.contact.ilike(f"%{normalize_phone(query) or query}%"),
        ))
    vehicles = vehicles.order_by(Vehicle.number).limit(MAX_RESULTS).all()
    return jsonify([{
        "id": vehicle.id,
        "number": vehicle.number,
        "label": vehicle.number,
        "sub": " ".join(part for part in [vehicle.owner.name, format_phone(vehicle.owner.contact)] if part),
        "meta": " ".join(part for part in [vehicle.make, vehicle.model] if part),
    } for vehicle in vehicles])


@search_blueprint.route("/app/search/employees", methods=["GET"])
@login_required
def search_employees():
    employees = _name_search(Employee, _query_text())
    return jsonify([{
        "id": employee.id,
        "name": employee.name,
        "label": employee.name,
        "sub": employee.designation or "",
    } for employee in employees])


@search_blueprint.route("/app/search/washbays", methods=["GET"])
@login_required
def search_washbays():
    washbays = _name_search(WashBay, _query_text())
    return jsonify([{
        "id": washbay.id,
        "name": washbay.name,
        "label": washbay.name,
        "sub": washbay.remarks or "",
    } for washbay in washbays])


@search_blueprint.route("/app/search/customers", methods=["GET"])
@login_required
def search_customers():
    query = _query_text()
    customers = Customer.query
    if query:
        conditions = [
            Customer.name.ilike(f"%{query}%"),
            Customer.contact.ilike(f"%{normalize_phone(query) or query}%"),
        ]
        if query.isdigit():
            conditions.append(Customer.id == int(query))
        customers = customers.filter(or_(*conditions))
    customers = customers.order_by(Customer.name).limit(MAX_RESULTS).all()
    return jsonify([{
        "id": customer.id,
        "name": customer.name,
        "label": customer.name,
        "sub": format_phone(customer.contact),
    } for customer in customers])


@search_blueprint.route("/app/search/invoices", methods=["GET"])
@login_required
def search_invoices():
    query = _query_text()
    invoices = (
        InvoiceHead.query
        .join(Customer, InvoiceHead.customer_id == Customer.id)
        .join(Vehicle, InvoiceHead.vehicle_id == Vehicle.id)
    )
    if query:
        pattern = f"%{query}%"
        conditions = [Customer.name.ilike(pattern), Vehicle.number.ilike(pattern)]
        if query.isdigit():
            conditions.append(InvoiceHead.id == int(query))
        invoices = invoices.filter(or_(*conditions))
    invoices = invoices.order_by(InvoiceHead.id.desc()).limit(MAX_RESULTS).all()
    return jsonify([{
        "id": invoice.id,
        "name": f"Invoice #{invoice.id} - {invoice.customer.name} ({invoice.vehicle.number})",
        "label": f"#{invoice.id} {invoice.vehicle.number}",
        "sub": invoice.customer.name,
        "meta": f"Balance {money_filter(invoice.balance)}",
    } for invoice in invoices])


@search_blueprint.route("/app/search/items", methods=["GET"])
@login_required
def search_Items():
    query = _query_text()
    items = Item.query
    if query:
        pattern = f"%{query}%"
        conditions = [Item.name.ilike(pattern), Item.description.ilike(pattern)]
        if query.isdigit():
            conditions.append(Item.id == int(query))
        items = items.filter(or_(*conditions))
    items = items.order_by(Item.name).limit(MAX_RESULTS).all()
    return jsonify([{
        "id": item.id,
        "name": item.name,
        "label": item.name,
        "sub": "Service, no stock" if not item.tracks_stock else f"{quantity_filter(item.quantity)} in stock",
        "meta": money_filter(item.unit_price),
        "price": item.unit_price,
        "cost": item.unit_cost if user_is_owner() else None,
        "discount_pct": item.discount_pct,
        "unit_of_measure": item.unit_of_measure,
        "stock": item.quantity,
        "tracks_stock": item.tracks_stock,
    } for item in items])


@search_blueprint.route("/app/search/suppliers", methods=["GET"])
@login_required
def search_suppliers():
    suppliers = _name_search(Supplier, _query_text())
    return jsonify([{
        "id": supplier.id,
        "name": supplier.name,
        "label": supplier.name,
        "sub": format_phone(supplier.contact),
    } for supplier in suppliers])
