from flask_wtf import FlaskForm

from wtforms import StringField, SubmitField, TelField
from wtforms.validators import DataRequired, Length

class SupplierUpdateForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=20)])
    contact = TelField("Contact", validators=[Length(min=9, max=9)])
    address = StringField("Address")
    submit = SubmitField('Update Supplier')

class SupplierCreateForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=20)])
    contact = TelField("Contact", validators=[Length(min=9, max=9)])
    address = StringField("Address")
    submit = SubmitField('Add Supplier')