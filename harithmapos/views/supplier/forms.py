from flask_wtf import FlaskForm

from wtforms import SubmitField

from harithmapos.formfields import phone_field, text_field


class SupplierCreateForm(FlaskForm):
    name = text_field("Name", max_length=100, required=True, min_length=2)
    contact = phone_field("Phone")
    address = text_field("Address", max_length=255)
    submit = SubmitField('Add supplier')


class SupplierUpdateForm(SupplierCreateForm):
    submit = SubmitField('Save supplier')
