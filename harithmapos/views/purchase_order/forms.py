from flask_wtf import FlaskForm

from wtforms import SubmitField, StringField, SelectField
from wtforms.validators import Optional

import harithmapos.config as config
from harithmapos.formfields import id_field, money_field, percent_field, quantity_field, text_field


class PurchaseOrderDetailCreateForm(FlaskForm):
    item = StringField("Item", validators=[Optional()])
    item_id = id_field("Item")
    quantity = quantity_field("Quantity")
    # What the supplier charged per unit. Left empty, the item's current cost is used.
    unit_cost = money_field("Unit cost")
    submit = SubmitField('Add item')


class PurchaseOrderHeadUpdateForm(FlaskForm):
    supplier = StringField("Supplier", validators=[Optional()])
    supplier_id = id_field("Supplier", required=False)
    supplier_invoice_id = text_field("Supplier invoice no.", max_length=255)
    discount_pct = percent_field("Discount %")
    payment_method = SelectField("Payment method", choices=config.PAYMENT_METHOD_FORM_LIST)
    paid_amount = money_field("Paid amount")
    update_purchase_order = SubmitField('Save')
    complete_purchase_order = SubmitField('Complete')


class PurchaseOrderHeadCreateForm(FlaskForm):
    supplier = StringField("Supplier", validators=[Optional()])
    supplier_id = id_field("Supplier")
    supplier_invoice_id = text_field("Supplier invoice no.", max_length=255)
    submit = SubmitField('Create purchase order')
