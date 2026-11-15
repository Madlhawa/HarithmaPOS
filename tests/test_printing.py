"""Receipts are printed from the browser: item sales on the 80 mm printer, service invoices on the LQ-350."""
import pytest

from harithmapos import config, db, settings as app_settings
from harithmapos.models import Customer, Employee, InvoiceHead, ItemInvoiceHead, Item, Vehicle, WashBay


@pytest.fixture
def ids(app):
    with app.app_context():
        cust = Customer.query.first()
        bay, emp = WashBay(name='Bay 1'), Employee(name='Ajith', wage=1, active=True)
        car = Vehicle(number='CAB-1234', owner_id=cust.id)
        db.session.add_all([bay, emp, car])
        db.session.flush()
        inv = InvoiceHead(customer_id=cust.id, vehicle_id=car.id, washbay_id=bay.id, employee_id=emp.id,
                          service_status=config.SERVICE_STATUS_WASHING, total_cost=0, gross_price=0)
        sale = ItemInvoiceHead(customer_id=cust.id)
        db.session.add_all([inv, sale])
        db.session.commit()
        return {'inv': inv.id, 'sale': sale.id, 'item': Item.query.first().id, 'bay': bay.id, 'emp': emp.id}


def _complete_service(client, ids):
    client.post(f"/app/invoice/detail/add/{ids['inv']}", data={'item_id': ids['item'], 'quantity': '2'})
    return client.post(f"/app/invoice/head/{ids['inv']}", data={
        'service_status': config.SERVICE_STATUS_WASHING, 'employee_id': ids['emp'], 'washbay_id': ids['bay'],
        'payment_method': 'cash', 'paid_amount': '1000', 'complete_invoice': '1'}, follow_redirects=True)


def _complete_sale(client, ids):
    client.post(f"/app/item_invoice/detail/add/{ids['sale']}", data={'item_id': ids['item'], 'quantity': '1'})
    return client.post(f"/app/item_invoice/head/{ids['sale']}", data={
        'payment_method': 'cash', 'paid_amount': '0', 'complete_item_invoice': '1'}, follow_redirects=True)


def test_service_invoice_prints_on_the_dot_matrix_layout(staff, ids):
    _complete_service(staff, ids)
    html = staff.get(f"/app/invoice/head/{ids['inv']}/print").get_data(as_text=True)
    assert 'LQ-350' in html and 'INVOICE' in html
    assert 'CAB-1234' in html and 'Current mileage' in html and 'Next service at' in html
    assert 'Ajith' not in html and 'Bay 1' not in html and 'Checked by' not in html
    assert 'Balance due' in html and '3,000.00' in html


def test_next_service_mileage_on_the_invoice(app, staff, ids):
    """Without a service interval the next mileage equals the current one: show a dash, not that number."""
    _complete_service(staff, ids)
    with app.app_context():
        inv = db.session.get(InvoiceHead, ids['inv'])
        inv.current_milage, inv.next_milage_in, inv.next_milage = 50000, None, 50000
        db.session.commit()
    html = staff.get(f"/app/invoice/head/{ids['inv']}/print").get_data(as_text=True)
    assert html.count('50,000 km') == 1
    with app.app_context():
        inv = db.session.get(InvoiceHead, ids['inv'])
        inv.next_milage_in, inv.next_milage = 5000, 55000
        db.session.commit()
    html = staff.get(f"/app/invoice/head/{ids['inv']}/print").get_data(as_text=True)
    assert '50,000 km' in html and '55,000 km' in html


def test_item_sale_prints_on_the_80mm_layout(staff, ids):
    _complete_sale(staff, ids)
    html = staff.get(f"/app/item_invoice/head/{ids['sale']}/print").get_data(as_text=True)
    assert '80 mm' in html and f"Sale #{ids['sale']}" in html
    assert 'LQ-350' not in html


def test_complete_opens_the_print_window_once(staff, ids):
    html = _complete_service(staff, ids).get_data(as_text=True)
    assert f'data-print-now="/app/invoice/head/{ids["inv"]}/print"' in html
    assert 'data-print-now' not in staff.get('/app/dashboard').get_data(as_text=True)

    html = _complete_sale(staff, ids).get_data(as_text=True)
    assert f'data-print-now="/app/item_invoice/head/{ids["sale"]}/print"' in html


def test_saving_without_completing_does_not_print(staff, ids):
    staff.post(f"/app/invoice/detail/add/{ids['inv']}", data={'item_id': ids['item'], 'quantity': '1'})
    html = staff.post(f"/app/invoice/head/{ids['inv']}", data={
        'service_status': config.SERVICE_STATUS_WASHING, 'employee_id': ids['emp'], 'washbay_id': ids['bay'],
        'payment_method': 'cash', 'paid_amount': '0', 'update_invoice': '1'}, follow_redirects=True).get_data(as_text=True)
    assert 'data-print-now' not in html


def test_print_on_complete_can_be_switched_off(app, owner, staff, ids):
    owner.post('/app/settings/printing', data={})            # switch left off
    with app.test_request_context():
        assert app_settings.get('print_on_complete') is False
    html = _complete_service(staff, ids).get_data(as_text=True)
    assert 'completed' in html and 'data-print-now' not in html


def test_print_buttons_print_in_place(staff, ids):
    assert 'data-print>' in staff.get(f"/app/invoice/head/{ids['inv']}").get_data(as_text=True)
    assert 'data-print>' in staff.get(f"/app/item_invoice/head/{ids['sale']}").get_data(as_text=True)


def test_rabbitmq_is_gone(owner):
    html = owner.get('/app/settings').get_data(as_text=True)
    assert 'RabbitMQ' not in html and 'Receipt printing' in html
    assert owner.post('/app/settings/test/printer').status_code == 404
