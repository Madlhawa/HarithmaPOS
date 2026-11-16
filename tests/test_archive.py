"""Customers, items and suppliers are archived, never deleted; employees are marked as left (archive.py)."""
import pytest

from harithmapos import db, documents, lines
from harithmapos.models import Customer, Employee, Item, ItemInvoiceHead, PurchaseOrderHead, Supplier, Vehicle


def _id(app, model, **by):
    with app.app_context():
        return model.query.filter_by(**by).one().id


def _page(client, url):
    client.get(url)                      # shows (and clears) the "archived" message, which names the record
    return client.get(url).get_data(as_text=True)


def _names(client, url):
    return [row['name'] for row in client.get(url).get_json()]


def test_an_archived_customer_leaves_lists_and_search_until_restored(app, owner):
    cid = _id(app, Customer, name='Kamal Perera')
    owner.post(f'/app/customer/{cid}/archive')
    with app.app_context():
        customer = db.session.get(Customer, cid)
        assert customer.is_archived
        assert customer.archived_by_id is not None
    assert 'Kamal Perera' not in _page(owner, '/app/customer/')
    assert 'Kamal Perera' in owner.get('/app/customer/?show=archived').get_data(as_text=True)
    assert _names(owner, '/app/search/customers?q=Kamal') == []
    owner.post(f'/app/customer/{cid}/restore')
    assert _names(owner, '/app/search/customers?q=Kamal') == ['Kamal Perera']
    assert 'Kamal Perera' in _page(owner, '/app/customer/')


def test_the_walk_in_customer_cannot_be_archived(app, owner):
    with app.app_context():
        db.session.add(Customer(id=-1, name='General Customer'))
        db.session.commit()
    owner.post('/app/customer/-1/archive')
    with app.app_context():
        assert not db.session.get(Customer, -1).is_archived


def test_a_new_vehicle_or_sale_brings_an_archived_customer_back(app, owner):
    cid = _id(app, Customer, name='Kamal Perera')
    for make_record in (lambda: Vehicle(number='CAB-1234', owner_id=cid),
                        lambda: ItemInvoiceHead(customer_id=cid)):
        owner.post(f'/app/customer/{cid}/archive')
        with app.app_context():
            assert db.session.get(Customer, cid).is_archived
            db.session.add(make_record())
            db.session.commit()
            assert not db.session.get(Customer, cid).is_archived


def test_an_archived_item_cannot_be_sold_or_bought(app, owner):
    iid = _id(app, Item, name='Engine oil')
    owner.post(f'/app/item/{iid}/archive')
    assert _names(owner, '/app/search/items?q=oil') == []
    assert 'Engine oil' in owner.get('/app/item?stock=archived').get_data(as_text=True)
    with app.app_context():
        item = db.session.get(Item, iid)
        sale = ItemInvoiceHead(customer_id=Customer.query.first().id)
        order = PurchaseOrderHead(supplier_id=Supplier.query.first().id, discount_pct=0)
        db.session.add_all([sale, order])
        db.session.commit()
        with pytest.raises(documents.DocumentError, match='archived'):
            lines.add_sale_line(sale, item, 1)
        with pytest.raises(documents.DocumentError, match='archived'):
            lines.add_purchase_line(order, item, 1)
        db.session.rollback()
        assert item.quantity == 10
    owner.post(f'/app/item/{iid}/restore')
    assert _names(owner, '/app/search/items?q=oil') == ['Engine oil']


def test_a_new_order_brings_an_archived_supplier_back(app, owner):
    sid = _id(app, Supplier, name='Oil Depot')
    owner.post(f'/app/supplier/{sid}/archive')
    assert _names(owner, '/app/search/suppliers?q=Oil') == []
    assert 'Oil Depot' not in _page(owner, '/app/supplier')
    assert 'Oil Depot' in owner.get('/app/supplier?show=archived').get_data(as_text=True)
    with app.app_context():
        db.session.add(PurchaseOrderHead(supplier_id=sid, discount_pct=0))
        db.session.commit()
        assert not db.session.get(Supplier, sid).is_archived


def test_an_employee_who_left_is_kept_but_not_offered(app, owner):
    with app.app_context():
        db.session.add(Employee(name='Nimal Silva'))
        db.session.commit()
    eid = _id(app, Employee, name='Nimal Silva')
    assert _names(owner, '/app/search/employees?q=Nimal') == ['Nimal Silva']
    owner.post(f'/app/employee/{eid}/left')
    with app.app_context():
        assert db.session.get(Employee, eid).active is False
    assert _names(owner, '/app/search/employees?q=Nimal') == []
    assert 'Nimal Silva' in owner.get('/app/employee?show=all').get_data(as_text=True)


def test_nothing_can_be_deleted_any_more(app, owner):
    for url in ('/app/item/1/delete', '/app/supplier/1/delete', '/app/employee/1/delete', '/app/delete_customer/1'):
        assert owner.post(url).status_code == 404, url


def test_staff_cannot_archive_or_restore(app, staff):
    sid = _id(app, Supplier, name='Oil Depot')
    iid = _id(app, Item, name='Engine oil')
    staff.post(f'/app/supplier/{sid}/archive')
    staff.post(f'/app/item/{iid}/archive')
    with app.app_context():
        assert not db.session.get(Supplier, sid).is_archived and not db.session.get(Item, iid).is_archived
