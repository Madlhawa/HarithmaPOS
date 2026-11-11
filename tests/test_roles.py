"""Owner vs counter staff permissions. Run with: python -m pytest tests"""
import os

import pytest

os.environ.setdefault('HARITHMA_SECRET_KEY', 'test-secret')

from harithmapos import create_app, db, bcrypt, config  # noqa: E402
from harithmapos.config import Config  # noqa: E402
from harithmapos.models import User, Customer, Item, Payment, Supplier  # noqa: E402

PASSWORD = 'password123'


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        hashed = bcrypt.generate_password_hash(PASSWORD).decode('utf-8')
        db.session.add_all([
            User(name='Olivia Owner', email='owner@example.com', password=hashed, role=config.ROLE_OWNER),
            User(name='Sam Staff', email='staff@example.com', password=hashed, role=config.ROLE_STAFF),
            Customer(name='Kamal Perera', contact='0771234567'),
            Item(name='Engine oil', unit_of_measure='L', quantity=10, unit_cost=1500, unit_price=2000),
            Supplier(name='Oil Depot'),
        ])
        db.session.commit()
    # No app context stays open during the test: each request gets its own,
    # otherwise the signed-in user is cached between the two clients.
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def sign_in(app, email):
    client = app.test_client()
    response = client.post('/app/login', data={'email': email, 'password': PASSWORD})
    assert response.status_code == 302, "sign-in should redirect"
    return client


@pytest.fixture
def owner(app):
    return sign_in(app, 'owner@example.com')


@pytest.fixture
def staff(app):
    return sign_in(app, 'staff@example.com')


def user_id(email):
    return User.query.filter_by(email=email).one().id


# --- new users -------------------------------------------------------------

def test_new_users_default_to_staff(app):
    with app.app_context():
        user = User(name='New', email='new@example.com', password='x')
        db.session.add(user)
        db.session.commit()
        assert user.role == config.ROLE_STAFF
        assert user.active is True
        assert not user.is_owner


# --- pages -----------------------------------------------------------------

@pytest.mark.parametrize('path', [
    '/app/purchase_order/head', '/app/supplier', '/app/employee', '/app/washbay',
    '/app/users', '/app/register',
])
def test_staff_cannot_open_owner_pages(staff, owner, path):
    assert staff.get(path).status_code == 403
    assert owner.get(path).status_code == 200


@pytest.mark.parametrize('path', ['/app/customer/', '/app/item', '/app/payment', '/app/invoice/head'])
def test_staff_can_open_counter_pages(staff, path):
    assert staff.get(path).status_code == 200


def test_staff_menu_hides_owner_pages(staff, owner):
    staff_page = staff.get('/app/customer/').get_data(as_text=True)
    owner_page = owner.get('/app/customer/').get_data(as_text=True)
    for link in ['/app/supplier', '/app/employee', '/app/washbay', '/app/users']:
        assert link not in staff_page
        assert link in owner_page


def test_staff_do_not_see_costs_or_margins(staff, owner):
    staff_page = staff.get('/app/item').get_data(as_text=True)
    owner_page = owner.get('/app/item').get_data(as_text=True)
    assert '1,500.00' not in staff_page and 'Margin' not in staff_page
    assert '1,500.00' in owner_page and 'Margin' in owner_page
    assert staff.get('/app/search/items?q=oil').get_json()[0]['cost'] is None
    assert owner.get('/app/search/items?q=oil').get_json()[0]['cost'] is not None


# --- actions ---------------------------------------------------------------

def test_staff_cannot_delete_customers(app, staff, owner):
    with app.app_context():
        customer_id = Customer.query.filter_by(name='Kamal Perera').one().id
    staff.post(f'/app/delete_customer/{customer_id}')
    with app.app_context():
        assert db.session.get(Customer, customer_id) is not None
    owner.post(f'/app/delete_customer/{customer_id}')
    with app.app_context():
        assert db.session.get(Customer, customer_id) is None


def test_staff_cannot_change_items(app, staff):
    with app.app_context():
        item_id = Item.query.one().id
    staff.post(f'/app/item/{item_id}/update', data={
        'name': 'Cheap oil', 'unit_of_measure': 'L', 'unit_cost': '1', 'unit_price': '1'})
    staff.post(f'/app/item/{item_id}/delete')
    with app.app_context():
        item = db.session.get(Item, item_id)
        assert item is not None and item.name == 'Engine oil'


def payment_form(direction):
    return {'payment_direction': direction, 'payment_amount': '500', 'payment_method': 'cash',
            'payment_type': config.PAYMENT_TYPE_FORM_LIST[0][0], 'remarks': 'test'}


def test_staff_can_take_money_in_but_not_pay_out(app, staff, owner):
    staff.post('/app/payment/create', data=payment_form('in'))
    staff.post('/app/payment/create', data=payment_form('out'))
    with app.app_context():
        assert [p.payment_direction for p in Payment.query.all()] == ['in']
    owner.post('/app/payment/create', data=payment_form('out'))
    with app.app_context():
        assert Payment.query.filter_by(payment_direction='out').count() == 1


def test_staff_payment_list_shows_money_in_only(app, staff):
    with app.app_context():
        db.session.add(Payment(payment_direction='out', payment_amount=777, remarks='owner drawing'))
        db.session.commit()
    page = staff.get('/app/payment?direction=out').get_data(as_text=True)
    assert 'owner drawing' not in page


def test_staff_cannot_edit_or_delete_payments(app, staff):
    with app.app_context():
        payment = Payment(payment_direction='in', payment_amount=500, payment_method='cash', remarks='x')
        db.session.add(payment)
        db.session.commit()
        payment_id = payment.id
    staff.post(f'/app/payment/{payment_id}/delete')
    with app.app_context():
        assert db.session.get(Payment, payment_id) is not None


# --- user management ---------------------------------------------------------

def test_owner_adds_staff_user(app, owner):
    owner.post('/app/register', data={
        'name': 'Nimal', 'email': 'nimal@example.com', 'password': PASSWORD,
        'confirm_password': PASSWORD, 'role': config.ROLE_STAFF})
    with app.app_context():
        assert User.query.filter_by(email='nimal@example.com').one().role == config.ROLE_STAFF


def test_switched_off_user_cannot_sign_in_and_is_signed_out(app, owner, staff):
    with app.app_context():
        staff_id = user_id('staff@example.com')
    owner.post(f'/app/users/{staff_id}', data={
        'name': 'Sam Staff', 'email': 'staff@example.com', 'role': config.ROLE_STAFF})  # active unticked
    # Already signed in: thrown out on the next page.
    assert staff.get('/app/customer/').status_code == 302
    # Signing in again is refused.
    client = app.test_client()
    client.post('/app/login', data={'email': 'staff@example.com', 'password': PASSWORD})
    assert client.get('/app/customer/').status_code == 302


def test_last_owner_cannot_be_demoted_or_switched_off(app, owner):
    with app.app_context():
        owner_id = user_id('owner@example.com')
    owner.post(f'/app/users/{owner_id}', data={
        'name': 'Olivia Owner', 'email': 'owner@example.com', 'role': config.ROLE_STAFF, 'active': 'y'})
    with app.app_context():
        assert db.session.get(User, owner_id).role == config.ROLE_OWNER


def test_owner_can_promote_staff_and_set_password(app, owner):
    with app.app_context():
        staff_id = user_id('staff@example.com')
    owner.post(f'/app/users/{staff_id}', data={
        'name': 'Sam Staff', 'email': 'staff@example.com', 'role': config.ROLE_OWNER, 'active': 'y',
        'password': 'newpassword1', 'confirm_password': 'newpassword1'})
    with app.app_context():
        user = db.session.get(User, staff_id)
        assert user.role == config.ROLE_OWNER
        assert bcrypt.check_password_hash(user.password, 'newpassword1')


@pytest.mark.parametrize('path', ['/app/dashboard', '/app/account', '/app/invoice/head', '/app/item_invoice/head'])
def test_pages_render_for_both_roles(staff, owner, path):
    assert staff.get(path).status_code == 200
    assert owner.get(path).status_code == 200


def test_staff_dashboard_hides_money_out(staff, owner):
    assert 'Paid out today' not in staff.get('/app/dashboard').get_data(as_text=True)
    assert 'Paid out today' in owner.get('/app/dashboard').get_data(as_text=True)


def test_owner_user_pages_render(app, owner):
    with app.app_context():
        staff_id = user_id('staff@example.com')
    assert owner.get('/app/users').status_code == 200
    assert owner.get(f'/app/users/{staff_id}').status_code == 200
