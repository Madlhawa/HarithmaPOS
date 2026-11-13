"""The floor board on the supervisor's phone."""
import pytest

from harithmapos import config, db
from harithmapos.models import Customer, Employee, InvoiceHead, InvoiceStatusLog, Vehicle, WashBay


@pytest.fixture
def floor(app):
    with app.app_context():
        cust = Customer.query.first()
        bay1, bay2 = WashBay(name='Bay 1'), WashBay(name='Bay 2')
        emp = Employee(name='Ajith', wage=1, active=True)
        gone = Employee(name='Left Us', wage=1, active=False)
        v1, v2 = Vehicle(number='CAB-1111', owner_id=cust.id), Vehicle(number='CAB-2222', owner_id=cust.id)
        db.session.add_all([bay1, bay2, emp, gone, v1, v2])
        db.session.flush()
        inv = InvoiceHead(customer_id=cust.id, vehicle_id=v1.id, washbay_id=bay1.id, employee_id=emp.id,
                          service_status=config.SERVICE_STATUS_WASHING, total_cost=0, gross_price=0)
        db.session.add(inv)
        db.session.commit()
        return {'bay1': bay1.id, 'bay2': bay2.id, 'emp': emp.id, 'inv': inv.id, 'v2': v2.id}


def _get(app, invoice_id):
    with app.app_context():
        return db.session.get(InvoiceHead, invoice_id)


def test_board_renders_for_staff(staff, floor):
    html = staff.get('/app/floor').get_data(as_text=True)
    assert 'CAB-1111' in html and 'Start polishing' in html and 'Add vehicle' in html
    assert 'Left Us' not in html                       # people who left are not offered
    assert '1 of 2 bays free' in html


def test_menu_links_to_board(staff):
    assert '/app/floor' in staff.get('/app/dashboard').get_data(as_text=True)


def test_move_to_next_stage_logs_it(app, staff, floor):
    r = staff.post(f"/app/floor/{floor['inv']}/move", data={'status': 3})
    assert r.status_code == 302 and r.headers['Location'].endswith('/app/floor')
    assert _get(app, floor['inv']).service_status == 3
    with app.app_context():
        assert InvoiceStatusLog.query.filter_by(invoice_id=floor['inv'], service_status=3).count() == 1


def test_mark_ready(app, staff, floor):
    staff.post(f"/app/floor/{floor['inv']}/move", data={'status': 4})
    assert _get(app, floor['inv']).service_status == config.SERVICE_STATUS_DONE


def test_change_bay_and_employee(app, staff, floor):
    with app.app_context():
        e2 = Employee(name='Bandula', wage=1, active=True)
        db.session.add(e2)
        db.session.commit()
        e2 = e2.id
    staff.post(f"/app/floor/{floor['inv']}/move", data={'status': 2, 'washbay_id': floor['bay2'], 'employee_id': e2})
    inv = _get(app, floor['inv'])
    assert (inv.washbay_id, inv.employee_id, inv.service_status) == (floor['bay2'], e2, 2)


def test_add_known_vehicle_to_queue(app, staff, floor):
    staff.post('/app/floor/add', data={'vehicle_id': floor['v2'], 'washbay_id': floor['bay2'],
                                        'employee_id': floor['emp'], 'start': 'queue', 'current_milage': '45,000'})
    with app.app_context():
        inv = InvoiceHead.query.filter_by(vehicle_id=floor['v2']).one()
        assert inv.service_status == 0 and inv.current_milage == 45000
        assert InvoiceStatusLog.query.filter_by(invoice_id=inv.id).count() == 1


def test_add_by_typed_number_finds_existing(app, staff, floor):
    staff.post('/app/floor/add', data={'number': ' cab-2222 ', 'washbay_id': floor['bay2'],
                                        'employee_id': floor['emp'], 'start': 'now'})
    with app.app_context():
        inv = InvoiceHead.query.filter_by(vehicle_id=floor['v2']).one()
        assert inv.service_status == 1 and inv.washbay_id == floor['bay2']


def test_add_new_vehicle_registers_owner(app, staff, floor):
    staff.post('/app/floor/add', data={'number': 'wp kx-9', 'name': 'Nimal Silva', 'contact': '077 555 1234',
                                        'washbay_id': floor['bay2'], 'employee_id': floor['emp'], 'start': 'queue'})
    with app.app_context():
        v = Vehicle.query.filter_by(number='WP KX-9').one()
        assert v.owner.name == 'Nimal Silva' and v.owner.contact == '775551234'
        assert InvoiceHead.query.filter_by(vehicle_id=v.id).count() == 1


def test_new_vehicle_needs_owner_name(app, staff, floor):
    r = staff.post('/app/floor/add', data={'number': 'NEW-1234', 'washbay_id': floor['bay2'],
                                            'employee_id': floor['emp']}, follow_redirects=True)
    assert "Enter the owner" in r.get_data(as_text=True)
    with app.app_context():
        assert Vehicle.query.filter_by(number='NEW-1234').count() == 0


def test_no_second_open_invoice(app, staff, floor):
    with app.app_context():
        v1 = db.session.get(InvoiceHead, floor['inv']).vehicle_id
    r = staff.post('/app/floor/add', data={'vehicle_id': v1, 'washbay_id': floor['bay2'], 'employee_id': floor['emp']},
                   follow_redirects=True)
    assert 'already on the floor' in r.get_data(as_text=True)
    with app.app_context():
        assert InvoiceHead.query.filter_by(vehicle_id=v1).count() == 1


def test_busy_bay_is_refused(app, staff, floor):
    r = staff.post('/app/floor/add', data={'vehicle_id': floor['v2'], 'washbay_id': floor['bay1'],
                                            'employee_id': floor['emp'], 'start': 'now'}, follow_redirects=True)
    assert 'already has CAB-1111' in r.get_data(as_text=True)
    with app.app_context():
        assert InvoiceHead.query.filter_by(vehicle_id=floor['v2']).count() == 0
        cust = Customer.query.first()
        q = InvoiceHead(customer_id=cust.id, vehicle_id=floor['v2'], washbay_id=floor['bay1'],
                        employee_id=floor['emp'], service_status=0, total_cost=0, gross_price=0)
        db.session.add(q)
        db.session.commit()
        q = q.id
    staff.post(f"/app/floor/{q}/move", data={'status': 1})
    assert _get(app, q).service_status == 0
    staff.post(f"/app/floor/{q}/move", data={'status': 1, 'washbay_id': floor['bay2']})
    inv = _get(app, q)
    assert (inv.service_status, inv.washbay_id) == (1, floor['bay2'])


def test_needs_sign_in(app):
    assert app.test_client().get('/app/floor').status_code == 302
