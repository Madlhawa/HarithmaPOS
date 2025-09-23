"""
Unit tests for Flask routes
"""

import pytest
import json
from harithmapos import db
from harithmapos.models import User, Customer, Vehicle, Supplier, Employee, Item, WashBay

class TestCustomerRoutes:
    """Test customer-related routes"""
    
    def test_customer_list_page(self, client, app):
        """Test customer list page loads correctly"""
        with app.app_context():
            # Create test user and login
            user = User(
                name='Test User',
                email='test@example.com',
                password='hashedpassword'
            )
            db.session.add(user)
            db.session.commit()
            
            # Login
            response = client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'hashedpassword'
            }, follow_redirects=True)
            
            # Test customer list page
            response = client.get('/app/customer/')
            assert response.status_code == 200
            assert b'Customers' in response.data
    
    def test_customer_creation(self, client, app):
        """Test creating a new customer"""
        with app.app_context():
            # Create test user and login
            user = User(
                name='Test User',
                email='test@example.com',
                password='hashedpassword'
            )
            db.session.add(user)
            db.session.commit()
            
            # Login
            client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'hashedpassword'
            }, follow_redirects=True)
            
            # Create customer
            response = client.post('/app/insert_customer/', data={
                'name': 'Test Customer',
                'contact': '1234567890',
                'address': '123 Test St',
                'email': 'testcustomer@example.com'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verify customer was created
            customer = Customer.query.filter_by(name='Test Customer').first()
            assert customer is not None
            assert customer.contact == '1234567890'
            assert customer.address == '123 Test St'
            assert customer.email == 'testcustomer@example.com'
    
    def test_customer_search(self, client, app):
        """Test customer search functionality"""
        with app.app_context():
            # Create test user and login
            user = User(
                name='Test User',
                email='test@example.com',
                password='hashedpassword'
            )
            db.session.add(user)
            db.session.commit()
            
            # Create test customer
            customer = Customer(
                name='Search Test Customer',
                contact='9876543210',
                address='456 Search St',
                email='search@example.com'
            )
            db.session.add(customer)
            db.session.commit()
            
            # Login
            client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'hashedpassword'
            }, follow_redirects=True)
            
            # Search for customer
            response = client.post('/app/customer/', data={
                'query': 'Search Test'
            })
            
            assert response.status_code == 200
            assert b'Search Test Customer' in response.data

class TestVehicleRoutes:
    """Test vehicle-related routes"""
    
    def test_vehicle_creation(self, client, app):
        """Test creating a new vehicle"""
        with app.app_context():
            # Create test user and login
            user = User(
                name='Test User',
                email='test@example.com',
                password='hashedpassword'
            )
            db.session.add(user)
            db.session.commit()
            
            # Create test customer
            customer = Customer(
                name='Vehicle Owner',
                contact='1111111111',
                address='123 Vehicle St',
                email='owner@example.com'
            )
            db.session.add(customer)
            db.session.commit()
            
            # Login
            client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'hashedpassword'
            }, follow_redirects=True)
            
            # Create vehicle
            response = client.post('/app/insert_vehicle/', data={
                'number': 'TEST-1234',
                'make': 'Toyota',
                'model': 'Camry',
                'year': 2020,
                'owner_id': customer.id
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verify vehicle was created
            vehicle = Vehicle.query.filter_by(number='TEST-1234').first()
            assert vehicle is not None
            assert vehicle.make == 'Toyota'
            assert vehicle.model == 'Camry'
            assert vehicle.year == 2020
            assert vehicle.owner_id == customer.id

class TestSupplierRoutes:
    """Test supplier-related routes"""
    
    def test_supplier_creation(self, client, app):
        """Test creating a new supplier"""
        with app.app_context():
            # Create test user and login
            user = User(
                name='Test User',
                email='test@example.com',
                password='hashedpassword'
            )
            db.session.add(user)
            db.session.commit()
            
            # Login
            client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'hashedpassword'
            }, follow_redirects=True)
            
            # Create supplier
            response = client.post('/app/supplier/create', data={
                'name': 'Test Supplier',
                'contact': '2222222222',
                'address': '789 Supplier Ave'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verify supplier was created
            supplier = Supplier.query.filter_by(name='Test Supplier').first()
            assert supplier is not None
            assert supplier.contact == '2222222222'
            assert supplier.address == '789 Supplier Ave'

class TestEmployeeRoutes:
    """Test employee-related routes"""
    
    def test_employee_creation(self, client, app):
        """Test creating a new employee"""
        with app.app_context():
            # Create test user and login
            user = User(
                name='Test User',
                email='test@example.com',
                password='hashedpassword'
            )
            db.session.add(user)
            db.session.commit()
            
            # Login
            client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'hashedpassword'
            }, follow_redirects=True)
            
            # Create employee
            response = client.post('/app/employee/create', data={
                'name': 'Test Employee',
                'contact': '3333333333',
                'address': '456 Employee St',
                'designation': 'Manager',
                'joined_date': '2023-01-01',
                'wage': 50000.0
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verify employee was created
            employee = Employee.query.filter_by(name='Test Employee').first()
            assert employee is not None
            assert employee.contact == '3333333333'
            assert employee.address == '456 Employee St'
            assert employee.designation == 'Manager'
            assert employee.wage == 50000.0

class TestItemRoutes:
    """Test item-related routes"""
    
    def test_item_creation(self, client, app):
        """Test creating a new item"""
        with app.app_context():
            # Create test user and login
            user = User(
                name='Test User',
                email='test@example.com',
                password='hashedpassword'
            )
            db.session.add(user)
            db.session.commit()
            
            # Login
            client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'hashedpassword'
            }, follow_redirects=True)
            
            # Create item
            response = client.post('/app/item/create', data={
                'name': 'Test Item',
                'description': 'A test item',
                'unit_of_measure': 'piece',
                'quantity': 100,
                'unit_cost': 10.0,
                'unit_price': 15.0,
                'discount_pct': 5.0
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verify item was created
            item = Item.query.filter_by(name='Test Item').first()
            assert item is not None
            assert item.description == 'A test item'
            assert item.unit_of_measure == 'piece'
            assert item.quantity == 100
            assert item.unit_cost == 10.0
            assert item.unit_price == 15.0
            assert item.discount_pct == 5.0

class TestWashBayRoutes:
    """Test washbay-related routes"""
    
    def test_washbay_creation(self, client, app):
        """Test creating a new washbay"""
        with app.app_context():
            # Create test user and login
            user = User(
                name='Test User',
                email='test@example.com',
                password='hashedpassword'
            )
            db.session.add(user)
            db.session.commit()
            
            # Login
            client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'hashedpassword'
            }, follow_redirects=True)
            
            # Create washbay
            response = client.post('/app/washbay/create', data={
                'name': 'Test Bay',
                'remarks': 'Test wash bay',
                'capacity': 1
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verify washbay was created
            washbay = WashBay.query.filter_by(name='Test Bay').first()
            assert washbay is not None
            assert washbay.remarks == 'Test wash bay'
            assert washbay.capacity == 1

class TestAuthenticationRoutes:
    """Test authentication-related routes"""
    
    def test_user_registration(self, client, app):
        """Test user registration"""
        response = client.post('/app/register', data={
            'name': 'New User',
            'email': 'newuser@example.com',
            'password': 'newpassword',
            'confirm_password': 'newpassword'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify user was created
        with app.app_context():
            user = User.query.filter_by(email='newuser@example.com').first()
            assert user is not None
            assert user.name == 'New User'
    
    def test_user_login(self, client, app):
        """Test user login"""
        with app.app_context():
            # Create test user
            user = User(
                name='Login Test User',
                email='logintest@example.com',
                password='hashedpassword'
            )
            db.session.add(user)
            db.session.commit()
            
            # Test login
            response = client.post('/app/login', data={
                'email': 'logintest@example.com',
                'password': 'hashedpassword'
            }, follow_redirects=True)
            
            assert response.status_code == 200
    
    def test_protected_route_access(self, client, app):
        """Test that protected routes require authentication"""
        # Try to access protected route without login
        response = client.get('/app/customer/', follow_redirects=True)
        
        # Should redirect to login page
        assert response.status_code == 200
        assert b'login' in response.data.lower()

class TestSearchRoutes:
    """Test search functionality"""
    
    def test_vehicle_search(self, client, app):
        """Test vehicle search API"""
        with app.app_context():
            # Create test user and login
            user = User(
                name='Test User',
                email='test@example.com',
                password='hashedpassword'
            )
            db.session.add(user)
            db.session.commit()
            
            # Create test customer and vehicle
            customer = Customer(
                name='Search Owner',
                contact='4444444444',
                address='123 Search St',
                email='searchowner@example.com'
            )
            db.session.add(customer)
            db.session.commit()
            
            vehicle = Vehicle(
                number='SEARCH-1234',
                make='Honda',
                model='Accord',
                year=2021,
                owner_id=customer.id
            )
            db.session.add(vehicle)
            db.session.commit()
            
            # Login
            client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'hashedpassword'
            }, follow_redirects=True)
            
            # Test vehicle search
            response = client.get('/app/search/vehicles?q=SEARCH')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data) > 0
            assert any(v['number'] == 'SEARCH-1234' for v in data)

