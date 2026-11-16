"""Every stock change is written down as a StockMovement (stock.py)."""
from decimal import Decimal

import pytest
from sqlalchemy import func

from harithmapos import db, documents, lines
from harithmapos.models import Customer, Item, ItemInvoiceHead, PurchaseOrderHead, StockMovement, Supplier


def _moves(item):
    return [(m.kind, m.change, m.quantity_after, m.doc_type, m.doc_id)
            for m in StockMovement.query.filter_by(item_id=item.id).order_by(StockMovement.id)]


def _balanced(item):
    total = db.session.query(func.coalesce(func.sum(StockMovement.change), 0)).filter_by(item_id=item.id).scalar()
    return Decimal(str(total)) == Decimal(str(item.quantity or 0))


@pytest.fixture
def ctx(app):
    with app.app_context():
        oil = Item.query.filter_by(name='Engine oil').one()        # 10 in stock, from before the history
        sale = ItemInvoiceHead(customer_id=Customer.query.first().id)
        order = PurchaseOrderHead(supplier_id=Supplier.query.first().id, discount_pct=0)
        db.session.add_all([sale, order])
        db.session.commit()
        yield {'oil': oil, 'sale': sale, 'order': order}


def test_sales_and_their_undoing_are_written_down(ctx):
    oil, sale = ctx['oil'], ctx['sale']
    line = lines.add_sale_line(sale, oil, 3)
    lines.change_quantity(sale, line, 1)
    lines.change_quantity(sale, line, -1)
    lines.remove_line(sale, line)
    db.session.commit()
    D = Decimal
    assert _moves(oil) == [
        ('sale', D(-3), D(7), 'item_sale', sale.id),
        ('sale', D(-1), D(6), 'item_sale', sale.id),
        ('sale_undo', D(1), D(7), 'item_sale', sale.id),
        ('sale_undo', D(3), D(10), 'item_sale', sale.id),
    ]


def test_purchases_and_voids_are_written_down(ctx):
    oil, order = ctx['oil'], ctx['order']
    lines.add_purchase_line(order, oil, 5)
    documents.complete(order)
    documents.void(order, 'Wrong supplier')
    db.session.commit()
    assert [(k, c, a) for k, c, a, _, _ in _moves(oil)] == [
        ('purchase', Decimal(5), Decimal(15)), ('void', Decimal(-5), Decimal(10))]
    assert {(t, i) for _, _, _, t, i in _moves(oil)} == {('purchase_order', order.id)}


def test_a_refused_sale_writes_nothing(ctx):
    from harithmapos import stock
    with pytest.raises(stock.StockError):
        lines.add_sale_line(ctx['sale'], ctx['oil'], 11)
    db.session.rollback()
    assert _moves(ctx['oil']) == []


def test_services_have_no_history(ctx):
    wash = Item(name='Body wash', unit_price=1500, unit_cost=0, quantity=None)
    db.session.add(wash)
    db.session.commit()
    lines.add_sale_line(ctx['sale'], wash, 2)
    db.session.commit()
    assert _moves(wash) == []


def _item_form(**values):
    data = {'name': 'Brake fluid', 'description': '', 'unit_of_measure': 'Bottle', 'quantity': '12',
            'unit_cost': '900', 'unit_price': '1200', 'discount_pct': ''}
    data.update(values)
    return data


def test_the_items_page_writes_opening_stock_and_counts(app, owner):
    owner.post('/app/item/create', data=_item_form())
    with app.app_context():
        fluid = Item.query.filter_by(name='Brake fluid').one()
        item_id = fluid.id
        assert [(k, c, a) for k, c, a, _, _ in _moves(fluid)] == [('opening', Decimal(12), Decimal(12))]
    owner.post(f'/app/item/{item_id}/update', data=_item_form(quantity='9'))       # counted 9 on the shelf
    owner.post(f'/app/item/{item_id}/update', data=_item_form(quantity='9', unit_price='1300'))   # price only
    owner.post(f'/app/item/{item_id}/update', data=_item_form(quantity=''))        # now a service
    owner.post(f'/app/item/{item_id}/update', data=_item_form(quantity='4'))       # stocked again
    with app.app_context():
        fluid = db.session.get(Item, item_id)
        moves = StockMovement.query.filter_by(item_id=item_id).order_by(StockMovement.id).all()
        assert [(m.kind, m.change, m.quantity_after) for m in moves] == [
            ('opening', 12, 12), ('count', -3, 9), ('count', -9, 0), ('count', 4, 4)]
        assert moves[1].user.name == 'Olivia Owner'
        assert _balanced(fluid)


def test_the_stock_page_lists_the_history(app, owner, staff):
    with app.app_context():
        oil = Item.query.filter_by(name='Engine oil').one()
        sale = ItemInvoiceHead(customer_id=Customer.query.first().id)
        db.session.add(sale)
        db.session.commit()
        lines.add_sale_line(sale, oil, 2)
        db.session.commit()
        oil_id, sale_id = oil.id, sale.id
    for client in (owner, staff):
        page = client.get(f'/app/item/{oil_id}/stock').get_data(as_text=True)
        assert 'Sold' in page and f'item sale #{sale_id}' in page and '-2' in page
    assert f'/app/item/{oil_id}/stock' in owner.get('/app/item').get_data(as_text=True)
    assert owner.get('/app/item/99999/stock').status_code == 404


def test_deleting_an_item_takes_its_history_with_it(app, owner):
    owner.post('/app/item/create', data=_item_form(name='Spare bulb'))
    with app.app_context():
        item_id = Item.query.filter_by(name='Spare bulb').one().id
    owner.post(f'/app/item/{item_id}/delete')
    with app.app_context():
        assert db.session.get(Item, item_id) is None
        assert StockMovement.query.filter_by(item_id=item_id).count() == 0
