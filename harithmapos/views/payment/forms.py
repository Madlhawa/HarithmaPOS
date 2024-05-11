from flask_wtf import FlaskForm

from wtforms import SubmitField, IntegerField, StringField, DecimalField, SelectField, ValidationError
from wtforms.validators import DataRequired, Optional

import harithmapos.config as config

def at_least_one_of_fields(form, field):
    field_names = ['invoice_id', 'item_invoice_id', 'purchase_order_id', 'customer_id', 'employee_id']
    for field_name in field_names:
        field_value = getattr(form, field_name).data
        if field_value:
            return  # At least one field is filled

    raise ValidationError('At least one of Invoice ID, Purchase Order ID, Customer ID, or Employee ID must be filled.')

class PaymentUpdateForm(FlaskForm): 
    invoice_id = StringField("Service Invoice", validators=[at_least_one_of_fields])
    item_invoice_id = StringField("Item Invoice", validators=[at_least_one_of_fields])
    purchase_order_id = StringField("Purchase Order", validators=[at_least_one_of_fields])
    customer_id = StringField("Customer", validators=[at_least_one_of_fields])
    employee_id = StringField("Employee", validators=[at_least_one_of_fields])
    payment_method = SelectField("Payment Method", choices=config.PAYMENT_METHOD_FORM_LIST)
    payment_direction = SelectField("Payment Direction", choices=config.PAYMENT_DIRECTION_FORM_LIST)
    payment_type = SelectField("Payment Type", choices=config.PAYMENT_TYPE_FORM_LIST)
    payment_amount = DecimalField("Payment Amount", places=2, validators=[Optional()])
    remarks = StringField("Remarks")
    submit = SubmitField('Update Payment')

class PaymentCreateForm(FlaskForm):
    invoice_id = StringField("Service Invoice", validators=[at_least_one_of_fields])
    item_invoice_id = StringField("Item Invoice", validators=[at_least_one_of_fields])
    purchase_order_id = StringField("Purchase Order", validators=[at_least_one_of_fields])
    customer_id = StringField("Customer", validators=[at_least_one_of_fields])
    employee_id = StringField("Employee", validators=[at_least_one_of_fields])
    payment_method = SelectField("Payment Method", choices=config.PAYMENT_METHOD_FORM_LIST)
    payment_direction = SelectField("Payment Direction", choices=config.PAYMENT_DIRECTION_FORM_LIST)
    payment_type = SelectField("Payment Type", choices=config.PAYMENT_TYPE_FORM_LIST)
    payment_amount = DecimalField("Payment Amount", places=2, validators=[Optional()])
    remarks = StringField("Remarks")
    submit = SubmitField('Create Payment')