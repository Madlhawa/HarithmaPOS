"""The public status page a customer opens from the SMS link."""
from decimal import Decimal

from harithmapos import db
from harithmapos.models import Customer, Employee, InvoiceDetail, InvoiceHead, Item, Vehicle, WashBay


def _invoice(app, item_discount=0, bill_discount=0):
    with app.app_context():
        cust = Customer.query.first()
        veh = Vehicle(number='CAB-1', owner_id=cust.id)
        emp, bay = Employee(name='Ajith', wage=1), WashBay(name='Bay 1')
        db.session.add_all([veh, emp, bay])
        db.session.flush()
        item = Item.query.first()
        price = Decimal('2000')
        head = InvoiceHead(customer_id=cust.id, vehicle_id=veh.id, washbay_id=bay.id, employee_id=emp.id,
                           service_status=1, discount_amount=bill_discount,
                           total_price=price, total_discount=item_discount + bill_discount,
                           gross_price=price - item_discount - bill_discount, total_cost=0)
        db.session.add(head)
        db.session.flush()
        db.session.add(InvoiceDetail(invoice_head_id=head.id, item_id=item.id, quantity=1, total_cost=0,
                                     total_price=price, discount_amount=item_discount,
                                     gross_price=price - item_discount))
        db.session.commit()
        with app.test_request_context():
            return '/invoice/' + head.get_customer_view_token()


def test_page_shows_discount(app):
    html = app.test_client().get(_invoice(app, item_discount=150, bill_discount=50)).get_data(as_text=True)
    assert 'Subtotal' in html and '2,000.00' in html
    assert 'Item discounts' in html and '-150.00' in html and 'Bill discount' in html and '-50.00' in html
    assert '1,800.00' in html


def test_single_discount_line(app):
    html = app.test_client().get(_invoice(app, item_discount=200)).get_data(as_text=True)
    assert '<dt>Discount</dt>' in html and 'Bill discount' not in html


def test_no_discount_no_subtotal(app):
    html = app.test_client().get(_invoice(app)).get_data(as_text=True)
    assert 'Subtotal' not in html and 'Discount' not in html and '2,000.00' in html


def test_heat_classes_do_not_clash_with_bootstrap_headings(app):
    css = open(app.static_folder + '/css/app.css').read()
    for n in range(7):
        assert f'\n.h{n} ' not in css
