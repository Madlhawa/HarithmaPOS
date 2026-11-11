from flask_wtf import FlaskForm

from wtforms import SubmitField, SelectField
from wtforms.validators import DataRequired, Length

from harithmapos.config import UOM_FORM_LIST
from harithmapos.formfields import money_field, percent_field, quantity_field, text_field


class ItemCreateForm(FlaskForm):
    name = text_field("Name", max_length=100, required=True, min_length=2)
    description = text_field("Description", max_length=255)
    # validate_choice=False so items saved with an older unit can still be edited.
    unit_of_measure = SelectField("Unit", choices=UOM_FORM_LIST, validate_choice=False,
                                  validators=[DataRequired(message='Choose a unit.'), Length(max=20)])
    # Leave the quantity empty for services and labour: they are sold without stock.
    quantity = quantity_field("Quantity in stock", required=False, allow_zero=True)
    unit_cost = money_field("Unit cost", required=True)
    unit_price = money_field("Unit price", required=True)
    discount_pct = percent_field("Discount %")
    submit = SubmitField('Add item')


class ItemUpdateForm(ItemCreateForm):
    submit = SubmitField('Save item')
