from flask_wtf import FlaskForm

from wtforms import StringField, SubmitField, IntegerField, DecimalField, SelectField
from wtforms.validators import DataRequired, Length
from harithmapos.config import UOM_FORM_LIST

class ItemUpdateForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=100)])
    description = StringField("Description")
    unit_of_measure = SelectField("Unit Of Measure", choices=UOM_FORM_LIST, validators=[DataRequired()])
    quantity = DecimalField("Quantity", places=4)
    unit_cost = DecimalField("Unit Cost", places=2, validators=[DataRequired()])
    unit_price = DecimalField("Unit Price", places=2, validators=[DataRequired()])
    discount_pct = DecimalField("Discount Pct", places=2)
    submit = SubmitField('Update Item')


class ItemCreateForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=100)])
    description = StringField("Description")
    unit_of_measure = SelectField("Unit Of Measure", choices=UOM_FORM_LIST, validators=[DataRequired()])
    quantity = DecimalField("Quantity", places=4)
    unit_cost = DecimalField("Unit Cost", places=2, validators=[DataRequired()])
    unit_price = DecimalField("Unit Price", places=2, validators=[DataRequired()])
    discount_pct = DecimalField("Discount Pct", places=2)
    submit = SubmitField('Insert Item')