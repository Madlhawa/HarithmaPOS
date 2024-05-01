from flask_wtf import FlaskForm

from wtforms import StringField, IntegerField
from wtforms.validators import DataRequired, Length

class VehicalForm(FlaskForm):
    number = StringField("Number*", validators=[DataRequired(), Length(min=7, max=8)])
    make = StringField("Make")
    model = StringField("Model")
    year = IntegerField("Year")
    owner_id = IntegerField("Owner ID", validators=[DataRequired()])