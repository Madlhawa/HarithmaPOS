"""A vehicle can wait in the queue with no bay and nobody assigned; work needs them (job_status.py)."""
import pytest

from harithmapos import config, db
from harithmapos.models import Customer, Employee, InvoiceHead, Vehicle, WashBay

WAITING, VACUUMING, POLISHING, DONE = (config.SERVICE_STATUS_WAITING, config.SERVICE_STATUS_VACUUMING,
                                       config.SERVICE_STATUS_POLISHING, config.SERVICE_STATUS_DONE)


@pytest.fixture
def shop(app):
    with app.app_context():
        cust = Customer.query.first()
        bay, emp = WashBay(name='Bay 1'), Employee(name='Ajith', wage=1, active=True)
        car = Vehicle(number='CAB-3333', owner_id=cust.id)
        db.session.add_all([bay, emp, car])
        db.session.commit()
        return {'bay': bay.id, 'emp': emp.id, 'car': car.id, 'cust': cust.id}


def _queued(app, shop):
    with app.app_context():
        inv = InvoiceHead(customer_id=shop['cust'], vehicle_id=shop['car'], service_status=WAITING,
                          total_cost=0, gross_price=0)
        db.session.add(inv)
        db.session.commit()
        return inv.id


def _inv(app, invoice_id):
    with app.app_context():
        return db.session.get(InvoiceHead, invoice_id)


def test_the_floor_board_queues_a_vehicle_without_bay_or_employee(app, staff, shop):
    staff.post('/app/floor/add', data={'vehicle_id': shop['car'], 'start': 'queue'})
    with app.app_context():
        inv = InvoiceHead.query.one()
        assert (inv.washbay_id, inv.employee_id, inv.service_status) == (None, None, WAITING)


def test_start_now_still_needs_both(app, staff, shop):
    page = staff.post('/app/floor/add', data={'vehicle_id': shop['car'], 'washbay_id': shop['bay'], 'start': 'now'},
                      follow_redirects=True).get_data(as_text=True)
    assert 'To start now, choose the bay and who will work on it' in page
    with app.app_context():
        assert InvoiceHead.query.count() == 0


def test_work_needs_a_bay_and_someone(app, staff, shop):
    inv_id = _queued(app, shop)
    page = staff.post(f'/app/floor/{inv_id}/move', data={'status': VACUUMING},
                      follow_redirects=True).get_data(as_text=True)
    assert 'Choose a wash bay and who will work on it before moving CAB-3333 to vacuuming' in page
    assert _inv(app, inv_id).service_status == WAITING
    staff.post(f'/app/floor/{inv_id}/move', data={'status': VACUUMING, 'washbay_id': shop['bay'], 'employee_id': shop['emp']})
    inv = _inv(app, inv_id)
    assert (inv.service_status, inv.washbay_id, inv.employee_id) == (VACUUMING, shop['bay'], shop['emp'])


def test_polishing_needs_someone_but_no_bay(app, staff, shop):
    inv_id = _queued(app, shop)
    staff.post(f'/app/floor/{inv_id}/move', data={'status': POLISHING})
    assert _inv(app, inv_id).service_status == WAITING
    staff.post(f'/app/floor/{inv_id}/move', data={'status': POLISHING, 'employee_id': shop['emp']})
    inv = _inv(app, inv_id)
    assert inv.service_status == POLISHING and inv.washbay_id is None


def test_ready_needs_neither(app, staff, shop):
    inv_id = _queued(app, shop)
    staff.post(f'/app/floor/{inv_id}/move', data={'status': DONE})
    assert _inv(app, inv_id).service_status == DONE


def test_the_dashboard_button_explains_what_is_missing(app, staff, shop):
    inv_id = _queued(app, shop)
    page = staff.post(f'/app/invoice/head/{inv_id}/status', data={'status': VACUUMING},
                      follow_redirects=True).get_data(as_text=True)
    assert 'Choose a wash bay' in page and _inv(app, inv_id).service_status == WAITING


def test_a_new_invoice_needs_only_the_vehicle(app, staff, shop):
    staff.post('/app/invoice/head/create', data={'vehicle_id': shop['car']})
    with app.app_context():
        inv = InvoiceHead.query.one()
        assert inv.vehicle_id == shop['car'] and inv.employee_id is None and inv.washbay_id is None


def test_pages_show_unassigned_jobs(app, staff, owner, shop):
    inv_id = _queued(app, shop)
    board = staff.get('/app/floor').get_data(as_text=True)
    assert 'Choose bay and bring in' in board and 'No bay yet' in board and 'Nobody yet' in board
    for url in ('/app/dashboard', f'/app/invoice/head/{inv_id}', '/app/invoice/head'):
        response = staff.get(url)
        assert response.status_code == 200, url
    with app.app_context():
        inv = db.session.get(InvoiceHead, inv_id)
        inv.service_status, inv.doc_status = DONE, 'completed'
        db.session.commit()
    report = owner.get('/app/reports/sales')
    assert report.status_code == 200 and 'Not assigned' in report.get_data(as_text=True)
