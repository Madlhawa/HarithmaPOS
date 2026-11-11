"""Field builders shared by the WTForms classes, so every form validates the same way."""

from decimal import Decimal

from wtforms import DecimalField, IntegerField, StringField, TelField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional, Regexp
from wtforms.widgets import HiddenInput

from harithmapos.textutils import normalize_phone, strip_or_none

MAX_AMOUNT = Decimal('99999999.99')   # fits Numeric(10, 2)
MAX_QUANTITY = Decimal('999999.9999')  # fits Numeric(10, 4)

PHONE_MESSAGE = 'Enter a 10-digit phone number such as 0771234567.'


class NumberBox(DecimalField):
    """A DecimalField that forgives thousands separators: '1,500.00' -> 1500.00."""

    def process_formdata(self, valuelist):
        if valuelist:
            valuelist = [str(valuelist[0]).replace(',', '').replace(' ', '')]
        super().process_formdata(valuelist)


def phone_field(label='Phone'):
    """Optional phone number, stored as 9 digits whatever way it was typed."""
    return TelField(label, filters=[normalize_phone], validators=[
        Optional(),
        Regexp(r'^\d{9}$', message=PHONE_MESSAGE),
    ])


def text_field(label, max_length, required=False, min_length=None):
    validators = [DataRequired(message='This cannot be empty.')] if required else [Optional()]
    validators.append(Length(min=min_length or -1, max=max_length))
    return StringField(label, filters=[strip_or_none], validators=validators)


def money_field(label, required=False):
    """An amount of money, zero allowed."""
    first = InputRequired(message='Enter an amount.') if required else Optional()
    return NumberBox(label, places=2, validators=[
        first,
        NumberRange(min=0, max=MAX_AMOUNT, message='Enter an amount of 0 or more.'),
    ])


def quantity_field(label, required=True, allow_zero=False):
    first = InputRequired(message='Enter a quantity.') if required else Optional()
    minimum = 0 if allow_zero else Decimal('0.0001')
    message = 'Enter a quantity of 0 or more.' if allow_zero else 'Enter a quantity above 0.'
    return NumberBox(label, places=4, validators=[
        first,
        NumberRange(min=minimum, max=MAX_QUANTITY, message=message),
    ])


def percent_field(label):
    return NumberBox(label, places=2, validators=[
        Optional(),
        NumberRange(min=0, max=100, message='Enter a percentage between 0 and 100.'),
    ])


def id_field(label, required=True):
    """Hidden id filled in by a search box. label is the thing being picked ("Vehicle")."""
    if required:
        validators = [DataRequired(message='Choose one from the list.')]
    else:
        validators = [Optional()]
    return IntegerField(label, widget=HiddenInput(), validators=validators)


def mileage_field(label):
    return IntegerField(label, validators=[
        Optional(),
        NumberRange(min=0, max=9999999, message='Enter the odometer reading in km.'),
    ])
