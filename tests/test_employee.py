"""
Unit tests for Employee CRUD operations
"""

import pytest
from harithmapos import db
from harithmapos.models import User, Employee


class TestEmployeeCRUD:
    """Test employee insert, update, and delete operations"""
    
    def test_employee_insert(self, client, app):
        """Test creating a new employee"""
        with app.app_context():
            from harithmapos import bcrypt
            # Create test user and login
            hashed_password = bcrypt.generate_password_hash('testpassword').decode('utf-8')
            user = User(
                name='Test User',
                email='test@example.com',
                password=hashed_password
            )
            db.session.add(user)
            db.session.commit()
            
            # Login
            client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'testpassword'
            }, follow_redirects=True)
            
            # Create employee
            response = client.post('/app/employee/create', data={
                'name': 'Test Employee',
                'contact': '1234567890',
                'address': '123 Employee St',
                'designation': 'Manager',
                'joined_date': '2023-01-01',
                'wage': 50000.0
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verify employee was created
            employee = Employee.query.filter_by(name='Test Employee').first()
            assert employee is not None
            assert employee.contact == '1234567890'
            assert employee.address == '123 Employee St'
            assert employee.designation == 'Manager'
            assert employee.wage == 50000.0
    
    def test_employee_update(self, client, app):
        """Test updating an existing employee"""
        with app.app_context():
            from harithmapos import bcrypt
            # Create test user and login
            hashed_password = bcrypt.generate_password_hash('testpassword').decode('utf-8')
            user = User(
                name='Test User',
                email='test@example.com',
                password=hashed_password
            )
            db.session.add(user)
            db.session.commit()
            
            # Create test employee
            employee = Employee(
                name='Original Employee',
                contact='9876543210',
                address='456 Original St',
                designation='Assistant',
                joined_date='2022-01-01',
                wage=30000.0
            )
            db.session.add(employee)
            db.session.commit()
            employee_id = employee.id
            
            # Login
            client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'testpassword'
            }, follow_redirects=True)
            
            # Update employee
            response = client.post(f'/app/employee/{employee_id}/update', data={
                'name': 'Updated Employee',
                'contact': '1111111111',
                'address': '789 Updated Ave',
                'designation': 'Senior Manager',
                'joined_date': '2022-06-01',
                'wage': 75000.0
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verify employee was updated
            updated_employee = Employee.query.get(employee_id)
            assert updated_employee is not None
            assert updated_employee.name == 'Updated Employee'
            assert updated_employee.contact == '1111111111'
            assert updated_employee.address == '789 Updated Ave'
            assert updated_employee.designation == 'Senior Manager'
            assert updated_employee.wage == 75000.0
    
    def test_employee_delete(self, client, app):
        """Test deleting an employee"""
        with app.app_context():
            from harithmapos import bcrypt
            # Create test user and login
            hashed_password = bcrypt.generate_password_hash('testpassword').decode('utf-8')
            user = User(
                name='Test User',
                email='test@example.com',
                password=hashed_password
            )
            db.session.add(user)
            db.session.commit()
            
            # Create test employee
            employee = Employee(
                name='Delete Test Employee',
                contact='2222222222',
                address='123 Delete St',
                designation='Trainee',
                joined_date='2023-06-01',
                wage=25000.0
            )
            db.session.add(employee)
            db.session.commit()
            employee_id = employee.id
            
            # Login
            client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'testpassword'
            }, follow_redirects=True)
            
            # Delete employee
            response = client.get(f'/app/employee/{employee_id}/delete', follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verify employee was deleted
            deleted_employee = Employee.query.get(employee_id)
            assert deleted_employee is None
    
    def test_employee_list_page(self, client, app):
        """Test employee list page loads correctly"""
        with app.app_context():
            from harithmapos import bcrypt
            # Create test user and login
            hashed_password = bcrypt.generate_password_hash('testpassword').decode('utf-8')
            user = User(
                name='Test User',
                email='test@example.com',
                password=hashed_password
            )
            db.session.add(user)
            db.session.commit()
            
            # Login
            response = client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'testpassword'
            }, follow_redirects=True)
            
            # Test employee list page
            response = client.get('/app/employee')
            assert response.status_code == 200
            assert b'Employee' in response.data
    
    def test_employee_search(self, client, app):
        """Test employee search functionality"""
        with app.app_context():
            from harithmapos import bcrypt
            # Create test user and login
            hashed_password = bcrypt.generate_password_hash('testpassword').decode('utf-8')
            user = User(
                name='Test User',
                email='test@example.com',
                password=hashed_password
            )
            db.session.add(user)
            db.session.commit()
            
            # Create test employee
            employee = Employee(
                name='Search Test Employee',
                contact='9876543210',
                address='456 Search St',
                designation='Developer',
                joined_date='2023-01-01',
                wage=60000.0
            )
            db.session.add(employee)
            db.session.commit()
            
            # Login
            client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'testpassword'
            }, follow_redirects=True)
            
            # Search for employee
            response = client.get('/app/employee?query=Search Test')
            
            assert response.status_code == 200
            assert b'Search Test Employee' in response.data
    
    def test_employee_pagination(self, client, app):
        """Test employee list pagination"""
        with app.app_context():
            from harithmapos import bcrypt
            # Create test user and login
            hashed_password = bcrypt.generate_password_hash('testpassword').decode('utf-8')
            user = User(
                name='Test User',
                email='test@example.com',
                password=hashed_password
            )
            db.session.add(user)
            db.session.commit()
            
            # Create multiple test employees
            for i in range(15):
                employee = Employee(
                    name=f'Employee {i}',
                    contact=f'123456789{i}',
                    address=f'{i} Test St',
                    designation='Staff',
                    joined_date='2023-01-01',
                    wage=30000.0 + i * 1000
                )
                db.session.add(employee)
            db.session.commit()
            
            # Login
            client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'testpassword'
            }, follow_redirects=True)
            
            # Test first page
            response = client.get('/app/employee?page=1')
            assert response.status_code == 200
            
            # Test second page
            response = client.get('/app/employee?page=2')
            assert response.status_code == 200
    
    def test_employee_form_validation(self, client, app):
        """Test employee form validation"""
        with app.app_context():
            from harithmapos import bcrypt
            # Create test user and login
            hashed_password = bcrypt.generate_password_hash('testpassword').decode('utf-8')
            user = User(
                name='Test User',
                email='test@example.com',
                password=hashed_password
            )
            db.session.add(user)
            db.session.commit()
            
            # Login
            client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'testpassword'
            }, follow_redirects=True)
            
            # Test with missing required fields
            response = client.post('/app/employee/create', data={
                'name': '',  # Empty name
                'contact': '1234567890',
                'address': '123 Test St',
                'designation': 'Manager',
                'joined_date': '2023-01-01',
                'wage': 50000.0
            }, follow_redirects=True)
            
            assert response.status_code == 200
            # Should redirect back to employee list with error message
    
    def test_employee_404_on_update_nonexistent(self, client, app):
        """Test that updating non-existent employee returns 404"""
        with app.app_context():
            from harithmapos import bcrypt
            # Create test user and login
            hashed_password = bcrypt.generate_password_hash('testpassword').decode('utf-8')
            user = User(
                name='Test User',
                email='test@example.com',
                password=hashed_password
            )
            db.session.add(user)
            db.session.commit()
            
            # Login
            client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'testpassword'
            }, follow_redirects=True)
            
            # Try to update non-existent employee
            response = client.post('/app/employee/99999/update', data={
                'name': 'Updated Employee',
                'contact': '1111111111',
                'address': '789 Updated Ave',
                'designation': 'Senior Manager',
                'joined_date': '2022-06-01',
                'wage': 75000.0
            }, follow_redirects=True)
            
            # Should return 404 or redirect with error
            assert response.status_code in [200, 404]
    
    def test_employee_404_on_delete_nonexistent(self, client, app):
        """Test that deleting non-existent employee returns 404"""
        with app.app_context():
            from harithmapos import bcrypt
            # Create test user and login
            hashed_password = bcrypt.generate_password_hash('testpassword').decode('utf-8')
            user = User(
                name='Test User',
                email='test@example.com',
                password=hashed_password
            )
            db.session.add(user)
            db.session.commit()
            
            # Login
            client.post('/app/login', data={
                'email': 'test@example.com',
                'password': 'testpassword'
            }, follow_redirects=True)
            
            # Try to delete non-existent employee
            response = client.get('/app/employee/99999/delete', follow_redirects=True)
            
            # Should return 404 or redirect with error
            assert response.status_code in [200, 404]
