"""
Unit tests for business logic and utilities
"""

import pytest
from datetime import datetime, date
from harithmapos import db
from harithmapos.models import (
    Customer, Vehicle, Supplier, Employee, Item, WashBay,
    InvoiceHead, InvoiceDetail, Payment, InvoiceStatusLog
)
from harithmapos.views.invoice.routes import (
    convert_service_invoice_to_json,
    update_total_values
)
from harithmapos.views.purchase_order.routes import get_id

class TestInvoiceBusinessLogic:
    """Test invoice-related business logic"""
    
    def test_invoice_total_calculation(self, app, sample_customer, sample_vehicle, sample_employee, sample_washbay, sample_item):
        """Test invoice total calculation"""
        with app.app_context():
            # Add related entities
            db.session.add(sample_customer)
            db.session.commit()
            
            # Update vehicle with correct owner_id
            sample_vehicle.owner_id = sample_customer.id
            db.session.add(sample_vehicle)
            db.session.add(sample_employee)
            db.session.add(sample_washbay)
            db.session.add(sample_item)
            db.session.commit()
            
            # Create invoice head
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
            
            # Create invoice detail
            invoice_detail = InvoiceDetail(
                invoice_head_id=invoice_head.id,
                item_id=sample_item.id,
                quantity=2,
                total_cost=sample_item.unit_cost * 2,
                total_price=sample_item.unit_price * 2,
                discount_amount=sample_item.discount_pct * sample_item.unit_price * 2 / 100,
                gross_price=(sample_item.unit_price * 2) - (sample_item.discount_pct * sample_item.unit_price * 2 / 100)
            )
            db.session.add(invoice_detail)
            db.session.commit()
            
            # Update total values
            update_total_values(invoice_head)
            
            # Verify totals are calculated correctly
            assert invoice_head.total_cost == sample_item.unit_cost * 2
            assert invoice_head.total_price == sample_item.unit_price * 2
            assert invoice_head.discount_amount == sample_item.discount_pct * sample_item.unit_price * 2 / 100
            assert invoice_head.gross_price == (sample_item.unit_price * 2) - (sample_item.discount_pct * sample_item.unit_price * 2 / 100)
    
    def test_invoice_status_progression(self, app, sample_customer, sample_vehicle, sample_employee, sample_washbay):
        """Test invoice status progression"""
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
            
            # Create invoice head
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
            
            # Verify initial status
            assert invoice_head.service_status == 1  # Initial status
            
            # Create initial status log
            status_log = InvoiceStatusLog(
                invoice_id=invoice_head.id,
                service_status=invoice_head.service_status,
                employee_id=sample_employee.id
            )
            db.session.add(status_log)
            db.session.commit()
            
            # Update status
            invoice_head.service_status = 2
            db.session.commit()
            
            # Create new status log
            new_status_log = InvoiceStatusLog(
                previous_invoice_status_log_id=status_log.id,
                invoice_id=invoice_head.id,
                service_status=invoice_head.service_status,
                employee_id=sample_employee.id
            )
            db.session.add(new_status_log)
            db.session.commit()
            
            # Verify status progression
            assert invoice_head.service_status == 2
            assert new_status_log.previous_invoice_status_log_id == status_log.id
    
    def test_payment_processing(self, app, sample_customer, sample_employee):
        """Test payment processing logic"""
        with app.app_context():
            # Add related entities
            db.session.add(sample_customer)
            db.session.add(sample_employee)
            db.session.commit()
            
            # Create payment
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
            
            # Verify payment details
            assert payment.payment_amount == 100.0
            assert payment.payment_method == 'cash'
            assert payment.payment_direction == 'in'
            assert payment.payment_type == 'general'
            assert payment.remarks == 'Test payment'

class TestItemBusinessLogic:
    """Test item-related business logic"""
    
    def test_item_quantity_management(self, app):
        """Test item quantity management"""
        with app.app_context():
            # Create item
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
            
            # Verify initial quantity
            assert item.quantity == 100
            
            # Simulate item usage (reduce quantity)
            item.quantity -= 5
            db.session.commit()
            
            # Verify updated quantity
            assert item.quantity == 95
    
    def test_item_discount_calculation(self, app):
        """Test item discount calculation"""
        with app.app_context():
            # Create item with discount
            item = Item(
                name='Discounted Item',
                description='An item with discount',
                unit_of_measure='piece',
                quantity=50,
                unit_cost=20.0,
                unit_price=30.0,
                discount_pct=10.0
            )
            db.session.add(item)
            db.session.commit()
            
            # Calculate discount for 2 items
            quantity = 2
            total_price = item.unit_price * quantity
            discount_amount = item.discount_pct * total_price / 100
            gross_price = total_price - discount_amount
            
            # Verify calculations
            assert total_price == 60.0  # 30 * 2
            assert discount_amount == 6.0  # 10% of 60
            assert gross_price == 54.0  # 60 - 6

class TestCustomerBusinessLogic:
    """Test customer-related business logic"""
    
    def test_customer_vehicle_relationship(self, app):
        """Test customer-vehicle relationship management"""
        with app.app_context():
            # Create customer
            customer = Customer(
                name='Vehicle Owner',
                contact='1234567890',
                address='123 Vehicle St',
                email='owner@example.com'
            )
            db.session.add(customer)
            db.session.commit()
            
            # Create multiple vehicles for same customer
            vehicle1 = Vehicle(
                number='VEH-001',
                make='Toyota',
                model='Camry',
                year=2020,
                owner_id=customer.id
            )
            vehicle2 = Vehicle(
                number='VEH-002',
                make='Honda',
                model='Civic',
                year=2021,
                owner_id=customer.id
            )
            
            db.session.add(vehicle1)
            db.session.add(vehicle2)
            db.session.commit()
            
            # Verify customer has both vehicles
            assert len(customer.vehicles) == 2
            assert customer.vehicles[0].number == 'VEH-001'
            assert customer.vehicles[1].number == 'VEH-002'
            
            # Verify vehicles belong to customer
            assert vehicle1.owner.name == 'Vehicle Owner'
            assert vehicle2.owner.name == 'Vehicle Owner'

class TestEmployeeBusinessLogic:
    """Test employee-related business logic"""
    
    def test_employee_wage_calculation(self, app):
        """Test employee wage calculations"""
        with app.app_context():
            # Create employee with wage
            employee = Employee(
                name='Wage Employee',
                contact='5555555555',
                address='123 Wage St',
                designation='Technician',
                joined_date=date(2023, 1, 1),
                wage=25.0  # Hourly wage
            )
            db.session.add(employee)
            db.session.commit()
            
            # Verify wage details
            assert employee.wage == 25.0
            assert employee.designation == 'Technician'
            assert employee.joined_date == date(2023, 1, 1)
    
    def test_employee_designation_hierarchy(self, app):
        """Test employee designation hierarchy"""
        with app.app_context():
            # Create employees with different designations
            manager = Employee(
                name='Manager',
                contact='1111111111',
                address='123 Manager St',
                designation='Manager',
                wage=50000.0
            )
            technician = Employee(
                name='Technician',
                contact='2222222222',
                address='456 Tech St',
                designation='Technician',
                wage=30000.0
            )
            
            db.session.add(manager)
            db.session.add(technician)
            db.session.commit()
            
            # Verify different designations
            assert manager.designation == 'Manager'
            assert technician.designation == 'Technician'
            assert manager.wage > technician.wage

class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_get_id_function(self, app):
        """Test the get_id utility function"""
        with app.app_context():
            # Test with different table names
            customer_id = get_id('customer')
            vehicle_id = get_id('vehicle')
            supplier_id = get_id('supplier')
            
            # Verify IDs are generated
            assert customer_id is not None
            assert vehicle_id is not None
            assert supplier_id is not None
            
            # Verify IDs are different
            assert customer_id != vehicle_id
            assert vehicle_id != supplier_id
    
    def test_convert_service_invoice_to_json(self, app, sample_customer, sample_vehicle, sample_employee, sample_washbay):
        """Test service invoice JSON conversion"""
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
            
            # Create invoice head
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
            
            # Convert to JSON
            json_data = convert_service_invoice_to_json(invoice_head)
            
            # Verify JSON structure
            assert 'invoice_id' in json_data
            assert 'customer_name' in json_data
            assert 'vehicle_number' in json_data
            assert 'employee_name' in json_data
            assert 'washbay_name' in json_data
            assert 'current_milage' in json_data
            assert 'next_milage' in json_data
            assert 'payment_method' in json_data
            
            # Verify data values
            assert json_data['invoice_id'] == invoice_head.id
            assert json_data['customer_name'] == sample_customer.name
            assert json_data['vehicle_number'] == sample_vehicle.number
            assert json_data['employee_name'] == sample_employee.name
            assert json_data['washbay_name'] == sample_washbay.name
            assert json_data['current_milage'] == 50000
            assert json_data['next_milage'] == 55000
            assert json_data['payment_method'] == 'cash'

class TestDataIntegrity:
    """Test data integrity and constraints"""
    
    def test_foreign_key_constraints(self, app):
        """Test foreign key constraints"""
        with app.app_context():
            # Try to create vehicle with non-existent customer
            with pytest.raises(Exception):
                vehicle = Vehicle(
                    number='INVALID-1234',
                    make='Test',
                    model='Car',
                    year=2020,
                    owner_id=99999  # Non-existent customer
                )
                db.session.add(vehicle)
                db.session.commit()
    
    def test_unique_constraints(self, app):
        """Test unique constraints"""
        with app.app_context():
            # Create first customer
            customer1 = Customer(
                name='First Customer',
                contact='1111111111',
                address='123 First St',
                email='first@example.com'
            )
            db.session.add(customer1)
            db.session.commit()
            
            # Try to create customer with same email
            customer2 = Customer(
                name='Second Customer',
                contact='2222222222',
                address='456 Second St',
                email='first@example.com'  # Same email
            )
            db.session.add(customer2)
            
            # Should raise integrity error
            with pytest.raises(Exception):
                db.session.commit()
    
    def test_required_field_constraints(self, app):
        """Test required field constraints"""
        with app.app_context():
            # Try to create customer without required fields
            with pytest.raises(Exception):
                customer = Customer()  # Missing required fields
                db.session.add(customer)
                db.session.commit()
