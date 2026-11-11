from flask_wtf import FlaskForm

from wtforms import SubmitField, DateField
from wtforms.validators import Optional

from harithmapos.formfields import money_field, phone_field, text_field


class EmployeeCreateForm(FlaskForm):
    name = text_field("Name", max_length=100, required=True, min_length=2)
    contact = phone_field("Phone")
    address = text_field("Address", max_length=255)
    designation = text_field("Designation", max_length=40)
    joined_date = DateField("Joined date", validators=[Optional()])
    wage = money_field("Wage")
    submit = SubmitField('Add employee')


class EmployeeUpdateForm(EmployeeCreateForm):
    submit = SubmitField('Save employee')
