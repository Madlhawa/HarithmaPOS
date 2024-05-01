from flask_wtf import FlaskForm

from wtforms import StringField, SubmitField, TelField, DecimalField, DateField
from wtforms.validators import DataRequired, Length

class EmployeeUpdateForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=50)])
    contact = TelField("Contact", validators=[Length(min=9, max=9)])
    address = StringField("Address")
    designation = StringField("Designation")
    joined_date = DateField("Joined Date")
    wage = DecimalField("Wage", places=2)
    submit = SubmitField('Update Employee')

class EmployeeCreateForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=50)])
    contact = TelField("Contact", validators=[Length(min=9, max=9)])
    address = StringField("Address")
    designation = StringField("Designation")
    joined_date = DateField("Joined Date")
    wage = DecimalField("Wage", places=2)
    submit = SubmitField('Add Employee')