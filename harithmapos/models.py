from harithmapos import db, login_manager, config
from datetime import datetime
from flask_login import UserMixin
from flask import current_app
from sqlalchemy.ext.hybrid import hybrid_property
from itsdangerous import URLSafeTimedSerializer as Serializer

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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

class ItemInvoiceDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_invoice_head_id = db.Column(db.Integer, db.ForeignKey('item_invoice_head.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Numeric(10,4), nullable=False)
    total_cost = db.Column(db.Numeric(10,2), nullable=False)
    total_price = db.Column(db.Numeric(10,2), nullable=False)
    discount_amount = db.Column(db.Numeric(10,2), nullable=False, default=0)
    gross_price = db.Column(db.Numeric(10,2), nullable=False)
    created_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class InvoiceHead(db.Model):
    id =  db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    vehical_id = db.Column(db.Integer, db.ForeignKey('vehical.id'), nullable=False)
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

    def get_customer_view_token(self, expire_seconds = 1800):
        serializer = Serializer(current_app.config['SECRET_KEY'])
        return serializer.dumps({'invoice_id': self.id})
    
    @staticmethod
    def verify_customer_view_token(token):
        serializer = Serializer(current_app.config['SECRET_KEY'])
        try:
            invoice_id = serializer.loads(token)['invoice_id']
        except:
            return None
        return InvoiceHead.query.get(invoice_id)

    @hybrid_property
    def service_status_str(self):
        return config.SERVICE_STATUS_LIST[int(self.service_status)]
    
    @hybrid_property
    def is_in_bay(self):
        return self.service_status in [1, 2, 3]    
        
    @is_in_bay.expression
    def is_in_bay(cls):
        return cls.service_status.in_([1, 2, 3])


class InvoiceDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_head_id = db.Column(db.Integer, db.ForeignKey('invoice_head.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Numeric(10,4), nullable=False)
    total_cost = db.Column(db.Numeric(10,2), nullable=False)
    total_price = db.Column(db.Numeric(10,2), nullable=False)
    discount_amount = db.Column(db.Numeric(10,2), nullable=False, default=0)
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
    wage = db.Column(db.Numeric(10,2))
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
    create_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def get_reset_token(self, expire_seconds = 1800):
        serializer = Serializer(current_app.config['SECRET_KEY'])
        return serializer.dumps({'user_id': self.id})
    
    @staticmethod
    def verify_reset_token(token):
        serializer = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = serializer.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

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
    vehicals = db.relationship('Vehical', backref='owner', lazy=True)
    invoices = db.relationship('InvoiceHead', backref='customer', lazy=True)
    item_invoices = db.relationship('ItemInvoiceHead', backref='customer', lazy=True)
    payments = db.relationship('Payment', backref='customer', lazy=True)

    def __repr__(self):
        return f"Customer('{self.name}','{self.contact}')"

class Vehical(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(8), nullable=False)
    make = db.Column(db.String(20))
    model = db.Column(db.String(20))
    year = db.Column(db.String(4))
    create_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    invoices = db.relationship('InvoiceHead', backref='vehical', lazy=True)

    def __repr__(self):
        return f"Vehical('{self.number}','{self.make}','{self.model}','{self.year}')"