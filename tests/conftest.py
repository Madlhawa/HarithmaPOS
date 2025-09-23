"""
Test configuration and fixtures for Harithma POS
"""

import pytest
import os
import tempfile
from harithmapos import create_app, db
from harithmapos.models import User, Customer, Vehicle, Supplier, Employee, Item, WashBay, Payment, InvoiceHead, InvoiceDetail
# Simple test configuration
class TestConfig:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Create test configuration
    test_config = TestConfig()
    
    # Create app with test configuration
    app = create_app(test_config)
    
    # Force SQLite for testing by overriding the database URI
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': test_config.SQLALCHEMY_DATABASE_URI,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_ECHO': False
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def auth_headers(client):
    """Get authentication headers for testing protected routes."""
    # Create a test user
    with client.application.app_context():
        from harithmapos import bcrypt
        hashed_password = bcrypt.generate_password_hash('testpassword').decode('utf-8')
        user = User(
            name='Test User',
            email='test@example.com',
            password=hashed_password
        )
        db.session.add(user)
        db.session.commit()
    
    # Login and get session
    response = client.post('/app/login', data={
        'email': 'test@example.com',
        'password': 'testpassword'
    }, follow_redirects=True)
    
    return response

@pytest.fixture
def sample_customer():
    """Create a sample customer for testing."""
    return Customer(
        name='John Doe',
        contact='123456789',  # 9 characters as required
        address='123 Main St',
        email='john@example.com'
    )

@pytest.fixture
def sample_vehicle(sample_customer):
    """Create a sample vehicle for testing."""
    return Vehicle(
        number='ABC-1234',
        make='Toyota',
        model='Camry',
        year=2020,
        owner_id=sample_customer.id
    )

@pytest.fixture
def sample_supplier():
    """Create a sample supplier for testing."""
    return Supplier(
        name='Test Supplier',
        contact='987654321',  # 9 characters as required
        address='456 Supplier St'
    )

@pytest.fixture
def sample_employee():
    """Create a sample employee for testing."""
    return Employee(
        name='Jane Smith',
        contact='555555555',  # 9 characters as required
        address='789 Employee Ave',
        designation='Manager',
        wage=50000.0
    )

@pytest.fixture
def sample_item():
    """Create a sample item for testing."""
    return Item(
        name='Test Item',
        description='A test item',
        unit_of_measure='piece',
        quantity=100,
        unit_cost=10.0,
        unit_price=15.0,
        discount_pct=5.0
    )

@pytest.fixture
def sample_washbay():
    """Create a sample washbay for testing."""
    return WashBay(
        name='Bay 1',
        remarks='Main wash bay',
        capacity=1
    )
