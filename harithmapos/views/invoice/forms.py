from flask_wtf import FlaskForm

from wtforms import SubmitField, StringField, SelectField, RadioField
from wtforms.validators import Optional

import harithmapos.config as config
from harithmapos.formfields import id_field, mileage_field, money_field, quantity_field


class InvoiceDetailCreateForm(FlaskForm):
    """One line on a service invoice or an item invoice."""
    item = StringField("Item", validators=[Optional()])
    item_id = id_field("Item")
    quantity = quantity_field("Quantity")
    discount_amount = money_field("Discount")
    submit = SubmitField('Add item')


class InvoiceHeadUpdateForm(FlaskForm):
    employee = StringField("Employee", validators=[Optional()])
    employee_id = id_field("Employee", required=False)
    washbay = StringField("Wash bay", validators=[Optional()])
    washbay_id = id_field("Wash bay", required=False)
    current_milage = mileage_field("Current mileage")
    next_milage_in = mileage_field("Next service in")
    service_status = RadioField("Status", choices=config.SERVICE_STATUS_FORM_LIST, coerce=int)
    discount_amount = money_field("Bill discount")
    payment_method = SelectField("Payment method", choices=config.PAYMENT_METHOD_FORM_LIST)
    paid_amount = money_field("Paid amount")
    update_invoice = SubmitField('Save')
    complete_invoice = SubmitField('Complete')
    cancel_invoice = SubmitField('Cancel invoice')
    send_service_start_msg = SubmitField('Notify started')
    send_service_complete_msg = SubmitField('Notify completed')


class InvoiceHeadCreateForm(FlaskForm):
    vehicle = StringField("Vehicle", validators=[Optional()])
    vehicle_id = id_field("Vehicle")
    employee = StringField("Employee", validators=[Optional()])
    employee_id = id_field("Employee")
    washbay = StringField("Wash bay", validators=[Optional()])
    washbay_id = id_field("Wash bay")
    current_milage = mileage_field("Mileage")
    submit = SubmitField('Create invoice')


class InvoiceStatusForm(FlaskForm):
    """The one-tap status buttons on the dashboard."""
    status = RadioField("Status", choices=config.SERVICE_STATUS_FORM_LIST, coerce=int)


class ItemInvoiceHeadUpdateForm(FlaskForm):
    customer = StringField("Customer", validators=[Optional()])
    customer_id = id_field("Customer", required=False)
    discount_amount = money_field("Bill discount")
    payment_method = SelectField("Payment method", choices=config.PAYMENT_METHOD_FORM_LIST)
    paid_amount = money_field("Paid amount")
    update_item_invoice = SubmitField('Save')
    complete_item_invoice = SubmitField('Complete')


class ItemInvoiceHeadCreateForm(FlaskForm):
    customer = StringField("Customer", validators=[Optional()])
    customer_id = id_field("Customer")
    submit = SubmitField('Create invoice')
