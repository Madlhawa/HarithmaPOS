from flask_wtf import FlaskForm

from wtforms import StringField, SubmitField, DecimalField
from wtforms.validators import DataRequired, Length

class WashBayUpdateForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=50)])
    remarks = StringField("Remarks")
    capacity = DecimalField("Capacity (Tons)", places=2)
    submit = SubmitField('Update Wash Bay')

class WashBayCreateForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=50)])
    remarks = StringField("Remarks")
    capacity = DecimalField("Capacity (Tons)", places=2)
    submit = SubmitField('Insert Wash Bay')