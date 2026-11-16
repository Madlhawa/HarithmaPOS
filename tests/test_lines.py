"""Document lines and stock, tested without the web pages (harithmapos/lines.py, stock.py)."""
from decimal import Decimal

import pytest

from harithmapos import db, documents, lines, stock
from harithmapos.models import Customer, Item, ItemInvoiceHead, PurchaseOrderHead, Supplier


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield {
            'oil': Item.query.filter_by(name='Engine oil').one(),          # 10 in stock, cost 1500, price 2000
            'wash': _service(),
            'sale': _new(ItemInvoiceHead(customer_id=Customer.query.first().id)),
            'order': _new(PurchaseOrderHead(supplier_id=Supplier.query.first().id, discount_pct=0)),
        }


def _service():
    item = Item(name='Body wash', unit_price=1500, unit_cost=0, quantity=None)
    return _new(item)


def _new(obj):
    db.session.add(obj)
    db.session.commit()
    return obj


def test_selling_takes_stock_and_totals_the_bill(ctx):
    line = lines.add_sale_line(ctx['sale'], ctx['oil'], 3, extra_discount=100)
    db.session.commit()
    assert ctx['oil'].quantity == 7
    assert line.gross_price == Decimal('5900.00')
    assert ctx['sale'].gross_price == Decimal('5900.00') and ctx['sale'].total_cost == Decimal('4500.00')


def test_cannot_sell_more_than_is_in_stock(ctx):
    with pytest.raises(stock.StockError, match='10 left, 11 asked for'):
        lines.add_sale_line(ctx['sale'], ctx['oil'], 11)
    db.session.rollback()
    assert ctx['oil'].quantity == 10 and lines.lines_of(ctx['sale']) == []


def test_services_have_no_stock(ctx):
    lines.add_sale_line(ctx['sale'], ctx['wash'], 5)
    db.session.commit()
    assert ctx['wash'].quantity is None and ctx['sale'].gross_price == Decimal('7500.00')


def test_quantity_steps_move_stock_both_ways(ctx):
    line = lines.add_sale_line(ctx['sale'], ctx['oil'], 2)
    lines.change_quantity(ctx['sale'], line, 1)
    assert ctx['oil'].quantity == 7 and ctx['sale'].gross_price == Decimal('6000.00')
    lines.change_quantity(ctx['sale'], line, -1)
    assert ctx['oil'].quantity == 8 and ctx['sale'].gross_price == Decimal('4000.00')
    lines.change_quantity(ctx['sale'], line, -1)
    with pytest.raises(documents.DocumentError, match='minimum'):
        lines.change_quantity(ctx['sale'], line, -1)


def test_last_one_in_stock_then_none(ctx):
    line = lines.add_sale_line(ctx['sale'], ctx['oil'], 10)
    with pytest.raises(stock.StockError, match='No more Engine oil'):
        lines.change_quantity(ctx['sale'], line, 1)


def test_removing_a_line_puts_stock_back(ctx):
    line = lines.add_sale_line(ctx['sale'], ctx['oil'], 4)
    lines.remove_line(ctx['sale'], line)
    db.session.commit()
    assert ctx['oil'].quantity == 10 and ctx['sale'].gross_price == 0


def test_a_completed_bill_cannot_change(ctx):
    line = lines.add_sale_line(ctx['sale'], ctx['oil'], 1)
    documents.complete(ctx['sale'])
    for change in (lambda: lines.add_sale_line(ctx['sale'], ctx['oil'], 1),
                   lambda: lines.change_quantity(ctx['sale'], line, 1),
                   lambda: lines.remove_line(ctx['sale'], line)):
        with pytest.raises(documents.DocumentError, match='completed'):
            change()
    assert ctx['oil'].quantity == 9


def test_buying_in_receives_stock_and_updates_the_cost(ctx):
    line = lines.add_purchase_line(ctx['order'], ctx['oil'], 5, unit_cost=1600)
    db.session.commit()
    assert ctx['oil'].quantity == 15 and ctx['oil'].unit_cost == Decimal('1600.00')
    assert ctx['order'].gross_price == Decimal('8000.00')
    # The line keeps its own cost when its quantity changes, even if the item's changes again.
    ctx['oil'].unit_cost = 1700
    lines.change_quantity(ctx['order'], line, 1)
    assert line.total_cost == Decimal('9600.00') and ctx['oil'].quantity == 16
    lines.remove_line(ctx['order'], line)
    assert ctx['oil'].quantity == 10


def test_services_cannot_be_bought_in(ctx):
    with pytest.raises(documents.DocumentError, match='service with no stock'):
        lines.add_purchase_line(ctx['order'], ctx['wash'], 1)


def test_void_undoes_stock_for_sales_and_orders(ctx):
    lines.add_sale_line(ctx['sale'], ctx['oil'], 4)
    lines.add_purchase_line(ctx['order'], ctx['oil'], 2)
    assert ctx['oil'].quantity == 8
    documents.void(ctx['sale'], 'wrong customer')
    documents.void(ctx['order'], 'wrong supplier')
    assert ctx['oil'].quantity == 10


def test_stock_is_read_from_the_database_not_a_stale_copy(ctx):
    db.session.execute(db.text("UPDATE item SET quantity = 2 WHERE id = :id"), {'id': ctx['oil'].id})
    assert ctx['oil'].quantity == 10          # the copy in memory is stale
    with pytest.raises(stock.StockError, match='2 left, 3 asked for'):
        stock.take(ctx['oil'], 3)


def test_routes_use_the_modules_not_each_others_helpers():
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1] / 'harithmapos' / 'views'
    for path in root.rglob('routes.py'):
        text = path.read_text()
        assert 'import _' not in text and ', _' not in text.split('from harithmapos.views')[-1].split('\n')[0], path
        assert '.quantity = ' not in text, f"{path}: stock must change through harithmapos/stock.py"
