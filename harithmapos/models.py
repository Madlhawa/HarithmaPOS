from harithmapos import db, login_manager, config
from datetime import datetime
from decimal import Decimal
from flask_login import UserMixin
from flask import current_app
from sqlalchemy.ext.hybrid import hybrid_property
from itsdangerous import URLSafeTimedSerializer as Serializer

@login_manager.user_loader
def load_user(user_id):
    try:
        user = db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
    # A switched-off account is signed out on its next page load.
    if user is None or not user.is_active:
        return None
    return user


def _balance(document):
    """What is still owed on an invoice or purchase order (negative = change due)."""
    return (document.gross_price or Decimal('0')) - (document.paid_amount or Decimal('0'))

class InvoiceStatusLog(db.Model):
    __tablename__ = 'invoice_status_log'
    id = db.Column(db.Integer, primary_key=True)
    previous_invoice_status_log_id = db.Column(db.Integer, db.ForeignKey('invoice_status_log.id'))
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice_head.id'))
    service_status = db.Column(db.Integer)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    created_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    previous_invoice_status = db.relationship('InvoiceStatusLog', remote_side=[id], backref='next_invoice_status')

class Payment(db.Model):
    id =  db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice_head.id'))
    item_invoice_id = db.Column(db.Integer, db.ForeignKey('item_invoice_head.id'))
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_order_head.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    payment_method = db.Column(db.String(10))
    payment_direction = db.Column(db.String(10))
    payment_amount = db.Column(db.Numeric(10,2), default=0)
    payment_type = db.Column(db.String(10))
    remarks = db.Column(db.String(255))
    created_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class PurchaseOrderHead(db.Model):
    id =  db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    supplier_invoice_id = db.Column(db.String(255))
    total_price = db.Column(db.Numeric(10,2), default=0)
    discount_pct = db.Column(db.Numeric(10,2), default=0)
    gross_price = db.Column(db.Numeric(10,2), default=0)
    payment_method = db.Column(db.String(10))
    paid_amount = db.Column(db.Numeric(10,2), default=0)
    remaining_amount = db.Column(db.Numeric(10,2))
    last_payment_date = db.Column(db.Date())
    created_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    purchase_order_details = db.relationship('PurchaseOrderDetail', backref='purchase_order', lazy=True)
    payments = db.relationship('Payment', backref='purchase_order', lazy=True)

    @property
    def balance(self):
        return _balance(self)

class PurchaseOrderDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    purchase_order_head_id = db.Column(db.Integer, db.ForeignKey('purchase_order_head.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Numeric(10,4), nullable=False)
    total_cost = db.Column(db.Numeric(10,2), nullable=False)
    total_price = db.Column(db.Numeric(10,2), nullable=False)
    discount_pct = db.Column(db.Numeric(10,2), nullable=False)
    created_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class WashBay(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    remarks = db.Column(db.String(255))
    capacity = db.Column(db.Numeric(10,2))
    create_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    invoices = db.relationship('InvoiceHead', backref='washbay', lazy=True)

    @hybrid_property
    def active_invoice(self):
        active_invoice_head = InvoiceHead.query.filter(InvoiceHead.is_in_bay).filter(InvoiceHead.washbay_id==self.id).first()
        return active_invoice_head

class ItemInvoiceHead(db.Model):
    id =  db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    discount_amount = db.Column(db.Numeric(10,2), default=0)
    total_cost = db.Column(db.Numeric(10,2), default=0)
    total_price = db.Column(db.Numeric(10,2), default=0)
    total_discount = db.Column(db.Numeric(10,2), default=0)
    gross_price = db.Column(db.Numeric(10,2), default=0)
    payment_method = db.Column(db.String(10))
    paid_amount = db.Column(db.Numeric(10,2), default=0)
    remaining_amount = db.Column(db.Numeric(10,2))
    last_payment_date = db.Column(db.Date())
    created_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    invoice_details = db.relationship('ItemInvoiceDetail', backref='item_invoice', lazy=True)
    payments = db.relationship('Payment', backref='item_invoice', lazy=True)

    @property
    def balance(self):
        return _balance(self)

class ItemInvoiceDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_invoice_head_id = db.Column(db.Integer, db.ForeignKey('item_invoice_head.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Numeric(10,4), nullable=False)
    total_cost = db.Column(db.Numeric(10,2), nullable=False)
    total_price = db.Column(db.Numeric(10,2), nullable=False)
    discount_amount = db.Column(db.Numeric(10,2), nullable=False, default=0)  # Total discount (auto + additional)
    additional_discount = db.Column(db.Numeric(10,2), nullable=False, default=0)  # Manual additional discount
    gross_price = db.Column(db.Numeric(10,2), nullable=False)
    created_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class InvoiceHead(db.Model):
    id =  db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    washbay_id = db.Column(db.Integer, db.ForeignKey('wash_bay.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    current_milage = db.Column(db.Numeric(18,0))
    next_milage_in = db.Column(db.Numeric(18,0))
    next_milage = db.Column(db.Numeric(18,0))
    service_status = db.Column(db.Integer, default=0)
    service_start_msg_sent_ind = db.Column(db.Boolean, default=False, nullable=False)
    service_complete_msg_sent_ind = db.Column(db.Boolean, default=False, nullable=False)
    discount_amount = db.Column(db.Numeric(10,2), default=0)
    total_cost = db.Column(db.Numeric(10,2), default=0)
    total_price = db.Column(db.Numeric(10,2), default=0)
    total_discount = db.Column(db.Numeric(10,2), default=0)
    gross_price = db.Column(db.Numeric(10,2), default=0)
    payment_method = db.Column(db.String(10))
    paid_amount = db.Column(db.Numeric(10,2), default=0)
    remaining_amount = db.Column(db.Numeric(10,2))
    last_payment_date = db.Column(db.Date())
    created_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    invoice_details = db.relationship('InvoiceDetail', backref='invoice', lazy=True)
    payments = db.relationship('Payment', backref='invoice', lazy=True)
    invoice_statuses = db.relationship('InvoiceStatusLog', backref='invoice', lazy=True)

    def get_customer_view_token(self):
        serializer = Serializer(current_app.config['SECRET_KEY'])
        return serializer.dumps({'invoice_id': self.id})
    
    @staticmethod
    def verify_customer_view_token(token, expire_seconds=None):
        if expire_seconds is None:
            from harithmapos import settings as app_settings
            expire_seconds = app_settings.customer_link_max_age_seconds()
        serializer = Serializer(current_app.config['SECRET_KEY'])
        try:
            invoice_id = serializer.loads(token, max_age=expire_seconds)['invoice_id']
        except Exception:
            return None
        return db.session.get(InvoiceHead, invoice_id)

    @property
    def balance(self):
        return _balance(self)

    @property
    def is_done(self):
        return self.service_status == config.SERVICE_STATUS_DONE

    @hybrid_property
    def service_status_str(self):
        try:
            return config.SERVICE_STATUS_LIST[int(self.service_status)]
        except (IndexError, ValueError, TypeError):
            return f"Unknown Status ({self.service_status})"
    
    @hybrid_property
    def is_in_bay(self):
        return self.service_status in [1, 2]    
    
    @is_in_bay.expression
    def is_in_bay(cls):
        return cls.service_status.in_([1, 2])


class InvoiceDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_head_id = db.Column(db.Integer, db.ForeignKey('invoice_head.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Numeric(10,4), nullable=False)
    total_cost = db.Column(db.Numeric(10,2), nullable=False)
    total_price = db.Column(db.Numeric(10,2), nullable=False)
    discount_amount = db.Column(db.Numeric(10,2), nullable=False, default=0)  # Total discount (auto + additional)
    additional_discount = db.Column(db.Numeric(10,2), nullable=False, default=0)  # Manual additional discount
    gross_price = db.Column(db.Numeric(10,2), nullable=False)
    created_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(10))
    address = db.Column(db.String(255))
    designation = db.Column(db.String(40))
    joined_date = db.Column(db.Date())
    wage = db.Column(db.Numeric(10,2))  # monthly salary, or the day rate for daily-paid staff
    pay_type = db.Column(db.String(10), nullable=False, default=config.PAY_MONTHLY)
    epf_enabled = db.Column(db.Boolean, nullable=False, default=True)
    epf_number = db.Column(db.String(20))
    active = db.Column(db.Boolean, nullable=False, default=True)
    create_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    invoices = db.relationship('InvoiceHead', backref='employee', lazy=True)
    payments = db.relationship('Payment', backref='employee', lazy=True)
    invoice_statuses = db.relationship('InvoiceStatusLog', backref='employee', lazy=True)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    unit_of_measure = db.Column(db.String(20))
    quantity = db.Column(db.Numeric(10,4))
    unit_cost = db.Column(db.Numeric(10,2))
    unit_price = db.Column(db.Numeric(10,2))
    discount_pct = db.Column(db.Numeric(5,2))
    create_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    invoice_details = db.relationship('InvoiceDetail', backref='item', lazy=True)
    item_invoice_details = db.relationship('ItemInvoiceDetail', backref='item', lazy=True)
    purchase_order_details = db.relationship('PurchaseOrderDetail', backref='item', lazy=True)

    @property
    def tracks_stock(self):
        """Items with no quantity are services or labour: sold without touching stock."""
        return self.quantity is not None

    @property
    def is_low_stock(self):
        from harithmapos import settings as app_settings
        return self.quantity is not None and self.quantity <= app_settings.low_stock_threshold()

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(10))
    address = db.Column(db.String(255))
    create_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    purchse_orders = db.relationship('PurchaseOrderHead', backref='supplier', lazy=True)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(20), default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    ui_theme = db.Column(db.String(5), default='light')
    role = db.Column(db.String(10), nullable=False, default=config.ROLE_STAFF)
    active = db.Column(db.Boolean, nullable=False, default=True)
    last_seen_dttm = db.Column(db.DateTime)      # UTC; updated at most once a minute
    create_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def is_owner(self):
        return self.role == config.ROLE_OWNER

    @property
    def is_active(self):
        # Flask-Login refuses to sign in a user whose is_active is False.
        return bool(self.active)

    @property
    def role_label(self):
        return dict(config.ROLE_FORM_LIST).get(self.role, self.role)

    RESET_TOKEN_SALT = 'password-reset'
    RESET_TOKEN_MAX_AGE_SECONDS = 1800

    def get_reset_token(self):
        serializer = Serializer(current_app.config['SECRET_KEY'], salt=self.RESET_TOKEN_SALT)
        return serializer.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token, max_age=None):
        if max_age is None:
            max_age = User.RESET_TOKEN_MAX_AGE_SECONDS
        serializer = Serializer(current_app.config['SECRET_KEY'], salt=User.RESET_TOKEN_SALT)
        try:
            user_id = serializer.loads(token, max_age=max_age)['user_id']
        except Exception:
            return None
        return db.session.get(User, user_id)

    def __repr__(self):
        return f"User('{self.name}','{self.email}')"

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(10))
    address = db.Column(db.String(255))
    email = db.Column(db.String(150))
    create_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    vehicles = db.relationship('Vehicle', backref='owner', lazy=True)
    invoices = db.relationship('InvoiceHead', backref='customer', lazy=True)
    item_invoices = db.relationship('ItemInvoiceHead', backref='customer', lazy=True)
    payments = db.relationship('Payment', backref='customer', lazy=True)

    def __repr__(self):
        return f"Customer('{self.name}','{self.contact}')"

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(8), nullable=False)
    make = db.Column(db.String(20))
    model = db.Column(db.String(20))
    year = db.Column(db.String(4))
    create_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    invoices = db.relationship('InvoiceHead', backref='vehicle', lazy=True)

    def __repr__(self):
        return f"Vehicle('{self.number}','{self.make}','{self.model}','{self.year}')"

class Setting(db.Model):
    """One value from the Settings page. See harithmapos/settings.py for the list."""
    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))


# ---------------------------------------------------------------------------
# Attendance, leave, advances and payroll
# ---------------------------------------------------------------------------

class AttendanceDay(db.Model):
    """One employee's day in the register. A day with no row is "not marked"."""
    __tablename__ = 'attendance_day'
    __table_args__ = (db.UniqueConstraint('employee_id', 'work_date', name='uq_attendance_employee_date'),)
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False, index=True)
    work_date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(10), nullable=False)        # config.ATTENDANCE_STATUSES
    leave_type = db.Column(db.String(10))                    # config.LEAVE_TYPES, for leave and half days
    time_in = db.Column(db.Time)
    time_out = db.Column(db.Time)
    late_minutes = db.Column(db.Integer, nullable=False, default=0)
    early_minutes = db.Column(db.Integer, nullable=False, default=0)
    overtime_minutes = db.Column(db.Integer, nullable=False, default=0)
    note = db.Column(db.String(255))
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    create_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    employee = db.relationship('Employee', backref=db.backref('attendance_days', lazy='dynamic'))


class ShortLeave(db.Model):
    """Time away during a working day (left for an hour and came back)."""
    __tablename__ = 'short_leave'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False, index=True)
    work_date = db.Column(db.Date, nullable=False, index=True)
    time_from = db.Column(db.Time, nullable=False)
    time_to = db.Column(db.Time, nullable=False)
    minutes = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255))
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    create_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    employee = db.relationship('Employee', backref=db.backref('short_leaves', lazy='dynamic'))


class PayrollRun(db.Model):
    """One month's payroll. Draft until finalised; finalised payslips are frozen."""
    __tablename__ = 'payroll_run'
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.Date, nullable=False, unique=True)  # the first day of the month
    status = db.Column(db.String(10), nullable=False, default='final')
    finalised_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    create_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    payslips = db.relationship('Payslip', backref='run', lazy=True, cascade='all, delete-orphan')


class Payslip(db.Model):
    __tablename__ = 'payslip'
    __table_args__ = (db.UniqueConstraint('payroll_run_id', 'employee_id', name='uq_payslip_run_employee'),)
    id = db.Column(db.Integer, primary_key=True)
    payroll_run_id = db.Column(db.Integer, db.ForeignKey('payroll_run.id'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False, index=True)
    pay_type = db.Column(db.String(10), nullable=False)
    rate = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    days_in_month = db.Column(db.Integer, nullable=False, default=0)
    days_present = db.Column(db.Numeric(5, 1), nullable=False, default=0)
    paid_leave_days = db.Column(db.Numeric(5, 1), nullable=False, default=0)
    nopay_days = db.Column(db.Numeric(5, 1), nullable=False, default=0)
    unmarked_days = db.Column(db.Integer, nullable=False, default=0)
    late_count = db.Column(db.Integer, nullable=False, default=0)
    late_minutes = db.Column(db.Integer, nullable=False, default=0)
    short_leave_count = db.Column(db.Integer, nullable=False, default=0)
    short_leave_minutes = db.Column(db.Integer, nullable=False, default=0)
    overtime_minutes = db.Column(db.Integer, nullable=False, default=0)
    basic_pay = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    nopay_deduction = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    overtime_pay = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    allowances = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    gross_pay = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    epf_employee = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    advances = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    other_deductions = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    net_pay = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    epf_employer = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    etf_employer = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    note = db.Column(db.String(255))
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'))
    employee = db.relationship('Employee', backref=db.backref('payslips', lazy='dynamic'))
    payment = db.relationship('Payment', foreign_keys=[payment_id])

    @property
    def is_paid(self):
        return self.payment_id is not None


class SalaryAdvance(db.Model):
    """Money paid to an employee ahead of payday, taken back on a payslip."""
    __tablename__ = 'salary_advance'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False, index=True)
    advance_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    note = db.Column(db.String(255))
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'))
    payslip_id = db.Column(db.Integer, db.ForeignKey('payslip.id'))  # set when it is taken back
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    create_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    employee = db.relationship('Employee', backref=db.backref('advances', lazy='dynamic'))
    payment = db.relationship('Payment', foreign_keys=[payment_id])
    payslip = db.relationship('Payslip', backref='advance_items', foreign_keys=[payslip_id])

    @property
    def is_recovered(self):
        return self.payslip_id is not None


class LoginEvent(db.Model):
    """Every sign-in attempt and sign-out, for the developer page."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    email = db.Column(db.String(120))            # as typed, so failed attempts on unknown emails show too
    outcome = db.Column(db.String(20), nullable=False)   # ok, bad_password, unknown_email, switched_off, logout
    ip = db.Column(db.String(45))
    user_agent = db.Column(db.String(200))
    created_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    user = db.relationship('User')


class UserActivityDay(db.Model):
    """One row per user per (local) day they used the app: unique users per day."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    day = db.Column(db.Date, nullable=False, index=True)
    requests = db.Column(db.Integer, nullable=False, default=1)
    __table_args__ = (db.UniqueConstraint('user_id', 'day', name='uq_user_activity_day'),)
