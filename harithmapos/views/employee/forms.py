from flask_wtf import FlaskForm

from wtforms import SubmitField, DateField, SelectField, BooleanField
from wtforms.validators import Optional, DataRequired

from harithmapos import config

from harithmapos.formfields import money_field, phone_field, text_field


class EmployeeCreateForm(FlaskForm):
    name = text_field("Name", max_length=100, required=True, min_length=2)
    contact = phone_field("Phone")
    address = text_field("Address", max_length=255)
    designation = text_field("Designation", max_length=40)
    joined_date = DateField("Joined date", validators=[Optional()])
    wage = money_field("Salary or day rate")
    pay_type = SelectField("Paid", choices=config.PAY_TYPE_FORM_LIST, default=config.PAY_MONTHLY,
                           validators=[DataRequired()])
    epf_enabled = BooleanField("EPF and ETF", default=True)
    epf_number = text_field("EPF number", max_length=20)
    active = BooleanField("Working here", default=True)
    submit = SubmitField('Add employee')


class EmployeeUpdateForm(EmployeeCreateForm):
    submit = SubmitField('Save employee')
