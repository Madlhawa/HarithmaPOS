from flask_wtf import FlaskForm

from wtforms import SubmitField, IntegerField, StringField, DecimalField, SelectField, RadioField, HiddenField
from wtforms.validators import DataRequired, Optional

import harithmapos.config as config

class InvoiceDetailCreateForm(FlaskForm):
    item = StringField("Item", validators=[DataRequired()])
    item_id = HiddenField("Item ID", validators=[DataRequired()])
    quantity = DecimalField("Qty", places=4, validators=[DataRequired()])
    discount_amount = DecimalField("Discount", places=4, validators=[Optional()])
    submit = SubmitField('Add Item')

class InvoiceHeadUpdateForm(FlaskForm):
    employee = StringField("Employee", validators=[DataRequired()])
    employee_id = HiddenField("Employee ID", validators=[Optional()])
    washbay = StringField("Wash Bay", validators=[DataRequired()])
    washbay_id = HiddenField("WashBay ID", validators=[Optional()])
    current_milage = IntegerField("Current Milage", validators=[Optional()])
    next_milage_in = IntegerField("Next Milage In", validators=[Optional()])
    service_status = RadioField("Status", choices=config.SERVICE_STATUS_FORM_LIST)
    total_cost = DecimalField("Total Cost", places=2, validators=[Optional()])
    total_price = DecimalField("Total Price", places=2, validators=[Optional()])
    discount_amount = DecimalField("Discount Amount", places=2, validators=[Optional()])
    gross_price = DecimalField("Gross Price", places=2, validators=[Optional()])
    payment_method = SelectField("Payment Method", choices=config.PAYMENT_METHOD_FORM_LIST)
    paid_amount = DecimalField("Paid Amount", places=2, validators=[Optional()])
    update_invoice = SubmitField('Update')
    complete_invoice = SubmitField('Complete')
    cancel_invoice = SubmitField('Cancel')
    send_service_start_msg = SubmitField('Notify Started')
    send_service_complete_msg = SubmitField('Notify Completed')

class InvoiceHeadCreateForm(FlaskForm):
    vehicle = StringField("Vehicle", validators=[DataRequired()])
    vehicle_id = HiddenField("Vehicle ID", validators=[DataRequired()])
    employee = StringField("Employee", validators=[DataRequired()])
    employee_id = HiddenField("Employee ID", validators=[DataRequired()])
    washbay = StringField("Wash Bay", validators=[DataRequired()])
    washbay_id = HiddenField("WashBay ID", validators=[DataRequired()])
    current_milage = IntegerField("Milage")
    submit = SubmitField('Create Invoice')

class ItemInvoiceHeadUpdateForm(FlaskForm):
    customer = StringField("Customer", validators=[DataRequired()])
    customer_id = HiddenField("Customer ID", validators=[Optional()])
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
    customer_id = HiddenField("Customer ID", validators=[Optional()])
    submit = SubmitField('Create Invoice')