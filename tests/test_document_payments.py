"""Money taken on a service invoice, item sale or purchase order: recorded in the ledger, never typed onto the bill."""
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
        payments = [(p.payment_type, p.payment_direction, p.payment_amount, p.tendered_amount) for p in doc.payments]
        return doc, payments


def _service_invoice(client, ids, received, complete=True, method='cash'):
    """Two litres of engine oil (Rs. 4,000), with `received` handed over."""
    client.post(f"/app/invoice/detail/add/{ids['inv']}", data={'item_id': ids['item'], 'quantity': '2'})
    data = {'service_status': config.SERVICE_STATUS_WASHING, 'employee_id': ids['emp'], 'washbay_id': ids['bay'],
            'payment_method': method, 'received_amount': received}
    data['complete_invoice' if complete else 'update_invoice'] = '1'
    return client.post(f"/app/invoice/head/{ids['inv']}", data=data, follow_redirects=True)


def _item_sale(client, ids, received, complete=True):
    client.post(f"/app/item_invoice/detail/add/{ids['sale']}", data={'item_id': ids['item'], 'quantity': '2'})
    data = {'payment_method': 'cash', 'received_amount': received}
    data['complete_item_invoice' if complete else 'update_item_invoice'] = '1'
    return client.post(f"/app/item_invoice/head/{ids['sale']}", data=data, follow_redirects=True)


def _purchase_order(client, ids, paid_now, complete=True):
    """Ten litres at Rs. 1,500: Rs. 15,000 to the supplier."""
    client.post(f"/app/purchase_order/detail/add/{ids['po']}",
                data={'item_id': ids['item'], 'quantity': '10', 'unit_cost': '1500'})
    data = {'payment_method': 'bt', 'paid_now': paid_now}
    data['complete_purchase_order' if complete else 'update_purchase_order'] = '1'
    return client.post(f"/app/purchase_order/head/{ids['po']}", data=data, follow_redirects=True)


# --- Completing a service invoice --------------------------------------------

def test_cash_with_change_records_only_the_bill(app, staff, ids):
    page = _service_invoice(staff, ids, '5,000').get_data(as_text=True)
    assert 'Give back Rs. 1,000.00 change.' in page
    doc, payments = _get(app, InvoiceHead, ids['inv'])
    assert payments == [('sale', 'in', Decimal('4000.00'), Decimal('5000.00'))]
    assert doc.paid_amount == Decimal('4000') and doc.balance == 0
    with app.app_context():
        entry = Payment.query.one()
        assert entry.created_by.name == 'Sam Staff' and entry.customer_id == doc.customer_id
    receipt = staff.get(f"/app/invoice/head/{ids['inv']}/print").get_data(as_text=True)
    assert 'Handed over' in receipt and '5,000.00' in receipt and '1,000.00' in receipt


def test_part_payment_leaves_a_balance(app, staff, ids):
    page = _service_invoice(staff, ids, '1000', method='card').get_data(as_text=True)
    assert 'Still to pay: Rs. 3,000.00.' in page
    doc, payments = _get(app, InvoiceHead, ids['inv'])
    assert payments == [('sale', 'in', Decimal('1000.00'), None)] and doc.balance == Decimal('3000')
    html = staff.get(f"/app/invoice/head/{ids['inv']}").get_data(as_text=True)
    assert 'Record payment' in html and '3,000.00' in html
    assert 'name="received_amount"' not in html                # completed: money is taken with Record payment


def test_completing_unpaid_records_nothing(app, staff, ids):
    _service_invoice(staff, ids, '')
    doc, payments = _get(app, InvoiceHead, ids['inv'])
    assert payments == [] and doc.balance == Decimal('4000')


def test_save_does_not_take_money(app, staff, ids):
    page = _service_invoice(staff, ids, '2000', complete=False).get_data(as_text=True)
    assert 'recorded only when you press Complete' in page
    doc, payments = _get(app, InvoiceHead, ids['inv'])
    assert payments == [] and doc.paid_amount == 0
    html = staff.get(f"/app/invoice/head/{ids['inv']}").get_data(as_text=True)
    assert 'name="received_amount"' in html and 'Record payment' not in html
    assert 'value="credit"' not in html                        # credit is not a way to pay


# --- Paying later --------------------------------------------------------------

def test_payment_refused_before_completion(app, staff, ids):
    _service_invoice(staff, ids, '', complete=False)
    response = staff.post(f"/app/invoice/head/{ids['inv']}/pay",
                          data={'payment_amount': '1000', 'payment_method': 'cash'}, follow_redirects=True)
    assert 'Complete invoice #' in response.get_data(as_text=True)
    assert _get(app, InvoiceHead, ids['inv'])[1] == []


def test_pay_off_in_two_parts(app, staff, ids):
    _service_invoice(staff, ids, '1000')
    staff.post(f"/app/invoice/head/{ids['inv']}/pay", data={'payment_amount': '1,000', 'payment_method': 'card'})
    response = staff.post(f"/app/invoice/head/{ids['inv']}/pay",
                          data={'payment_amount': '2000', 'payment_method': 'qr', 'remarks': 'Final'},
                          follow_redirects=True)
    assert 'now settled' in response.get_data(as_text=True)
    doc, payments = _get(app, InvoiceHead, ids['inv'])
    assert doc.balance == 0 and [p[2] for p in payments] == [Decimal('1000.00')] * 2 + [Decimal('2000.00')]
    html = staff.get(f"/app/invoice/head/{ids['inv']}").get_data(as_text=True)
    assert 'Record payment' not in html and 'Settled' in html


def test_cannot_pay_more_than_the_balance(app, staff, ids):
    _service_invoice(staff, ids, '1000')
    response = staff.post(f"/app/invoice/head/{ids['inv']}/pay",
                          data={'payment_amount': '3000.01', 'payment_method': 'cash'}, follow_redirects=True)
    assert 'more than the balance' in response.get_data(as_text=True)
    assert len(_get(app, InvoiceHead, ids['inv'])[1]) == 1


def test_bad_amounts_and_methods_are_refused(app, staff, ids):
    _service_invoice(staff, ids, '1000')
    for amount, method in (('0', 'cash'), ('-5', 'cash'), ('abc', 'cash'), ('', 'cash'), ('100', 'credit')):
        staff.post(f"/app/invoice/head/{ids['inv']}/pay", data={'payment_amount': amount, 'payment_method': method})
    assert len(_get(app, InvoiceHead, ids['inv'])[1]) == 1


def test_done_on_the_floor_board_without_complete(app, staff, ids):
    _service_invoice(staff, ids, '', complete=False)
    staff.post(f"/app/invoice/head/{ids['inv']}/status", data={'status': config.SERVICE_STATUS_DONE})
    assert 'Record payment' in staff.get(f"/app/invoice/head/{ids['inv']}").get_data(as_text=True)
    staff.post(f"/app/invoice/head/{ids['inv']}/pay", data={'payment_amount': '4000', 'payment_method': 'cash'})
    doc, payments = _get(app, InvoiceHead, ids['inv'])
    assert doc.balance == 0 and len(payments) == 1


# --- Overpaid: refunds (owners) ------------------------------------------------

def test_discount_after_payment_is_refunded_by_an_owner(app, staff, owner, ids):
    _service_invoice(staff, ids, '4000')
    staff.post(f"/app/invoice/head/{ids['inv']}", data={
        'service_status': config.SERVICE_STATUS_DONE, 'discount_amount': '500', 'update_invoice': '1'})
    doc, payments = _get(app, InvoiceHead, ids['inv'])
    assert doc.balance == Decimal('-500') and len(payments) == 1      # Save never touches what was paid
    assert 'Overpaid' in owner.get(f"/app/invoice/head/{ids['inv']}").get_data(as_text=True)

    staff.post(f"/app/invoice/head/{ids['inv']}/refund", data={'payment_amount': '500', 'payment_method': 'cash'})
    owner.post(f"/app/invoice/head/{ids['inv']}/refund", data={'payment_amount': '600', 'payment_method': 'cash'})
    assert len(_get(app, InvoiceHead, ids['inv'])[1]) == 1            # staff refused, too much refused
    owner.post(f"/app/invoice/head/{ids['inv']}/refund", data={'payment_amount': '500', 'payment_method': 'cash'})
    doc, payments = _get(app, InvoiceHead, ids['inv'])
    assert payments[-1][:3] == ('sale_refund', 'out', Decimal('500.00')) and doc.balance == 0


# --- Item sales ----------------------------------------------------------------

def test_item_sale(app, staff, ids):
    _item_sale(staff, ids, '', complete=False)
    staff.post(f"/app/item_invoice/head/{ids['sale']}/pay", data={'payment_amount': '100', 'payment_method': 'cash'})
    doc, payments = _get(app, ItemInvoiceHead, ids['sale'])
    assert not doc.is_completed and payments == []

    page = _item_sale(staff, ids, '10000').get_data(as_text=True)     # second line added, so Rs. 8,000
    assert 'Give back Rs. 2,000.00 change.' in page
    doc, payments = _get(app, ItemInvoiceHead, ids['sale'])
    assert doc.is_completed and doc.balance == 0
    assert payments == [('sale', 'in', Decimal('8000.00'), Decimal('10000.00'))]


# --- Purchase orders -----------------------------------------------------------

def test_owner_pays_supplier(app, owner, ids):
    _purchase_order(owner, ids, '5000')
    doc, payments = _get(app, PurchaseOrderHead, ids['po'])
    assert doc.is_completed and doc.balance == Decimal('10000')
    assert payments == [('supplier', 'out', Decimal('5000.00'), None)]
    html = owner.get(f"/app/purchase_order/head/{ids['po']}").get_data(as_text=True)
    assert 'Pay supplier' in html and 'name="paid_now"' not in html
    owner.post(f"/app/purchase_order/head/{ids['po']}/pay", data={'payment_amount': '10000', 'payment_method': 'bt'})
    assert _get(app, PurchaseOrderHead, ids['po'])[0].balance == 0


def test_paying_a_supplier_more_than_the_order_is_refused(app, owner, ids):
    page = _purchase_order(owner, ids, '20000').get_data(as_text=True)
    assert 'The payment was not recorded' in page
    doc, payments = _get(app, PurchaseOrderHead, ids['po'])
    assert doc.is_completed and payments == []


def test_open_order_has_no_payment_button(owner, ids):
    _purchase_order(owner, ids, '0', complete=False)
    html = owner.get(f"/app/purchase_order/head/{ids['po']}").get_data(as_text=True)
    assert 'Pay supplier' not in html and 'name="paid_now"' in html


def test_staff_cannot_pay_suppliers(app, owner, staff, ids):
    _purchase_order(owner, ids, '0')
    response = staff.post(f"/app/purchase_order/head/{ids['po']}/pay",
                          data={'payment_amount': '100', 'payment_method': 'cash'})
    assert response.status_code in (302, 403)
    assert _get(app, PurchaseOrderHead, ids['po'])[1] == []
