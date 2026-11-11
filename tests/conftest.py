"""Shared test setup: an app on an in-memory database with one owner and one staff user."""
import os
import sys

# Make "import harithmapos" work when running pytest from the repository root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Also make "from conftest import ..." work in the test files.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


import pytest

os.environ.setdefault('HARITHMA_SECRET_KEY', 'test-secret')

from harithmapos import create_app, db, bcrypt, config  # noqa: E402
from harithmapos.config import Config  # noqa: E402
from harithmapos.models import User, Customer, Item, Supplier  # noqa: E402

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


