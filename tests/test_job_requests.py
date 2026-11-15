"""What the customer asked for: noted when a job starts, ticked off before it is finished."""
import html as htmllib

import pytest

from harithmapos import config, db
from harithmapos.models import Customer, Employee, InvoiceHead, InvoiceRequest, Item, User, Vehicle, WashBay

ASKED = "Full wash and vacuum\n\n - Check the AC smell\nfull wash and vacuum\n  Engine oil change  \n"


@pytest.fixture
def ids(app):
    with app.app_context():
        cust = Customer.query.first()
        bay, emp = WashBay(name='Bay 1'), Employee(name='Ajith', wage=1, active=True)
        car = Vehicle(number='CAB-1234', owner_id=cust.id)
        db.session.add_all([bay, emp, car])
        db.session.commit()
        return {'car': car.id, 'bay': bay.id, 'emp': emp.id, 'item': Item.query.first().id}


def _requests(app, invoice_id):
    with app.app_context():
        return [(r.description, r.done) for r in
                InvoiceRequest.query.filter_by(invoice_id=invoice_id).order_by(InvoiceRequest.id)]


def _start(client, ids, asked=ASKED):
    client.post('/app/invoice/head/create', data={'vehicle_id': ids['car'], 'employee_id': ids['emp'],
                                                  'washbay_id': ids['bay'], 'requests': asked})
    return InvoiceHead.query.filter_by(vehicle_id=ids['car']).one().id


def test_requests_noted_when_the_job_starts(app, staff, ids):
    with app.app_context():
        inv = _start(staff, ids)
    # One per line; blank lines, bullets and repeats dropped.
    assert _requests(app, inv) == [('Full wash and vacuum', False), ('Check the AC smell', False),
                                   ('Engine oil change', False)]
    page = staff.get(f'/app/invoice/head/{inv}').get_data(as_text=True)
    assert 'Customer asked for' in page and 'Check the AC smell' in page and '0 of 3 done' in page


def test_requests_noted_from_the_floor_board(app, staff, ids):
    staff.post('/app/floor/add', data={'vehicle_id': ids['car'], 'washbay_id': ids['bay'], 'employee_id': ids['emp'],
                                       'start': 'queue', 'requests': 'Underbody wash\nTyre shine'})
    with app.app_context():
        inv = InvoiceHead.query.filter_by(vehicle_id=ids['car']).one().id
    assert _requests(app, inv) == [('Underbody wash', False), ('Tyre shine', False)]
    board = staff.get('/app/floor').get_data(as_text=True)
    assert '0/2' in board and 'Underbody wash' in htmllib.unescape(board)    # count on the card, list for the sheet


def test_no_requests_is_fine(app, staff, ids):
    with app.app_context():
        inv = _start(staff, ids, asked='')
    assert _requests(app, inv) == []
    page = staff.get(f'/app/invoice/head/{inv}').get_data(as_text=True)
    assert 'What did the customer ask for?' in page          # can still be added later
    assert 'not ticked off' not in page


def test_tick_untick_add_and_remove(app, staff, ids):
    with app.app_context():
        inv = _start(staff, ids, asked='Full wash')
        first = InvoiceRequest.query.filter_by(invoice_id=inv).one().id
    staff.post(f'/app/invoice/request/{first}/done', data={'done': '1'})
    with app.app_context():
        r = db.session.get(InvoiceRequest, first)
        assert r.done and r.done_dttm and r.done_by.name == 'Sam Staff'
    assert 'All done' in staff.get(f'/app/invoice/head/{inv}').get_data(as_text=True)

    staff.post(f'/app/invoice/request/{first}/done', data={'done': '0'})
    with app.app_context():
        r = db.session.get(InvoiceRequest, first)
        assert not r.done and r.done_by_id is None

    staff.post(f'/app/invoice/head/{inv}/requests', data={'requests': 'Wax polish'})
    staff.post(f'/app/invoice/head/{inv}/requests', data={'requests': 'wax polish'})     # already there
    assert _requests(app, inv) == [('Full wash', False), ('Wax polish', False)]

    staff.post(f'/app/invoice/request/{first}/delete')
    assert _requests(app, inv) == [('Wax polish', False)]


def test_complete_warns_about_open_requests(app, staff, ids):
    with app.app_context():
        inv = _start(staff, ids, asked='Full wash\nCheck the AC smell')
        first, second = [r.id for r in InvoiceRequest.query.filter_by(invoice_id=inv).order_by(InvoiceRequest.id)]
    page = htmllib.unescape(staff.get(f'/app/invoice/head/{inv}').get_data(as_text=True))
    assert "2 of the customer's requests not ticked off yet" in page and '- Check the AC smell' in page

    staff.post(f'/app/invoice/request/{first}/done', data={'done': '1'})
    staff.post(f'/app/invoice/request/{second}/done', data={'done': '1'})
    page = staff.get(f'/app/invoice/head/{inv}').get_data(as_text=True)
    assert 'not ticked off' not in page and 'All done' in page


def test_floor_sheet_ticks_requests_and_ready_warns(app, staff, ids):
    with app.app_context():
        inv = _start(staff, ids, asked='Full wash\nTyre shine')
        first, second = [r.id for r in InvoiceRequest.query.filter_by(invoice_id=inv).order_by(InvoiceRequest.id)]
        head = db.session.get(InvoiceHead, inv)
        head.service_status = config.SERVICE_STATUS_POLISHING
        db.session.commit()
    board = htmllib.unescape(staff.get('/app/floor').get_data(as_text=True))
    assert "not ticked off yet" in board                      # the Ready to collect button asks first

    # The sheet lists both and sends only the ticked one.
    staff.post(f'/app/floor/{inv}/move', data={'status': config.SERVICE_STATUS_POLISHING,
                                               'request_ids': [first, second], 'request_done': [first]})
    assert _requests(app, inv) == [('Full wash', True), ('Tyre shine', False)]
    assert '1/2' in staff.get('/app/floor').get_data(as_text=True)

    # A move that does not show the list (the quick buttons) leaves the ticks alone.
    staff.post(f'/app/floor/{inv}/move', data={'status': config.SERVICE_STATUS_POLISHING})
    assert _requests(app, inv) == [('Full wash', True), ('Tyre shine', False)]


def test_requests_go_with_a_cancelled_invoice(app, owner, ids):
    with app.app_context():
        inv = _start(owner, ids, asked='Full wash')
    owner.post(f'/app/invoice/head/{inv}', data={'service_status': 0, 'payment_method': 'cash',
                                                 'cancel_invoice': '1'})
    with app.app_context():
        assert db.session.get(InvoiceHead, inv) is None
        assert InvoiceRequest.query.count() == 0


def test_requests_need_sign_in(app, ids):
    client = app.test_client()
    assert client.post('/app/invoice/request/1/done', data={'done': '1'}).status_code == 302
    with app.app_context():
        assert User.query.count() == 2
