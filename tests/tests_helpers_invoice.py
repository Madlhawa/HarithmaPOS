"""Small helpers shared by tests."""
from harithmapos import config, db
from harithmapos.models import Customer, Employee, InvoiceHead, Vehicle, WashBay


def make_completed_invoice(app, gross=4000, number='CAB-9999'):
    with app.app_context():
        cust = Customer.query.first()
        bay, emp = WashBay(name='Bay X'), Employee(name='Helper', wage=1, active=True)
        car = Vehicle(number=number, owner_id=cust.id)
        db.session.add_all([bay, emp, car])
        db.session.flush()
        inv = InvoiceHead(customer_id=cust.id, vehicle_id=car.id, washbay_id=bay.id, employee_id=emp.id,
                          service_status=config.SERVICE_STATUS_DONE, total_cost=0, total_price=gross,
                          gross_price=gross)
        db.session.add(inv)
        db.session.commit()
        return inv.id
