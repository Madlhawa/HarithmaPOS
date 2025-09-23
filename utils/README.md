# Utilities for Harithma POS

This package contains various utility functions and tools for the Harithma POS application.

## 📁 Structure

```
utils/
├── __init__.py              # Package initialization
├── database.py              # All database utilities and operations
└── README.md               # This documentation
```

## 🔧 Database Utilities (`database.py`)

### `safe_insert_with_sequence_check(model_class, **kwargs)`
**Purpose:** Safely insert a new record with automatic sequence checking and fixing.

**Usage:**
```python
from utils.database import safe_insert_with_sequence_check
from harithmapos.models import Customer

# Safe insertion with automatic sequence fixing
customer = safe_insert_with_sequence_check(
    Customer,
    name="John Doe",
    contact="123456789",
    address="123 Main St",
    email="john@example.com"
)
```

**Features:**
- Automatic sequence conflict detection
- Automatic sequence fixing
- Automatic retry after fixing
- Comprehensive error handling

### `fix_sequence_for_table(table_name)`
**Purpose:** Fix sequence for a specific table.

**Usage:**
```python
from utils.database import fix_sequence_for_table

# Fix customer table sequence
fix_sequence_for_table('customer')
```

### `check_database_health()`
**Purpose:** Check database for common issues and sequence problems.

**Usage:**
```python
from utils.database import check_database_health

# Check database health
check_database_health()
```

### `fix_database_sequences()`
**Purpose:** Fix all database sequences after migrations.

**Usage:**
```python
from utils.database import fix_database_sequences

# Fix all sequences
fix_database_sequences()
```

**Or run as standalone script:**
```bash
# From the project root directory
python utils/database.py
```

**When to use:**
- After running `flask db upgrade`
- When you get "duplicate key value violates unique constraint" errors
- Before deploying to production
- As part of your regular database maintenance

## 🚀 Quick Start

### Fix Current Sequence Issues:
```bash
python utils/database.py
# Then choose option 2
```

### Check Database Health:
```bash
python utils/database.py
# Then choose option 1
```

### Use Safe Insertion in Your Code:
```python
from utils.database import safe_insert_with_sequence_check

# Instead of manual db.session.add() and commit()
customer = safe_insert_with_sequence_check(Customer, **form_data)
```

## 🔄 Integration Examples

### In Flask Routes:
```python
from utils.database import safe_insert_with_sequence_check

@route('/insert_customer/', methods=['POST'])
def insert_customer():
    form = CustomerForm()
    if form.validate_on_submit():
        try:
            customer = safe_insert_with_sequence_check(
                Customer,
                name=form.name.data,
                contact=form.contact.data,
                address=form.address.data,
                email=form.email.data
            )
            flash("Customer added successfully.", category='success')
        except Exception as e:
            flash(f"Customer failed to add: {str(e)}", category='danger')
```

### In Deployment Scripts:
```bash
# After migration
flask db upgrade
python utils/database.py
# Choose option 2 to fix sequences
```

## ⚠️ Important Notes

- **Always backup your database** before running these scripts
- **Test in development** before using in production
- **Run sequence fixer** after every database migration
- **Use safe insertion** for all new record creation

## 📞 Support

If you encounter issues:
1. Check the error messages carefully
2. Ensure your database connection is working
3. Verify you're running from the project root directory
4. Check that all dependencies are installed
