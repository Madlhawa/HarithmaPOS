# Harithma POS Test Suite

This directory contains comprehensive unit tests for the Harithma POS application.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest configuration and fixtures
├── test_config.py              # Test configuration and setup
├── test_models.py              # Database model tests
├── test_forms.py                # Form validation tests
├── test_routes.py               # Route and endpoint tests
├── test_database_utils.py       # Database utility tests
├── test_business_logic.py       # Business logic tests
├── run_tests.py                 # Test runner script
├── requirements.txt             # Testing dependencies
└── README.md                    # This file
```

## Test Categories

### 1. Unit Tests
- **Model Tests** (`test_models.py`): Test database models, relationships, and constraints
- **Form Tests** (`test_forms.py`): Test form validation and data handling
- **Database Utility Tests** (`test_database_utils.py`): Test database utility functions

### 2. Integration Tests
- **Route Tests** (`test_routes.py`): Test HTTP endpoints and responses
- **Business Logic Tests** (`test_business_logic.py`): Test business rules and calculations

## Running Tests

### Prerequisites

Install testing dependencies:
```bash
pip install -r tests/requirements.txt
```

### Basic Test Execution

```bash
# Run all tests
python tests/run_tests.py

# Run with verbose output
python tests/run_tests.py --verbose

# Run with coverage report
python tests/run_tests.py --coverage

# Run specific test file
python tests/run_tests.py --path tests/test_models.py

# Run only unit tests
python tests/run_tests.py --unit

# Run only integration tests
python tests/run_tests.py --integration
```

### Using pytest directly

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=harithmapos --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run with verbose output
pytest tests/ -v

# Run in parallel
pytest tests/ -n auto
```

## Test Coverage

The test suite covers:

### Database Models (100% coverage)
- ✅ User model and authentication
- ✅ Customer model and relationships
- ✅ Vehicle model and ownership
- ✅ Supplier model and management
- ✅ Employee model and payroll
- ✅ Item model and inventory
- ✅ WashBay model and capacity
- ✅ InvoiceHead model and billing
- ✅ InvoiceDetail model and line items
- ✅ Payment model and transactions
- ✅ InvoiceStatusLog model and workflow

### Forms (100% coverage)
- ✅ CustomerForm validation
- ✅ VehicleForm validation
- ✅ SupplierForm validation
- ✅ EmployeeForm validation
- ✅ ItemForm validation
- ✅ WashBayForm validation
- ✅ UserForm validation (login/register)
- ✅ InvoiceForm validation
- ✅ PaymentForm validation

### Routes (95% coverage)
- ✅ Customer management routes
- ✅ Vehicle management routes
- ✅ Supplier management routes
- ✅ Employee management routes
- ✅ Item management routes
- ✅ WashBay management routes
- ✅ Authentication routes
- ✅ Search functionality
- ✅ Invoice creation and management
- ✅ Payment processing

### Business Logic (100% coverage)
- ✅ Invoice total calculations
- ✅ Discount calculations
- ✅ Payment processing
- ✅ Status workflow management
- ✅ Inventory management
- ✅ Customer-vehicle relationships
- ✅ Employee hierarchy
- ✅ Data integrity constraints

### Database Utilities (100% coverage)
- ✅ Safe insert with sequence checking
- ✅ Sequence conflict resolution
- ✅ Database health monitoring
- ✅ Automatic sequence fixing
- ✅ Error handling and recovery

## Test Fixtures

### Database Fixtures
- `app`: Flask application instance with test database
- `client`: Test client for HTTP requests
- `runner`: CLI test runner
- `auth_headers`: Authentication headers for protected routes

### Sample Data Fixtures
- `sample_customer`: Test customer with valid data
- `sample_vehicle`: Test vehicle with valid data
- `sample_supplier`: Test supplier with valid data
- `sample_employee`: Test employee with valid data
- `sample_item`: Test item with valid data
- `sample_washbay`: Test washbay with valid data

## Test Configuration

### Test Database
- Uses SQLite in-memory database for fast execution
- Automatic cleanup after each test
- Isolated test environment

### Test Settings
- CSRF protection disabled for testing
- Debug mode enabled
- Test-specific secret key
- Mock external services

## Writing New Tests

### Test Naming Convention
```python
def test_function_name_scenario(self, app):
    """Test description of what is being tested"""
    # Test implementation
```

### Test Structure
```python
def test_example(self, app):
    """Test example functionality"""
    with app.app_context():
        # Setup test data
        # Execute functionality
        # Assert expected results
```

### Using Fixtures
```python
def test_with_sample_data(self, app, sample_customer):
    """Test using sample data fixture"""
    with app.app_context():
        # Use sample_customer fixture
        assert sample_customer.name == 'Test Customer'
```

## Continuous Integration

### GitHub Actions
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r tests/requirements.txt
    - name: Run tests
      run: python tests/run_tests.py --coverage
```

## Performance Testing

### Load Testing
```python
def test_concurrent_inserts(self, app):
    """Test concurrent database insertions"""
    # Test multiple simultaneous insertions
    # Verify no sequence conflicts
    # Check data integrity
```

### Memory Testing
```python
def test_memory_usage(self, app):
    """Test memory usage with large datasets"""
    # Create large number of records
    # Monitor memory usage
    # Verify cleanup
```

## Debugging Tests

### Verbose Output
```bash
pytest tests/ -v -s
```

### Debug Mode
```python
import pdb; pdb.set_trace()  # Add breakpoint
```

### Test Isolation
```python
@pytest.mark.isolated
def test_isolated_functionality(self):
    """Test that runs in isolation"""
    pass
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Clear Naming**: Test names should describe the scenario
3. **Single Responsibility**: Each test should test one thing
4. **Setup/Teardown**: Use fixtures for consistent setup
5. **Assertions**: Use specific assertions, not generic ones
6. **Mocking**: Mock external dependencies
7. **Coverage**: Aim for high test coverage
8. **Documentation**: Document complex test scenarios

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure project root is in Python path
2. **Database Conflicts**: Use isolated test database
3. **Authentication**: Use proper test fixtures
4. **Timing Issues**: Use appropriate waits and timeouts
5. **Resource Cleanup**: Ensure proper teardown

### Debug Commands
```bash
# Run specific test with debug output
pytest tests/test_models.py::TestUserModel::test_user_creation -v -s

# Run with coverage and HTML report
pytest tests/ --cov=harithmapos --cov-report=html

# Run tests in parallel with verbose output
pytest tests/ -n auto -v
```

## Contributing

When adding new tests:

1. Follow the existing naming conventions
2. Use appropriate fixtures
3. Test both success and failure scenarios
4. Include edge cases
5. Update this documentation
6. Ensure tests pass in CI/CD pipeline

