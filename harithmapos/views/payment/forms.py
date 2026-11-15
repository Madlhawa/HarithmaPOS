from decimal import Decimal

from flask_wtf import FlaskForm

from wtforms import SubmitField, SelectField
from wtforms.validators import InputRequired, NumberRange

import harithmapos.config as config
from harithmapos.formfields import MAX_AMOUNT, NumberBox, text_field

TYPE_LABELS = dict(config.PAYMENT_TYPE_FORM_LIST)


def _amount_field(label="Amount"):
    return NumberBox(label, places=2, validators=[
        InputRequired(message='Enter the amount.'),
        NumberRange(min=Decimal('0.01'), max=MAX_AMOUNT, message='Enter an amount above 0.'),
    ])


class LedgerEntryForm(FlaskForm):
    """Money recorded by hand on the Payments page: expenses, other income and the owner's own money.

    Customer, supplier and staff payments are taken on their invoice, order or payroll page instead.
    """
    payment_type = SelectField("What kind", choices=[(t, TYPE_LABELS[t]) for t in config.MANUAL_PAYMENT_TYPES])
    payment_amount = _amount_field()
    payment_method = SelectField("Paid by", choices=config.PAYMENT_METHOD_FORM_LIST)
    remarks = text_field("What was it for?", max_length=255, required=True)
    submit = SubmitField('Record')


class ReversalForm(FlaskForm):
    reason = text_field("Why is it being reversed?", max_length=200, required=True)
    submit = SubmitField('Reverse')


class DocumentPaymentForm(FlaskForm):
    """A payment (or refund) taken on a completed invoice or purchase order's own page."""
    payment_amount = _amount_field()
    payment_method = SelectField("Paid by", choices=config.PAYMENT_METHOD_FORM_LIST)
    remarks = text_field("Note", max_length=255)
    submit = SubmitField('Record payment')
