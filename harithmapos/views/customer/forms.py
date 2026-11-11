from flask_wtf import FlaskForm

from wtforms import EmailField, IntegerField, StringField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional

from harithmapos.formfields import phone_field, text_field
from harithmapos.textutils import normalize_plate, strip_or_none


class CustomerForm(FlaskForm):
    name = text_field("Name", max_length=100, required=True, min_length=2)
    contact = phone_field("Phone")
    address = text_field("Address", max_length=255)
    email = EmailField("Email", filters=[strip_or_none], validators=[Optional(), Email(), Length(max=150)])


class QuickRegisterForm(FlaskForm):
    """A new customer and their vehicle in one go, for the front counter."""
    name = text_field("Customer name", max_length=100, required=True, min_length=2)
    contact = phone_field("Phone")
    number = StringField("Vehicle number", filters=[normalize_plate], validators=[
        DataRequired(message='Enter the vehicle number.'),
        Length(min=4, max=8, message='Vehicle numbers are 4 to 8 characters, for example CAB-1234.'),
    ])
    make = text_field("Make", max_length=20)
    model = text_field("Model", max_length=20)
    year = IntegerField("Year", validators=[Optional(), NumberRange(min=1950, max=2100, message='Enter a four-digit year.')])
