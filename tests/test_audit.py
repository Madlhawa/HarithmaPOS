"""The audit log: who changed a price, discount, payment, pay rate, role or setting, and from what."""
from decimal import Decimal

import pytest

from harithmapos import config, db
from harithmapos.models import (
    AuditLog, Customer, Employee, InvoiceHead, Item, Payment, User, Vehicle, WashBay,
)


@pytest.fixture(autouse=True)
def fresh_log(app):
    """Forget the rows written while the test data (users, an item) was set up."""
    with app.app_context():
        AuditLog.query.delete()
        db.session.commit()


def _log(app, **filters):
    with app.app_context():
        q = AuditLog.query.filter_by(**filters).order_by(AuditLog.id)
        return [(r.action, r.label, r.field, r.old_value, r.new_value, r.user.name if r.user else None) for r in q]


@pytest.fixture
def item_id(app):
    with app.app_context():
        return Item.query.filter_by(name='Engine oil').one().id


def test_price_change_is_recorded_with_who_and_from_what(app, owner, item_id):
    owner.post(f'/app/item/{item_id}/update', data={
        'name': 'Engine oil', 'unit_of_measure': 'L', 'quantity': '10', 'unit_cost': '1,500.00',
        'unit_price': '2,250', 'discount_pct': ''})
    rows = _log(app, category='prices')
    assert rows == [('changed', 'Item: Engine oil', 'Price', '2,000.00', '2,250.00', 'Olivia Owner')]
    with app.app_context():
        assert AuditLog.query.one().path == f'POST /app/item/{item_id}/update'


def test_saving_without_changes_records_nothing(app, owner, item_id):
    owner.post(f'/app/item/{item_id}/update', data={
        'name': 'Engine oil', 'unit_of_measure': 'L', 'quantity': '10', 'unit_cost': '1500',
        'unit_price': '2000', 'discount_pct': ''})
    assert _log(app) == []


def test_payments_and_their_reversals_are_recorded(app, owner):
    owner.post('/app/payment/create', data={'payment_type': 'expense', 'payment_amount': '5000',
                                            'payment_method': 'cash', 'remarks': 'Electricity'})
    with app.app_context():
        pid = Payment.query.one().id
    owner.post(f'/app/payment/{pid}/reverse', data={'reason': 'Entered twice'})
    rows = _log(app, entity='payment')
    assert [r[0] for r in rows] == ['created', 'created']
    assert rows[0][4] == 'Rs. 5,000.00 out, Cash, Expense' and rows[0][5] == 'Olivia Owner'
    assert rows[1][4] == f'Rs. 5,000.00 in, Cash, Expense, reverses #{pid}'


def test_bill_and_line_discounts_and_deleted_lines(app, staff, item_id):
    with app.app_context():
        cust = Customer.query.first()
        bay, emp = WashBay(name='Bay 1'), Employee(name='Ajith', wage=1, active=True)
        car = Vehicle(number='CAB-1234', owner_id=cust.id)
        db.session.add_all([bay, emp, car]); db.session.flush()
        inv = InvoiceHead(customer_id=cust.id, vehicle_id=car.id, washbay_id=bay.id, employee_id=emp.id,
                          service_status=0, total_cost=0, gross_price=0)
        db.session.add(inv); db.session.commit()
        inv_id, bay_id, emp_id = inv.id, bay.id, emp.id
    staff.post(f'/app/invoice/detail/add/{inv_id}', data={'item_id': item_id, 'quantity': '2', 'discount_amount': '100'})
    staff.post(f'/app/invoice/head/{inv_id}', data={'service_status': 0, 'employee_id': emp_id, 'washbay_id': bay_id,
                                                   'payment_method': 'cash', 'paid_amount': '0', 'discount_amount': '250',
                                                   'update_invoice': '1'})
    with app.app_context():
        line_id = db.session.get(InvoiceHead, inv_id).invoice_details[0].id
    staff.post(f'/app/invoice/detail/delete/{line_id}')
    rows = _log(app)
    assert ('changed', f'Service invoice #{inv_id} (CAB-1234)', 'Bill discount', '0.00', '250.00', 'Sam Staff') in rows
    added = [r for r in rows if r[0] == 'created' and r[1].endswith('Engine oil')]
    assert added and added[0][4].endswith('discount 100.00')                 # a discount given when the line was added
    deleted = [r for r in rows if r[0] == 'deleted']
    assert deleted and deleted[0][1] == f'Service invoice #{inv_id}: Engine oil' and deleted[0][3].startswith('2 × Engine oil')


def test_roles_pay_and_secrets(app, owner):
    with app.app_context():
        staff_id = User.query.filter_by(email='staff@example.com').one().id
        emp = Employee(name='Nimal', wage=60000, active=True); db.session.add(emp); db.session.commit()
        emp.wage = Decimal('65000'); db.session.commit()
        user = db.session.get(User, staff_id); user.role = config.ROLE_OWNER; db.session.commit()
    owner.post('/app/settings/sms', data={'sms_enabled': 'on', 'notifylk_user_id': 'u1', 'notifylk_api_key': 'very-secret',
                                          'sms_sender_id': 'Harithma', 'sms_start_message': 'Hi {customer}',
                                          'sms_done_message': 'Done {customer}'})
    rows = _log(app)
    assert ('changed', 'Employee: Nimal', 'Pay rate', '60,000.00', '65,000.00', None) in rows       # no signed-in user: "System"
    assert ('changed', 'User: Sam Staff', 'Role', config.ROLE_STAFF, config.ROLE_OWNER, None) in rows
    secret = [r for r in rows if 'API key' in r[1]]
    assert secret and secret[0][4] == '(hidden)'
    assert not any('very-secret' in (r[3] or '') + (r[4] or '') for r in rows)


def test_audit_page_is_for_owners(app, owner, staff, item_id):
    owner.post(f'/app/item/{item_id}/update', data={
        'name': 'Engine oil', 'unit_of_measure': 'L', 'quantity': '10', 'unit_cost': '1500',
        'unit_price': '2100', 'discount_pct': ''})
    assert staff.get('/app/audit').status_code == 403
    html = owner.get('/app/audit').get_data(as_text=True)
    assert 'Item: Engine oil' in html and '2,100.00' in html and 'Olivia Owner' in html
    assert 'Item: Engine oil' in owner.get('/app/audit?category=prices').get_data(as_text=True)
    assert 'Item: Engine oil' not in owner.get('/app/audit?category=payments').get_data(as_text=True)
    assert 'Item: Engine oil' in owner.get('/app/audit?query=engine').get_data(as_text=True)


def test_a_rolled_back_change_leaves_no_record(app, item_id):
    with app.app_context():
        item = db.session.get(Item, item_id)
        item.unit_price = 9999
        db.session.flush()
        db.session.rollback()
        assert AuditLog.query.count() == 0
