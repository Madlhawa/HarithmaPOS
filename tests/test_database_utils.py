"""
Unit tests for database utilities
"""

import pytest
from harithmapos import db
from harithmapos.models import Customer, Vehicle, Supplier, Employee, Item, WashBay
from utils.database import (
    safe_insert_with_sequence_check,
    fix_sequence_for_table,
    check_database_health,
    fix_database_sequences
)

class TestSafeInsertWithSequenceCheck:
    """Test the safe_insert_with_sequence_check function"""
    
    def test_successful_insert(self, app, sample_customer):
        """Test successful insertion without sequence issues"""
        with app.app_context():
            # Add customer to database first
            db.session.add(sample_customer)
            db.session.commit()
            
            # Test safe insert for vehicle
            vehicle = safe_insert_with_sequence_check(
                Vehicle,
                number='TEST-1234',
                make='Honda',
                model='Civic',
                year=2021,
                owner_id=sample_customer.id
            )
            
            assert vehicle is not None
            assert vehicle.number == 'TEST-1234'
            assert vehicle.make == 'Honda'
            assert vehicle.model == 'Civic'
            assert vehicle.year == '2021'  # Year is stored as string
            assert vehicle.owner_id == sample_customer.id
    
    def test_sequence_conflict_handling(self, app, sample_customer):
        """Test handling of sequence conflicts"""
        with app.app_context():
            # Add customer to database
            db.session.add(sample_customer)
            db.session.commit()
            
            # Manually create a vehicle to cause sequence conflict
            vehicle1 = Vehicle(
                number='CONFLICT-1',
                make='Toyota',
                model='Corolla',
                year=2020,
                owner_id=sample_customer.id
            )
            db.session.add(vehicle1)
            db.session.commit()
            
            # Manually reset sequence to cause conflict
            from sqlalchemy import text
            db.session.execute(text("SELECT setval('vehicle_id_seq', 1);"))
            db.session.commit()
            
            # This should trigger sequence conflict and auto-fix
            vehicle2 = safe_insert_with_sequence_check(
                Vehicle,
                number='CONFLICT-2',
                make='Nissan',
                model='Altima',
                year=2022,
                owner_id=sample_customer.id
            )
            
            assert vehicle2 is not None
            assert vehicle2.number == 'CONFLICT-2'
            assert vehicle2.id > vehicle1.id
    
    def test_invalid_data_handling(self, app):
        """Test handling of invalid data"""
        with app.app_context():
            with pytest.raises(Exception):
                # Try to insert vehicle with invalid owner_id
                safe_insert_with_sequence_check(
                    Vehicle,
                    number='INVALID-1234',
                    make='Test',
                    model='Car',
                    year=2020,
                    owner_id=99999  # Non-existent customer
                )

class TestFixSequenceForTable:
    """Test the fix_sequence_for_table function"""
    
    def test_fix_sequence_with_data(self, app, sample_customer):
        """Test fixing sequence for table with data"""
        with app.app_context():
            # Add customer to database
            db.session.add(sample_customer)
            db.session.commit()
            
            # Manually reset sequence to cause conflict
            from sqlalchemy import text
            db.session.execute(text("SELECT setval('customer_id_seq', 1);"))
            db.session.commit()
            
            # Fix the sequence
            fix_sequence_for_table('customer')
            
            # Verify sequence is fixed by checking next insert
            customer2 = Customer(
                name='Jane Doe',
                contact='0987654321',
                address='456 Oak St',
                email='jane@example.com'
            )
            db.session.add(customer2)
            db.session.commit()
            
            assert customer2.id > sample_customer.id
    
    def test_fix_sequence_empty_table(self, app):
        """Test fixing sequence for empty table"""
        with app.app_context():
            # Should not raise exception for empty table
            fix_sequence_for_table('customer')
    
    def test_fix_sequence_nonexistent_table(self, app):
        """Test fixing sequence for non-existent table"""
        with app.app_context():
            # Should handle non-existent table gracefully
            fix_sequence_for_table('nonexistent_table')

class TestCheckDatabaseHealth:
    """Test the check_database_health function"""
    
    def test_healthy_database(self, app, sample_customer):
        """Test health check on healthy database"""
        with app.app_context():
            # Add some data
            db.session.add(sample_customer)
            db.session.commit()
            
            # Should not raise exception
            check_database_health()
    
    def test_unhealthy_database(self, app, sample_customer):
        """Test health check on database with sequence issues"""
        with app.app_context():
            # Add customer
            db.session.add(sample_customer)
            db.session.commit()
            
            # Manually create sequence conflict
            from sqlalchemy import text
            db.session.execute(text("SELECT setval('customer_id_seq', 1);"))
            db.session.commit()
            
            # Should detect the issue
            check_database_health()

class TestFixDatabaseSequences:
    """Test the fix_database_sequences function"""
    
    def test_fix_all_sequences(self, app, sample_customer, sample_supplier, sample_employee):
        """Test fixing all database sequences"""
        with app.app_context():
            # Add some data
            db.session.add(sample_customer)
            db.session.add(sample_supplier)
            db.session.add(sample_employee)
            db.session.commit()
            
            # Create sequence conflicts
            from sqlalchemy import text
            db.session.execute(text("SELECT setval('customer_id_seq', 1);"))
            db.session.execute(text("SELECT setval('supplier_id_seq', 1);"))
            db.session.execute(text("SELECT setval('employee_id_seq', 1);"))
            db.session.commit()
            
            # Fix all sequences
            fix_database_sequences()
            
            # Verify sequences are fixed by inserting new records
            customer2 = Customer(
                name='Test Customer 2',
                contact='1111111111',
                address='Test Address',
                email='test2@example.com'
            )
            db.session.add(customer2)
            db.session.commit()
            
            assert customer2.id > sample_customer.id

