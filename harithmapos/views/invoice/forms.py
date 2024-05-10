from flask_wtf import FlaskForm

from wtforms import SubmitField, IntegerField, StringField, DecimalField, SelectField
from wtforms.validators import DataRequired, Optional

import harithmapos.config as config

class InvoiceDetailCreateForm(FlaskForm):
    item = StringField("Item", validators=[DataRequired()])
    quantity = IntegerField("Qty", validators=[DataRequired()])
    submit = SubmitField('Add Item')

class InvoiceHeadUpdateForm(FlaskForm):
    vehical = StringField("Vehical", validators=[DataRequired()])
    employee = StringField("Employee", validators=[DataRequired()])
    washbay = StringField("Wash Bay", validators=[DataRequired()])
    current_milage = IntegerField("Current Milage", validators=[Optional()])
    next_milage = IntegerField("Next Milage", validators=[Optional()])
    service_status = SelectField("Status", choices=config.SERVICE_STATUS_FORM_LIST)
    total_cost = DecimalField("Total Cost", places=2, validators=[Optional()])
    total_price = DecimalField("Total Price", places=2, validators=[Optional()])
    discount_pct = DecimalField("Discount Percentage", places=2, validators=[Optional()])
    gross_price = DecimalField("Gross Price", places=2, validators=[Optional()])
    payment_method = SelectField("Payment Method", choices=config.PAYMENT_METHOD_FORM_LIST)
    paid_amount = DecimalField("Paid Amount", places=2, validators=[Optional()])
    update_invoice = SubmitField('Update Invoice')
    complete_invoice = SubmitField('Complete Invoice')

class InvoiceHeadCreateForm(FlaskForm):
    vehical = StringField("Vehical", validators=[DataRequired()])
    employee = StringField("Employee", validators=[DataRequired()])
    washbay = StringField("Wash Bay", validators=[DataRequired()])
    current_milage = IntegerField("Milage")
    submit = SubmitField('Create Invoice')

class ItemInvoiceHeadUpdateForm(FlaskForm):
    customer = StringField("Customer", validators=[DataRequired()])
    total_cost = DecimalField("Total Cost", places=2, validators=[Optional()])
    total_price = DecimalField("Total Price", places=2, validators=[Optional()])
    discount_pct = DecimalField("Discount Percentage", places=2, validators=[Optional()])
    gross_price = DecimalField("Gross Price", places=2, validators=[Optional()])
    payment_method = SelectField("Payment Method", choices=config.PAYMENT_METHOD_FORM_LIST)
    paid_amount = DecimalField("Paid Amount", places=2, validators=[Optional()])
    update_item_invoice = SubmitField('Update Invoice')
    complete_item_invoice = SubmitField('Complete Invoice')

class ItemInvoiceHeadCreateForm(FlaskForm):
    customer = StringField("Customer", validators=[DataRequired()])
    submit = SubmitField('Create Invoice')