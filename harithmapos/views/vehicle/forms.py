from flask_wtf import FlaskForm

from wtforms import StringField, IntegerField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from harithmapos.formfields import id_field, text_field
from harithmapos.textutils import normalize_plate


class VehicleForm(FlaskForm):
    number = StringField("Vehicle number", filters=[normalize_plate], validators=[
        DataRequired(message='Enter the vehicle number.'),
        Length(min=4, max=8, message='Vehicle numbers are 4 to 8 characters, for example CAB-1234.'),
    ])
    make = text_field("Make", max_length=20)
    model = text_field("Model", max_length=20)
    year = IntegerField("Year", validators=[Optional(), NumberRange(min=1950, max=2100, message='Enter a four-digit year.')])
    owner_id = id_field("Owner")
