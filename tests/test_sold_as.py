"""Lines keep the item's name and prices as sold (models.SoldAs, lines.py)."""
from decimal import Decimal

import pytest

from harithmapos import db, documents, lines
from harithmapos.models import Customer, Item, ItemInvoiceDetail, ItemInvoiceHead, PurchaseOrderHead, Supplier


@pytest.fixture
def ctx(app):
    with app.app_context():
        oil = Item.query.filter_by(name='Engine oil').one()      # cost 1500, price 2000
        oil.discount_pct = 10
        sale = ItemInvoiceHead(customer_id=Customer.query.first().id)
        order = PurchaseOrderHead(supplier_id=Supplier.query.first().id, discount_pct=0)
        db.session.add_all([sale, order])
        db.session.commit()
        yield {'oil': oil, 'sale': sale, 'order': order}


def _reprice(item):
    item.name = 'Engine oil 5W-30 (new name)'
    item.unit_price = 2600
    item.unit_cost = 1900
    item.discount_pct = 0
    db.session.commit()


def test_a_sale_line_copies_the_item_as_it_is_now(ctx):
    line = lines.add_sale_line(ctx['sale'], ctx['oil'], 2)
    db.session.commit()
    assert (line.item_name, line.unit_price, line.unit_cost, line.discount_pct) == \
        ('Engine oil', Decimal('2000.00'), Decimal('1500.00'), Decimal('10'))
    assert line.discount_amount == Decimal('400.00') and line.gross_price == Decimal('3600.00')


def test_changing_the_item_later_leaves_the_line_alone(ctx):
    line = lines.add_sale_line(ctx['sale'], ctx['oil'], 2)
    db.session.commit()
    _reprice(ctx['oil'])
    lines.change_quantity(ctx['sale'], line, 1)        # +1 on the draft keeps the price it was added at
    db.session.commit()
    assert line.item_name == 'Engine oil'
    assert line.total_price == Decimal('6000.00') and line.discount_amount == Decimal('600.00')
    assert line.total_cost == Decimal('4500.00') and ctx['sale'].gross_price == Decimal('5400.00')


def test_a_new_line_takes_the_new_price(ctx):
    lines.add_sale_line(ctx['sale'], ctx['oil'], 1)
    _reprice(ctx['oil'])
    line = lines.add_sale_line(ctx['sale'], ctx['oil'], 1)
    db.session.commit()
    assert line.item_name == 'Engine oil 5W-30 (new name)' and line.gross_price == Decimal('2600.00')
    assert ctx['sale'].gross_price == Decimal('1800.00') + Decimal('2600.00')


def test_a_purchase_line_keeps_its_cost(ctx):
    line = lines.add_purchase_line(ctx['order'], ctx['oil'], 2, unit_cost='1450.50')
    db.session.commit()
    _reprice(ctx['oil'])
    lines.change_quantity(ctx['order'], line, 1)
    db.session.commit()
    assert (line.item_name, line.unit_cost, line.total_cost) == ('Engine oil', Decimal('1450.50'), Decimal('4351.50'))
    assert line.total_price == Decimal('6000.00')


def test_pages_and_prints_show_the_name_and_price_as_sold(app, owner):
    with app.app_context():
        oil = Item.query.filter_by(name='Engine oil').one()
        sale = ItemInvoiceHead(customer_id=Customer.query.first().id)
        db.session.add(sale)
        db.session.commit()
        lines.add_sale_line(sale, oil, 1)
        documents.complete(sale)
        db.session.commit()
        _reprice(oil)
        sale_id = sale.id
    for url in (f"/app/item_invoice/head/{sale_id}", f"/app/item_invoice/head/{sale_id}/print"):
        page = owner.get(url).get_data(as_text=True)
        assert 'Engine oil' in page and '2,000.00' in page, url
        assert 'new name' not in page and '2,600.00' not in page, url


def test_a_line_saved_without_the_copies_fills_them_in(app):
    with app.app_context():
        sale = ItemInvoiceHead(customer_id=Customer.query.first().id)
        db.session.add(sale)
        db.session.flush()
        oil = Item.query.filter_by(name='Engine oil').one()
        line = ItemInvoiceDetail(item_invoice_head_id=sale.id, item_id=oil.id, quantity=Decimal('2.5'),
                                 total_cost=3750, total_price=5000, discount_amount=0, gross_price=5000)
        db.session.add(line)
        db.session.commit()
        assert (line.item_name, line.unit_price, line.unit_cost) == ('Engine oil', Decimal('2000.00'), Decimal('1500.00'))
