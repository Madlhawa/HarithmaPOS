"""Payments taken on a completed invoice, item sale or purchase order's own page."""
from decimal import Decimal

import pytest

from harithmapos import config, db
from harithmapos.models import (
    Customer, Employee, InvoiceHead, ItemInvoiceHead, Item, Payment, PurchaseOrderHead, Supplier, Vehicle, WashBay,
)


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
        po = PurchaseOrderHead(supplier_id=Supplier.query.first().id)
        db.session.add_all([inv, sale, po])
        db.session.commit()
        return {'inv': inv.id, 'sale': sale.id, 'po': po.id, 'item': Item.query.first().id,
                'bay': bay.id, 'emp': emp.id}


def _get(app, model, doc_id):
    with app.app_context():
        doc = db.session.get(model, doc_id)
        payments = sorted((p.payment_direction, p.payment_amount) for p in doc.payments)
        return doc, payments


def _service_invoice(client, ids, paid, complete=True):
    """Two litres of engine oil (Rs. 4,000), with `paid` handed over."""
    client.post(f"/app/invoice/detail/add/{ids['inv']}", data={'item_id': ids['item'], 'quantity': '2'})
    data = {'service_status': config.SERVICE_STATUS_WASHING, 'employee_id': ids['emp'], 'washbay_id': ids['bay'],
            'payment_method': 'cash', 'paid_amount': paid}
    data['complete_invoice' if complete else 'update_invoice'] = '1'
    return client.post(f"/app/invoice/head/{ids['inv']}", data=data)


def _item_sale(client, ids, paid, complete=True):
    client.post(f"/app/item_invoice/detail/add/{ids['sale']}", data={'item_id': ids['item'], 'quantity': '2'})
    data = {'payment_method': 'cash', 'paid_amount': paid}
    data['complete_item_invoice' if complete else 'update_item_invoice'] = '1'
    return client.post(f"/app/item_invoice/head/{ids['sale']}", data=data)


def _purchase_order(client, ids, paid, complete=True):
    """Ten litres at Rs. 1,500: Rs. 15,000 to the supplier."""
    client.post(f"/app/purchase_order/detail/add/{ids['po']}",
                data={'item_id': ids['item'], 'quantity': '10', 'unit_cost': '1500'})
    data = {'payment_method': 'bt', 'paid_amount': paid}
    data['complete_purchase_order' if complete else 'update_purchase_order'] = '1'
    return client.post(f"/app/purchase_order/head/{ids['po']}", data=data)


# --- Service invoices -------------------------------------------------------

def test_open_invoice_has_paid_box_and_no_payment_button(staff, ids):
    _service_invoice(staff, ids, '0', complete=False)
    html = staff.get(f"/app/invoice/head/{ids['inv']}").get_data(as_text=True)
    assert 'name="paid_amount"' in html
    assert 'Complete and print receipt' in html
    assert 'Record payment' not in html


def test_payment_refused_before_completion(app, staff, ids):
    _service_invoice(staff, ids, '0', complete=False)
    response = staff.post(f"/app/invoice/head/{ids['inv']}/pay",
                          data={'payment_amount': '1000', 'payment_method': 'cash'}, follow_redirects=True)
    assert 'Complete invoice #' in response.get_data(as_text=True)
    doc, payments = _get(app, InvoiceHead, ids['inv'])
    assert payments == [] and not doc.paid_amount


def test_completed_invoice_with_balance_shows_payment_button(staff, ids):
    _service_invoice(staff, ids, '1000')
    html = staff.get(f"/app/invoice/head/{ids['inv']}").get_data(as_text=True)
    assert 'Record payment' in html and 'Balance to collect' in html
    assert 'name="paid_amount"' not in html                    # the paid box is replaced by the payment list
    assert 'Complete and print receipt' not in html
    assert '3,000.00' in html                                  # prefilled with the balance


def test_staff_pays_off_an_invoice_in_two_parts(app, staff, ids):
    _service_invoice(staff, ids, '1000')
    staff.post(f"/app/invoice/head/{ids['inv']}/pay", data={'payment_amount': '1,000', 'payment_method': 'card'})
    doc, payments = _get(app, InvoiceHead, ids['inv'])
    assert doc.paid_amount == Decimal('2000') and doc.balance == Decimal('2000')
    assert payments == [('in', Decimal('1000.00')), ('in', Decimal('1000.00'))]

    response = staff.post(f"/app/invoice/head/{ids['inv']}/pay",
                          data={'payment_amount': '2000', 'payment_method': 'cash', 'remarks': 'Final'},
                          follow_redirects=True)
    assert 'now settled' in response.get_data(as_text=True)
    doc, payments = _get(app, InvoiceHead, ids['inv'])
    assert doc.balance == 0 and len(payments) == 3
    with app.app_context():
        last = Payment.query.order_by(Payment.id.desc()).first()
        assert (last.customer_id, last.payment_method, last.remarks) == (doc.customer_id, 'cash', 'Final')
    html = staff.get(f"/app/invoice/head/{ids['inv']}").get_data(as_text=True)
    assert 'Record payment' not in html and 'Settled' in html


def test_cannot_pay_more_than_the_balance(app, staff, ids):
    _service_invoice(staff, ids, '1000')
    response = staff.post(f"/app/invoice/head/{ids['inv']}/pay",
                          data={'payment_amount': '3000.01', 'payment_method': 'cash'}, follow_redirects=True)
    assert 'more than the balance' in response.get_data(as_text=True)
    doc, payments = _get(app, InvoiceHead, ids['inv'])
    assert doc.paid_amount == Decimal('1000') and len(payments) == 1


def test_bad_amounts_are_refused(app, staff, ids):
    _service_invoice(staff, ids, '1000')
    for amount in ('0', '-5', 'abc', ''):
        staff.post(f"/app/invoice/head/{ids['inv']}/pay", data={'payment_amount': amount, 'payment_method': 'cash'})
    _, payments = _get(app, InvoiceHead, ids['inv'])
    assert len(payments) == 1


def test_saving_a_completed_invoice_keeps_what_was_paid(app, staff, ids):
    _service_invoice(staff, ids, '1000')
    staff.post(f"/app/invoice/head/{ids['inv']}/pay", data={'payment_amount': '500', 'payment_method': 'qr'})
    # The page now sends only the hidden payment method and no paid box.
    staff.post(f"/app/invoice/head/{ids['inv']}", data={
        'service_status': config.SERVICE_STATUS_DONE, 'payment_method': 'qr', 'discount_amount': '100',
        'update_invoice': '1'})
    doc, payments = _get(app, InvoiceHead, ids['inv'])
    assert doc.paid_amount == Decimal('1500') and doc.balance == Decimal('2400')
    assert len(payments) == 2


def test_done_on_the_floor_board_without_complete(app, staff, ids):
    """Set to Done without pressing Complete: what was typed in the paid box reaches the ledger first."""
    _service_invoice(staff, ids, '1000', complete=False)
    staff.post(f"/app/invoice/head/{ids['inv']}/status", data={'status': config.SERVICE_STATUS_DONE})
    assert 'Record payment' in staff.get(f"/app/invoice/head/{ids['inv']}").get_data(as_text=True)
    staff.post(f"/app/invoice/head/{ids['inv']}/pay", data={'payment_amount': '3000', 'payment_method': 'cash'})
    doc, payments = _get(app, InvoiceHead, ids['inv'])
    assert doc.balance == 0
    assert payments == [('in', Decimal('1000.00')), ('in', Decimal('3000.00'))]


# --- Item sales -------------------------------------------------------------

def test_item_sale_payment_only_after_complete(app, staff, ids):
    _item_sale(staff, ids, '0', complete=False)
    assert 'Record payment' not in staff.get(f"/app/item_invoice/head/{ids['sale']}").get_data(as_text=True)
    staff.post(f"/app/item_invoice/head/{ids['sale']}/pay", data={'payment_amount': '100', 'payment_method': 'cash'})
    doc, payments = _get(app, ItemInvoiceHead, ids['sale'])
    assert not doc.is_completed and payments == []

    staff.post(f"/app/item_invoice/head/{ids['sale']}", data={'payment_method': 'cash', 'paid_amount': '0',
                                                             'complete_item_invoice': '1'})
    doc, _ = _get(app, ItemInvoiceHead, ids['sale'])
    assert doc.is_completed and doc.balance == Decimal('4000')
    assert 'Record payment' in staff.get(f"/app/item_invoice/head/{ids['sale']}").get_data(as_text=True)

    staff.post(f"/app/item_invoice/head/{ids['sale']}/pay", data={'payment_amount': '4000', 'payment_method': 'cash'})
    doc, payments = _get(app, ItemInvoiceHead, ids['sale'])
    assert doc.balance == 0 and payments == [('in', Decimal('4000.00'))]


# --- Purchase orders --------------------------------------------------------

def test_owner_pays_supplier_on_completed_order(app, owner, ids):
    _purchase_order(owner, ids, '5000')
    doc, _ = _get(app, PurchaseOrderHead, ids['po'])
    assert doc.is_completed and doc.balance == Decimal('10000')
    html = owner.get(f"/app/purchase_order/head/{ids['po']}").get_data(as_text=True)
    assert 'Pay supplier' in html and 'name="paid_amount"' not in html

    owner.post(f"/app/purchase_order/head/{ids['po']}/pay", data={'payment_amount': '10000', 'payment_method': 'bt'})
    doc, payments = _get(app, PurchaseOrderHead, ids['po'])
    assert doc.balance == 0
    assert payments == [('out', Decimal('5000.00')), ('out', Decimal('10000.00'))]


def test_open_order_has_no_payment_button(owner, ids):
    _purchase_order(owner, ids, '0', complete=False)
    html = owner.get(f"/app/purchase_order/head/{ids['po']}").get_data(as_text=True)
    assert 'Pay supplier' not in html and 'name="paid_amount"' in html


def test_staff_cannot_pay_suppliers(app, owner, staff, ids):
    _purchase_order(owner, ids, '0')
    response = staff.post(f"/app/purchase_order/head/{ids['po']}/pay",
                          data={'payment_amount': '100', 'payment_method': 'cash'})
    assert response.status_code in (302, 403)
    _, payments = _get(app, PurchaseOrderHead, ids['po'])
    assert payments == []
