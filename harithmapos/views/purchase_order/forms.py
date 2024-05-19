from flask_wtf import FlaskForm

from wtforms import SubmitField, IntegerField, StringField, DecimalField, SelectField
from wtforms.validators import DataRequired, Optional

import harithmapos.config as config

class PurchaseOrderDetailCreateForm(FlaskForm):
    item = StringField("Item", validators=[DataRequired()])
    quantity = DecimalField("Qty", places=4, validators=[DataRequired()])
    submit = SubmitField('Add Item')

class PurchaseOrderHeadUpdateForm(FlaskForm):
    supplier = StringField("Supplier", validators=[DataRequired()])
    supplier_invoice_id = StringField("Supplier Invoice ID", validators=[DataRequired()])
    total_price = DecimalField("Total Price", places=2, validators=[Optional()])
    discount_pct = DecimalField("Discount Percentage", places=2, validators=[Optional()])
    gross_price = DecimalField("Gross Price", places=2, validators=[Optional()])
    payment_method = SelectField("Payment Method", choices=config.PAYMENT_METHOD_FORM_LIST)
    paid_amount = DecimalField("Paid Amount", places=2, validators=[Optional()])
    update_purchase_order = SubmitField('Update Purchase Order')
    complete_purchase_order = SubmitField('Complete Purchase Order')

class PurchaseOrderHeadCreateForm(FlaskForm):
    supplier = StringField("Supplier", validators=[DataRequired()])
    supplier_invoice_id = StringField("Supplier Invoice ID", validators=[DataRequired()])
    submit = SubmitField('Create Purchase Order')