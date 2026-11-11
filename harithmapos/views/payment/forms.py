from decimal import Decimal

from flask_wtf import FlaskForm

from wtforms import SubmitField, SelectField
from wtforms.validators import InputRequired, NumberRange

import harithmapos.config as config
from harithmapos.formfields import MAX_AMOUNT, NumberBox, id_field, text_field

LINK_FIELDS = ['invoice_id', 'item_invoice_id', 'purchase_order_id', 'customer_id', 'employee_id']


class PaymentCreateForm(FlaskForm):
    invoice_id = id_field("Service invoice", required=False)
    item_invoice_id = id_field("Item invoice", required=False)
    purchase_order_id = id_field("Purchase order", required=False)
    customer_id = id_field("Customer", required=False)
    employee_id = id_field("Employee", required=False)
    payment_method = SelectField("Payment method", choices=config.PAYMENT_METHOD_FORM_LIST)
    payment_direction = SelectField("Direction", choices=config.PAYMENT_DIRECTION_FORM_LIST)
    payment_type = SelectField("Type", choices=config.PAYMENT_TYPE_FORM_LIST)
    payment_amount = NumberBox("Amount", places=2, validators=[
        InputRequired(message='Enter the amount.'),
        NumberRange(min=Decimal('0.01'), max=MAX_AMOUNT, message='Enter an amount above 0.'),
    ])
    remarks = text_field("Remarks", max_length=255)
    submit = SubmitField('Record payment')

    def validate(self, extra_validators=None):
        """Every payment must say what it was for: a linked record or a note."""
        valid = super().validate(extra_validators=extra_validators)
        linked = any(getattr(self, name).data is not None for name in LINK_FIELDS)
        if not linked and not self.remarks.data:
            self.remarks.errors = list(self.remarks.errors) + [
                'Link the payment to an invoice, purchase order, customer or employee, '
                'or write what it was for.'
            ]
            return False
        return valid


class PaymentUpdateForm(PaymentCreateForm):
    submit = SubmitField('Save payment')
