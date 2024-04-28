from harithmapos import db, login_manager
from datetime import datetime
from flask_login import UserMixin
from flask import current_app
from itsdangerous import URLSafeTimedSerializer as Serializer

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class WashBay(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    remarks = db.Column(db.String(255))
    capacity = db.Column(db.Numeric(10,2))
    create_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    invoices = db.relationship('InvoiceHead', backref='washbay', lazy=True)

class InvoiceHead(db.Model):
    id =  db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    vehical_id = db.Column(db.Integer, db.ForeignKey('vehical.id'), nullable=False)
    washbay_id = db.Column(db.Integer, db.ForeignKey('wash_bay.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    current_milage = db.Column(db.Numeric(18,0), nullable=False)
    next_milage = db.Column(db.Numeric(18,0), nullable=False)
    service_status = db.Column(db.String(10))
    total_cost = db.Column(db.Numeric(10,2))
    total_price = db.Column(db.Numeric(10,2))
    discount_pct = db.Column(db.Numeric(10,2))
    gross_price = db.Column(db.Numeric(10,2))
    payment_method = db.Column(db.String(10))
    paid_amount = db.Column(db.Numeric(10,2))
    remaining_amount = db.Column(db.Numeric(10,2))
    last_payment_date = db.Column(db.Date())
    created_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    invoice_details = db.relationship('InvoiceDetail', backref='invoice', lazy=True)

class InvoiceDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_head_id = db.Column(db.Integer, db.ForeignKey('invoice_head.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_cost = db.Column(db.Numeric(10,2), nullable=False)
    total_price = db.Column(db.Numeric(10,2), nullable=False)
    discount_pct = db.Column(db.Numeric(10,2), nullable=False)
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

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    unit_of_measure = db.Column(db.String(20))
    quantity = db.Column(db.Integer)
    unit_cost = db.Column(db.Numeric(10,2))
    unit_price = db.Column(db.Numeric(10,2))
    discount_pct = db.Column(db.Numeric(5,2))
    create_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    invoice_details = db.relationship('InvoiceDetail', backref='item', lazy=True)

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(10))
    address = db.Column(db.String(255))
    create_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_dttm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(20), default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
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