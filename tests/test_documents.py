"""Invoices, item sales and purchase orders: draft -> completed, or -> void. Completed bills are fixed."""
from decimal import Decimal

import pytest

from harithmapos import config, db
from harithmapos.models import (
    AuditLog, Customer, Employee, InvoiceDetail, InvoiceHead, Item, ItemInvoiceHead, PurchaseOrderHead, Supplier,
    Vehicle, WashBay,
)


@pytest.fixture
def ids(app):
    with app.app_context():
        cust = Customer.query.first()
        bay, emp = WashBay(name='Bay 1'), Employee(name='Ajith', wage=1, active=True)
        car = Vehicle(number='WPX-555', owner_id=cust.id)
        db.session.add_all([bay, emp, car])
        db.session.flush()
        inv = InvoiceHead(customer_id=cust.id, vehicle_id=car.id, washbay_id=bay.id, employee_id=emp.id,
                          service_status=config.SERVICE_STATUS_WASHING, total_cost=0, gross_price=0)
        sale = ItemInvoiceHead(customer_id=cust.id)
        po = PurchaseOrderHead(supplier_id=Supplier.query.first().id)
        db.session.add_all([inv, sale, po])
        db.session.commit()
        return {'inv': inv.id, 'sale': sale.id, 'po': po.id, 'item': Item.query.first().id, 'bay': bay.id,
                'emp': emp.id, 'cust': cust.id}


def _stock(app, ids):
    with app.app_context():
        return db.session.get(Item, ids['item']).quantity


def _job(ids, **extra):
    data = {'service_status': config.SERVICE_STATUS_WASHING, 'employee_id': ids['emp'], 'washbay_id': ids['bay'],
            'payment_method': 'cash'}
    data.update(extra)
    return data


def _add(client, ids, qty='2'):
    client.post(f"/app/invoice/detail/add/{ids['inv']}", data={'item_id': ids['item'], 'quantity': qty})


def _complete(client, ids, received=''):
    return client.post(f"/app/invoice/head/{ids['inv']}", data=_job(ids, received_amount=received, complete_invoice='1'),
                       follow_redirects=True)


def _inv(app, ids):
    with app.app_context():
        inv = db.session.get(InvoiceHead, ids['inv'])
        db.session.expunge(inv)
        return inv


# --- Completing ---------------------------------------------------------------

def test_completing_needs_a_line_and_stamps_who_and_when(app, staff, ids):
    page = _complete(staff, ids).get_data(as_text=True)
    assert 'Add at least one item' in page and _inv(app, ids).is_draft
    _add(staff, ids)
    _complete(staff, ids)
    with app.app_context():
        inv = db.session.get(InvoiceHead, ids['inv'])
        assert inv.is_completed and inv.completed_dttm and inv.completed_by.name == 'Sam Staff'
        assert inv.service_status == config.SERVICE_STATUS_DONE        # the job is finished with the bill
    assert 'is completed' in _complete(staff, ids).get_data(as_text=True)


def test_a_completed_bill_is_fixed(app, staff, ids):
    _add(staff, ids)
    _complete(staff, ids, '1000')
    stock = _stock(app, ids)
    _add(staff, ids, '1')
    with app.app_context():
        line = InvoiceDetail.query.one()
        line_id = line.id
    staff.post(f"/app/invoice/detail/quantity/add/{line_id}")
    staff.post(f"/app/invoice/detail/quantity/remove/{line_id}")
    staff.post(f"/app/invoice/detail/delete/{line_id}")
    staff.post(f"/app/invoice/head/{ids['inv']}", data=_job(ids, discount_amount='500', current_milage='52000',
                                                            update_invoice='1'))
    with app.app_context():
        inv = db.session.get(InvoiceHead, ids['inv'])
        assert InvoiceDetail.query.count() == 1 and InvoiceDetail.query.one().quantity == 2
        assert inv.gross_price == Decimal('4000') and not inv.discount_amount     # no later discount
        assert inv.current_milage == 52000                                        # job details can be corrected
        assert inv.service_status == config.SERVICE_STATUS_DONE
    assert _stock(app, ids) == stock
    html = staff.get(f"/app/invoice/head/{ids['inv']}").get_data(as_text=True)
    assert 'data-entry' not in html and 'Complete and print receipt' not in html
    assert 'name="discount_amount"' not in html and 'Completed' in html
    staff.post(f"/app/invoice/head/{ids['inv']}/status", data={'status': 0})
    assert _inv(app, ids).service_status == config.SERVICE_STATUS_DONE


def test_completed_item_sale_and_order_are_fixed(app, owner, ids):
    owner.post(f"/app/item_invoice/detail/add/{ids['sale']}", data={'item_id': ids['item'], 'quantity': '1'})
    owner.post(f"/app/item_invoice/head/{ids['sale']}", data={'payment_method': 'cash', 'complete_item_invoice': '1'})
    owner.post(f"/app/item_invoice/head/{ids['sale']}", data={'discount_amount': '100', 'update_item_invoice': '1'})
    owner.post(f"/app/item_invoice/detail/add/{ids['sale']}", data={'item_id': ids['item'], 'quantity': '1'})
    with app.app_context():
        sale = db.session.get(ItemInvoiceHead, ids['sale'])
        assert sale.is_completed and sale.gross_price == Decimal('2000') and len(sale.invoice_details) == 1

    owner.post(f"/app/purchase_order/detail/add/{ids['po']}", data={'item_id': ids['item'], 'quantity': '5', 'unit_cost': '1500'})
    owner.post(f"/app/purchase_order/head/{ids['po']}", data={'payment_method': 'bt', 'complete_purchase_order': '1'})
    owner.post(f"/app/purchase_order/head/{ids['po']}", data={'discount_pct': '10', 'supplier_invoice_id': 'INV-77',
                                                             'update_purchase_order': '1'})
    with app.app_context():
        po = db.session.get(PurchaseOrderHead, ids['po'])
        assert po.is_completed and po.gross_price == Decimal('7500') and not po.discount_pct
        assert po.supplier_invoice_id == 'INV-77'                                  # a reference: still editable


# --- Voiding -------------------------------------------------------------------

def test_voiding_a_draft_puts_stock_back_and_takes_it_off_the_boards(app, owner, staff, ids):
    before = _stock(app, ids)
    _add(owner, ids)
    assert _stock(app, ids) == before - 2
    staff.post(f"/app/invoice/head/{ids['inv']}/void", data={'reason': 'Customer left'})
    owner.post(f"/app/invoice/head/{ids['inv']}/void", data={'reason': ''})
    assert _inv(app, ids).is_draft                                    # staff refused, reason required
    owner.post(f"/app/invoice/head/{ids['inv']}/void", data={'reason': 'Customer left'})
    with app.app_context():
        inv = db.session.get(InvoiceHead, ids['inv'])
        assert inv.is_void and inv.void_reason == 'Customer left' and inv.voided_by.name == 'Olivia Owner'
        assert InvoiceDetail.query.count() == 1                       # kept for the record
    assert _stock(app, ids) == before
    assert 'WPX-555' not in owner.get('/app/floor').get_data(as_text=True)
    assert 'WPX-555' not in owner.get('/app/dashboard').get_data(as_text=True)
    html = owner.get(f"/app/invoice/head/{ids['inv']}").get_data(as_text=True)
    assert 'This invoice is void' in html and 'Customer left' in html and 'name="update_invoice"' not in html
    owner.post(f"/app/invoice/head/{ids['inv']}/void", data={'reason': 'again'})
    assert _stock(app, ids) == before                                 # not put back twice
    _add(owner, ids)
    assert _stock(app, ids) == before
    # The car can come in again on a new invoice.
    owner.post('/app/floor/add', data={'vehicle_id': _inv(app, ids).vehicle_id, 'washbay_id': ids['bay'],
                                       'employee_id': ids['emp'], 'start': 'queue'})
    with app.app_context():
        assert InvoiceHead.query.count() == 2


def test_a_paid_bill_is_refunded_before_it_is_voided(app, owner, ids):
    _add(owner, ids)
    _complete(owner, ids, '4000')
    page = owner.post(f"/app/invoice/head/{ids['inv']}/void", data={'reason': 'Wrong car'},
                      follow_redirects=True).get_data(as_text=True)
    assert 'Refund or reverse those payments first' in page and _inv(app, ids).is_completed
    owner.post(f"/app/invoice/head/{ids['inv']}/refund", data={'payment_amount': '4000', 'payment_method': 'cash'})
    owner.post(f"/app/invoice/head/{ids['inv']}/void", data={'reason': 'Wrong car'})
    inv = _inv(app, ids)
    assert inv.is_void
    owner.post(f"/app/invoice/head/{ids['inv']}/pay", data={'payment_amount': '10', 'payment_method': 'cash'})
    with app.app_context():
        assert len(db.session.get(InvoiceHead, ids['inv']).payments) == 2      # payment and refund only


def test_voiding_an_order_takes_its_stock_back_off(app, owner, ids):
    before = _stock(app, ids)
    owner.post(f"/app/purchase_order/detail/add/{ids['po']}", data={'item_id': ids['item'], 'quantity': '5', 'unit_cost': '1500'})
    assert _stock(app, ids) == before + 5
    owner.post(f"/app/purchase_order/head/{ids['po']}/void", data={'reason': 'Delivery returned'})
    assert _stock(app, ids) == before
    with app.app_context():
        assert db.session.get(PurchaseOrderHead, ids['po']).is_void


def test_no_deleting_documents(owner, ids):
    for url in (f"/app/invoice/head/{ids['inv']}/delete", f"/app/item_invoice/head/{ids['sale']}/delete",
                f"/app/purchase_order/head/{ids['po']}/delete"):
        assert owner.post(url).status_code in (404, 405)


# --- Lists, reports, audit --------------------------------------------------------

def test_lists_filter_by_bill_state(app, owner, ids):
    _add(owner, ids)
    owner.post(f"/app/invoice/head/{ids['inv']}/status", data={'status': config.SERVICE_STATUS_DONE})
    assert 'WPX-555' in owner.get('/app/invoice/head?status=tobill').get_data(as_text=True)
    assert 'WPX-555' not in owner.get('/app/invoice/head?status=done').get_data(as_text=True)
    assert 'to bill' in owner.get('/app/dashboard').get_data(as_text=True)
    _complete(owner, ids)
    assert 'WPX-555' in owner.get('/app/invoice/head?status=unpaid').get_data(as_text=True)
    owner.post(f"/app/invoice/head/{ids['inv']}/void", data={'reason': 'test'})   # nothing paid, so it can be voided
    assert 'WPX-555' in owner.get('/app/invoice/head?status=void').get_data(as_text=True)
    assert 'WPX-555' not in owner.get('/app/invoice/head?status=unpaid').get_data(as_text=True)


def test_completing_and_voiding_are_in_the_audit_log(app, owner, ids):
    _add(owner, ids)
    _complete(owner, ids)
    owner.post(f"/app/invoice/head/{ids['inv']}/void", data={'reason': 'Billed the wrong car'})
    with app.app_context():
        rows = [(r.category, r.field, r.old_value, r.new_value) for r in
                AuditLog.query.filter_by(entity='invoice', field='Status').order_by(AuditLog.id)]
    assert rows == [('discounts', 'Status', 'Draft', 'Completed'),
                    ('deletions', 'Status', 'Completed', 'Void: Billed the wrong car')]


def test_customer_link_to_a_voided_visit(app, owner, ids):
    owner.post(f"/app/invoice/head/{ids['inv']}/void", data={'reason': 'Customer left'})
    with app.app_context():
        token = db.session.get(InvoiceHead, ids['inv']).get_customer_view_token()
    response = owner.get(f'/invoice/{token}')
    assert response.status_code == 404 and 'cancelled' in response.get_data(as_text=True)


def _ancestors_classes(html, element_id):
    """Classes of every element enclosing the one with this id (a tiny parser; no extra packages)."""
    from html.parser import HTMLParser
    void = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}

    class Finder(HTMLParser):
        def __init__(self):
            super().__init__()
            self.stack, self.found = [], None

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if attrs.get('id') == element_id and self.found is None:
                self.found = [c for _, c in self.stack]
            if tag not in void:
                self.stack.append((tag, attrs.get('class') or ''))

        def handle_endtag(self, tag):
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    del self.stack[i:]
                    break

    finder = Finder()
    finder.feed(html)
    return finder.found


def test_void_popup_is_not_inside_the_sticky_side_column(app, owner, ids):
    """A pop-up inside .job-side sits under Bootstrap's backdrop and can't be clicked."""
    _add(owner, ids)
    owner.post(f"/app/item_invoice/detail/add/{ids['sale']}", data={'item_id': ids['item'], 'quantity': '1'})
    for url in (f"/app/invoice/head/{ids['inv']}", f"/app/item_invoice/head/{ids['sale']}",
                f"/app/purchase_order/head/{ids['po']}"):
        html = owner.get(url).get_data(as_text=True)
        classes = _ancestors_classes(html, 'voidModal')
        assert classes is not None, url
        assert not any('job-side' in c or 'job' in c.split() for c in classes), (url, classes)
