"""
Unit tests for database models
"""

import pytest
from datetime import datetime
from harithmapos import db
from harithmapos.models import (
    User, Customer, Vehicle, Supplier, Employee, Item, WashBay,
    InvoiceHead, InvoiceDetail, Payment, InvoiceStatusLog
)

class TestUserModel:
    """Test the User model"""
    
    def test_user_creation(self, app):
        """Test creating a user"""
        with app.app_context():
            user = User(
                name='Test User',
                email='test@example.com',
                password='hashedpassword'
            )
            db.session.add(user)
            db.session.commit()
            
            assert user.id is not None
            assert user.name == 'Test User'
            assert user.email == 'test@example.com'
            assert user.password == 'hashedpassword'
            assert user.create_dttm is not None
            assert user.update_dttm is not None
    
    def test_user_repr(self, app):
        """Test user string representation"""
        with app.app_context():
            user = User(
                name='Test User',
                email='test@example.com',
                password='hashedpassword'
            )
            db.session.add(user)
            db.session.commit()
            
            assert 'Test User' in str(user)
            assert 'test@example.com' in str(user)

class TestCustomerModel:
    """Test the Customer model"""
    
    def test_customer_creation(self, app):
        """Test creating a customer"""
        with app.app_context():
            customer = Customer(
                name='John Doe',
                contact='1234567890',
                address='123 Main St',
                email='john@example.com'
            )
            db.session.add(customer)
            db.session.commit()
            
            assert customer.id is not None
            assert customer.name == 'John Doe'
            assert customer.contact == '1234567890'
            assert customer.address == '123 Main St'
            assert customer.email == 'john@example.com'
            assert customer.create_dttm is not None
            assert customer.update_dttm is not None
    
    def test_customer_vehicles_relationship(self, app):
        """Test customer-vehicles relationship"""
        with app.app_context():
            customer = Customer(
                name='John Doe',
                contact='1234567890',
                address='123 Main St',
                email='john@example.com'
            )
            db.session.add(customer)
            db.session.commit()
            
            vehicle = Vehicle(
                number='ABC-1234',
                make='Toyota',
                model='Camry',
                year=2020,
                owner_id=customer.id
            )
            db.session.add(vehicle)
            db.session.commit()
            
            assert len(customer.vehicles) == 1
            assert customer.vehicles[0].number == 'ABC-1234'
            assert vehicle.owner.name == 'John Doe'

class TestVehicleModel:
    """Test the Vehicle model"""
    
    def test_vehicle_creation(self, app, sample_customer):
        """Test creating a vehicle"""
        with app.app_context():
            db.session.add(sample_customer)
            db.session.commit()
            
            vehicle = Vehicle(
                number='XYZ-5678',
                make='Honda',
                model='Civic',
                year=2021,
                owner_id=sample_customer.id
            )
            db.session.add(vehicle)
            db.session.commit()
            
            assert vehicle.id is not None
            assert vehicle.number == 'XYZ-5678'
            assert vehicle.make == 'Honda'
            assert vehicle.model == 'Civic'
            assert vehicle.year == '2021'  # Year is stored as string
            assert vehicle.owner_id == sample_customer.id
            assert vehicle.owner.name == sample_customer.name

class TestSupplierModel:
    """Test the Supplier model"""
    
    def test_supplier_creation(self, app):
        """Test creating a supplier"""
        with app.app_context():
            supplier = Supplier(
                name='Test Supplier',
                contact='9876543210',
                address='456 Supplier St'
            )
            db.session.add(supplier)
            db.session.commit()
            
            assert supplier.id is not None
            assert supplier.name == 'Test Supplier'
            assert supplier.contact == '9876543210'
            assert supplier.address == '456 Supplier St'
            assert supplier.create_dttm is not None
            assert supplier.update_dttm is not None

class TestEmployeeModel:
    """Test the Employee model"""
    
    def test_employee_creation(self, app):
        """Test creating an employee"""
        with app.app_context():
            employee = Employee(
                name='Jane Smith',
                contact='5555555555',
                address='789 Employee Ave',
                designation='Manager',
                joined_date=datetime.now().date(),
                wage=50000.0
            )
            db.session.add(employee)
            db.session.commit()
            
            assert employee.id is not None
            assert employee.name == 'Jane Smith'
            assert employee.contact == '5555555555'
            assert employee.address == '789 Employee Ave'
            assert employee.designation == 'Manager'
            assert employee.joined_date is not None
            assert employee.wage == 50000.0

class TestItemModel:
    """Test the Item model"""
    
    def test_item_creation(self, app):
        """Test creating an item"""
        with app.app_context():
            item = Item(
                name='Test Item',
                description='A test item',
                unit_of_measure='piece',
                quantity=100,
                unit_cost=10.0,
                unit_price=15.0,
                discount_pct=5.0
            )
            db.session.add(item)
            db.session.commit()
            
            assert item.id is not None
            assert item.name == 'Test Item'
            assert item.description == 'A test item'
            assert item.unit_of_measure == 'piece'
            assert item.quantity == 100
            assert item.unit_cost == 10.0
            assert item.unit_price == 15.0
            assert item.discount_pct == 5.0

class TestWashBayModel:
    """Test the WashBay model"""
    
    def test_washbay_creation(self, app):
        """Test creating a washbay"""
        with app.app_context():
            washbay = WashBay(
                name='Bay 1',
                remarks='Main wash bay',
                capacity=1
            )
            db.session.add(washbay)
            db.session.commit()
            
            assert washbay.id is not None
            assert washbay.name == 'Bay 1'
            assert washbay.remarks == 'Main wash bay'
            assert washbay.capacity == 1

class TestInvoiceHeadModel:
    """Test the InvoiceHead model"""
    
    def test_invoice_head_creation(self, app, sample_customer, sample_vehicle, sample_employee, sample_washbay):
        """Test creating an invoice head"""
        with app.app_context():
            # Add related entities
            db.session.add(sample_customer)
            db.session.commit()
            
            # Update vehicle with correct owner_id
            sample_vehicle.owner_id = sample_customer.id
            db.session.add(sample_vehicle)
            db.session.add(sample_employee)
            db.session.add(sample_washbay)
            db.session.commit()
            
            invoice_head = InvoiceHead(
                customer_id=sample_customer.id,
                vehicle_id=sample_vehicle.id,
                washbay_id=sample_washbay.id,
                employee_id=sample_employee.id,
                current_milage=50000,
                next_milage=55000,
                payment_method='cash'
            )
            db.session.add(invoice_head)
            db.session.commit()
            
            assert invoice_head.id is not None
            assert invoice_head.customer_id == sample_customer.id
            assert invoice_head.vehicle_id == sample_vehicle.id
            assert invoice_head.washbay_id == sample_washbay.id
            assert invoice_head.employee_id == sample_employee.id
            assert invoice_head.current_milage == 50000
            assert invoice_head.next_milage == 55000
            assert invoice_head.payment_method == 'cash'
            assert invoice_head.service_status == 0  # Default status
            assert invoice_head.created_dttm is not None
            assert invoice_head.update_dttm is not None

class TestPaymentModel:
    """Test the Payment model"""
    
    def test_payment_creation(self, app, sample_customer, sample_employee):
        """Test creating a payment"""
        with app.app_context():
            # Add related entities
            db.session.add(sample_customer)
            db.session.add(sample_employee)
            db.session.commit()
            
            payment = Payment(
                customer_id=sample_customer.id,
                employee_id=sample_employee.id,
                payment_method='cash',
                payment_direction='in',
                payment_amount=100.0,
                payment_type='general',
                remarks='Test payment'
            )
            db.session.add(payment)
            db.session.commit()
            
            assert payment.id is not None
            assert payment.customer_id == sample_customer.id
            assert payment.employee_id == sample_employee.id
            assert payment.payment_method == 'cash'
            assert payment.payment_direction == 'in'
            assert payment.payment_amount == 100.0
            assert payment.payment_type == 'general'
            assert payment.remarks == 'Test payment'
            assert payment.created_dttm is not None
            assert payment.update_dttm is not None

