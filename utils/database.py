#!/usr/bin/env python3
"""
Database utilities for Harithma POS
Provides tools for database maintenance, sequence fixing, and safe database operations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harithmapos import create_app, db
from sqlalchemy import text

def safe_insert_with_sequence_check(model_class, **kwargs):
    """
    Safely insert a new record with automatic sequence checking
    
    Args:
        model_class: The SQLAlchemy model class to create
        **kwargs: Model field values
    
    Returns:
        The created model instance
    """
    try:
        # Create the new instance
        new_record = model_class(**kwargs)
        db.session.add(new_record)
        db.session.commit()
        
        print(f"✅ Successfully created {model_class.__name__} with ID: {new_record.id}")
        return new_record
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creating {model_class.__name__}: {str(e)}")
        
        # If it's a sequence issue, fix it and retry
        if "duplicate key value" in str(e) and "violates unique constraint" in str(e):
            print("🔧 Detected sequence issue, fixing...")
            fix_sequence_for_table(model_class.__tablename__)
            
            # Retry the insertion
            try:
                new_record = model_class(**kwargs)
                db.session.add(new_record)
                db.session.commit()
                print(f"✅ Successfully created {model_class.__name__} after sequence fix")
                return new_record
            except Exception as retry_error:
                print(f"❌ Still failed after sequence fix: {str(retry_error)}")
                raise retry_error
        else:
            raise e

def fix_sequence_for_table(table_name):
    """Fix sequence for a specific table"""
    try:
        # Get current max ID
        result = db.session.execute(text(f"SELECT MAX(id) FROM {table_name}"))
        max_id = result.fetchone()[0]
        
        if max_id is not None:
            # Reset sequence
            sequence_name = f"{table_name}_id_seq"
            db.session.execute(text(f"SELECT setval('{sequence_name}', {max_id});"))
            db.session.commit()
            print(f"✅ Fixed sequence for {table_name} (max_id: {max_id})")
        else:
            print(f"⚠️  Table {table_name} is empty")
            
    except Exception as e:
        print(f"❌ Error fixing sequence for {table_name}: {str(e)}")

def check_database_health():
    """Check database for common issues"""
    print("🔍 Checking database health...")
    
    # Check for sequence issues
    tables = ['customer', 'vehicle', 'employee', 'supplier', 'item']
    
    for table in tables:
        try:
            # Check if sequence exists and is properly set
            result = db.session.execute(text(f"""
                SELECT last_value FROM {table}_id_seq;
            """))
            last_value = result.fetchone()[0]
            
            # Get max ID from table
            max_result = db.session.execute(text(f"SELECT MAX(id) FROM {table}"))
            max_id = max_result.fetchone()[0]
            
            if max_id and last_value < max_id:
                print(f"⚠️  {table}: Sequence needs fixing (last_value: {last_value}, max_id: {max_id})")
            else:
                print(f"✅ {table}: Sequence is healthy")
                
        except Exception as e:
            print(f"❌ {table}: Error checking sequence - {str(e)}")

def fix_database_sequences():
    """Fix all database sequences to prevent primary key conflicts"""
    app = create_app()
    
    with app.app_context():
        try:
            # List of tables with auto-incrementing primary keys
            tables_to_fix = [
                'customer',
                'vehicle', 
                'employee',
                'supplier',
                'item',
                'wash_bay',
                'invoice_head',
                'invoice_detail',
                'item_invoice_head',
                'item_invoice_detail',
                'purchase_order_head',
                'purchase_order_detail',
                'payment',
                'invoice_status_log'
            ]
            
            print("🔧 Fixing database sequences...")
            
            for table in tables_to_fix:
                try:
                    # Get the current max ID from the table
                    result = db.session.execute(text(f"SELECT MAX(id) FROM {table}"))
                    max_id = result.fetchone()[0]
                    
                    if max_id is not None:
                        # Reset the sequence to max_id + 1
                        sequence_name = f"{table}_id_seq"
                        db.session.execute(text(f"SELECT setval('{sequence_name}', {max_id});"))
                        db.session.commit()
                        print(f"✅ Fixed sequence for {table} (max_id: {max_id})")
                    else:
                        print(f"⚠️  Table {table} is empty, skipping...")
                        
                except Exception as e:
                    print(f"❌ Error fixing {table}: {str(e)}")
            
            print("🎉 All sequences fixed successfully!")
            
        except Exception as e:
            print(f"❌ Error fixing sequences: {str(e)}")

if __name__ == "__main__":
    # Can be run standalone for testing
    print("Choose an option:")
    print("1. Check database health")
    print("2. Fix all sequences")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        check_database_health()
    elif choice == "2":
        fix_database_sequences()
    else:
        print("Invalid choice. Running health check by default.")
        check_database_health()
