from flask_wtf import FlaskForm

from wtforms import SubmitField
from wtforms.validators import NumberRange, Optional

from harithmapos.formfields import NumberBox, text_field


class WashBayCreateForm(FlaskForm):
    name = text_field("Name", max_length=50, required=True, min_length=2)
    remarks = text_field("Remarks", max_length=255)
    capacity = NumberBox("Capacity (tons)", places=2, validators=[Optional(), NumberRange(min=0, max=9999)])
    submit = SubmitField('Add wash bay')


class WashBayUpdateForm(WashBayCreateForm):
    submit = SubmitField('Save wash bay')
