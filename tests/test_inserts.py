"""New records are saved with plain inserts, and multi-record saves are all or nothing."""
import pathlib

from harithmapos import config, db
from harithmapos.models import Customer, Employee, ItemInvoiceHead, User, Vehicle, WashBay

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_old_sequence_repair_helper_is_gone():
    assert not (ROOT / 'utils').exists()
    for path in list((ROOT / 'harithmapos').rglob('*.py')) + [ROOT / 'app.py']:
        assert 'safe_insert_with_sequence_check' not in path.read_text(), path


def test_quick_register_saves_customer_and_vehicle(app, staff):
    r = staff.post('/app/customer/quick', data={'name': 'Ruwan Jayasinghe', 'contact': '0712223344', 'number': 'CAR-5151'})
    assert r.status_code == 302
    with app.app_context():
        vehicle = Vehicle.query.filter_by(number='CAR-5151').one()
        assert vehicle.owner.name == 'Ruwan Jayasinghe'


def test_quick_item_invoice_creates_the_walk_in_customer_once(app, staff):
    staff.post('/app/item_invoice/head/create/quick')
    staff.post('/app/item_invoice/head/create/quick')
    with app.app_context():
        assert Customer.query.filter_by(id=-1).count() == 1
        assert ItemInvoiceHead.query.filter_by(customer_id=-1).count() == 2


def test_floor_add_saves_nothing_when_the_invoice_fails(app, staff, monkeypatch):
    with app.app_context():
        bay, emp = WashBay(name='Bay 9'), Employee(name='Ajith', wage=1, active=True)
        db.session.add_all([bay, emp])
        db.session.commit()
        bay_id, emp_id = bay.id, emp.id
        customers_before = Customer.query.count()

    def broken_invoice(**kwargs):
        raise RuntimeError('database went away')
    monkeypatch.setattr('harithmapos.views.floor.routes.InvoiceHead', broken_invoice)

    staff.post('/app/floor/add', data={'number': 'NEW-7777', 'name': 'Nimal Silva', 'contact': '0775551234',
                                       'washbay_id': bay_id, 'employee_id': emp_id})
    with app.app_context():
        assert Vehicle.query.filter_by(number='NEW-7777').count() == 0
        assert Customer.query.count() == customers_before


def test_create_user_command(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=['create-user', '--name', 'New Owner', '--email', 'new@example.com',
                                 '--password', 'password123'])
    assert result.exit_code == 0, result.output
    with app.app_context():
        assert User.query.filter_by(email='new@example.com').one().role == config.ROLE_OWNER

    again = runner.invoke(args=['create-user', '--name', 'X', '--email', 'new@example.com', '--password', 'password123'])
    assert again.exit_code != 0 and 'already exists' in again.output
