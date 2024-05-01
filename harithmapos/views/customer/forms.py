from flask_wtf import FlaskForm

from wtforms import StringField, EmailField, TelField
from wtforms.validators import DataRequired, Length

class CustomerForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=20)])
    contact = TelField("Contact", validators=[Length(min=9, max=9)])
    address = StringField("Address")
    email = EmailField("Email")