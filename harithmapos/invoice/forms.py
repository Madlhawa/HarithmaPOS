from flask_wtf import FlaskForm

from wtforms import SubmitField, IntegerField, StringField, DecimalField
from wtforms.validators import DataRequired, Length

class InvoiceHeadUpdateForm(FlaskForm):
    vehical = StringField("Vehical", validators=[DataRequired()])
    # employee = IntegerField("Employee", validators=[DataRequired()])
    washbay = IntegerField("Wash Bay", validators=[DataRequired()])
    current_milage = IntegerField("Current Milage")
    next_milage = IntegerField("Next Milage")
    service_status = StringField("Status")
    total_cost = DecimalField("Total Cost", places=2)
    total_price = DecimalField("Total Price", places=2)
    discount_pct = DecimalField("Discount Percentage", places=2)
    gross_price = DecimalField("Gross Price", places=2)
    payment_method = StringField("Payment Method")
    paid_amount = DecimalField("Paid Amount", places=2)
    submit = SubmitField('Update InvoiceHead')

class InvoiceHeadCreateForm(FlaskForm):
    vehical = StringField("Vehical", validators=[DataRequired()])
    employee = IntegerField("Employee", validators=[DataRequired()])
    washbay = IntegerField("Wash Bay", validators=[DataRequired()])
    current_milage = IntegerField("Milage")
    submit = SubmitField('Create Invoice')