"""The sales report: periods, figures and the page. Run with: python -m pytest tests"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest

from harithmapos import db, config
from harithmapos import reports
from harithmapos.models import (
    Customer, Vehicle, WashBay, Employee, Item, InvoiceHead, InvoiceDetail, InvoiceStatusLog,
    ItemInvoiceHead, ItemInvoiceDetail, Payment,
)

TODAY = date(2026, 11, 12)


def at(day, hour, minute=0):
    """A Sri Lanka wall-clock time, stored as naive UTC like the app does."""
    return datetime.combine(day, time(hour, minute), reports.LOCAL).astimezone(reports.UTC).replace(tzinfo=None)


# --- periods ---------------------------------------------------------------

@pytest.mark.parametrize('key, start, end', [
    ('today', TODAY, TODAY),
    ('7d', date(2026, 11, 6), TODAY),
    ('30d', date(2026, 10, 14), TODAY),
    ('month', date(2026, 11, 1), TODAY),
    ('last_month', date(2026, 10, 1), date(2026, 10, 31)),
    ('90d', date(2026, 8, 15), TODAY),
    ('nonsense', date(2026, 10, 14), TODAY),
])
def test_presets(key, start, end):
    p = reports.period_from_args(key, today=TODAY)
    assert (p.start, p.end) == (start, end)


def test_custom_period_is_ordered_and_capped_at_today():
    p = reports.period_from_args('custom', '2026-12-31', '2026-11-01', today=TODAY)
    assert (p.start, p.end) == (date(2026, 11, 1), TODAY)
    assert reports.period_from_args('custom', 'bad', '2026-11-01', today=TODAY).key == '30d'


def test_previous_period_is_the_same_length_just_before():
    p = reports.Period(date(2026, 11, 1), date(2026, 11, 10))
    assert (p.previous.start, p.previous.end) == (date(2026, 10, 22), date(2026, 10, 31))


def test_local_day_bounds_are_converted_to_utc():
    lo, hi = reports.Period(TODAY, TODAY).utc_bounds()
    assert lo == datetime(2026, 11, 11, 18, 30) and hi == datetime(2026, 11, 12, 18, 30)


# --- figures -----------------------------------------------------------------

@pytest.fixture
def shop(app):
    """Two finished jobs and an item sale in early November, one job in October."""
    with app.app_context():
        bay = WashBay(name='Bay 1')
        staff = Employee(name='Sunil')
        wash = Item(name='Body wash', unit_of_measure='Job', quantity=None, unit_cost=400, unit_price=1500)
        wax = Item(name='Wax', unit_of_measure='Job', quantity=None, unit_cost=1000, unit_price=3000)
        oil = Item(name='Shampoo', unit_of_measure='Bottle', quantity=10, unit_cost=1000, unit_price=1600)
        old = Customer(name='Old Regular', contact='0700000001')
        new = Customer(name='New Face', contact='0700000002')
        db.session.add_all([bay, staff, wash, wax, oil, old, new])
        db.session.flush()
        v_old = Vehicle(number='CAB-1111', owner_id=old.id)
        v_new = Vehicle(number='CAB-2222', owner_id=new.id)
        db.session.add_all([v_old, v_new])
        db.session.flush()

        def job(customer, vehicle, when, lines, paid, status=config.SERVICE_STATUS_DONE, minutes=40):
            head = InvoiceHead(customer_id=customer.id, vehicle_id=vehicle.id, washbay_id=bay.id, employee_id=staff.id,
                               service_status=status, created_dttm=when, payment_method='cash')
            db.session.add(head)
            db.session.flush()
            gross = cost = Decimal(0)
            for item in lines:
                db.session.add(InvoiceDetail(invoice_head_id=head.id, item_id=item.id, quantity=1,
                                             total_cost=item.unit_cost, total_price=item.unit_price,
                                             discount_amount=0, gross_price=item.unit_price))
                gross += Decimal(item.unit_price)
                cost += Decimal(item.unit_cost)
            head.gross_price, head.total_price, head.total_cost, head.paid_amount = gross, gross, cost, Decimal(paid)
            head.total_discount = 0
            if status == config.SERVICE_STATUS_DONE:
                db.session.add(InvoiceStatusLog(invoice_id=head.id, service_status=4, employee_id=staff.id,
                                                created_dttm=when + timedelta(minutes=minutes)))
            if paid:
                db.session.add(Payment(invoice_id=head.id, customer_id=customer.id, payment_method='cash',
                                       payment_direction='in', payment_amount=paid, created_dttm=when))
            return head

        job(old, v_old, at(date(2026, 10, 25), 9), [wash], 1500)                    # October: previous period
        job(old, v_old, at(date(2026, 11, 3), 10), [wash, wax], 4500, minutes=60)   # November
        job(new, v_new, at(date(2026, 11, 4), 15), [wash], 0, minutes=20)            # November, unpaid
        job(new, v_new, at(date(2026, 11, 5), 11), [wax], 0, status=2)               # still in the bay: not a sale
        sale = ItemInvoiceHead(customer_id=None, created_dttm=at(date(2026, 11, 4), 12), gross_price=1600,
                               total_price=1600, total_cost=1000, total_discount=0, paid_amount=1600, payment_method='card')
        db.session.add(sale)
        db.session.flush()
        db.session.add(ItemInvoiceDetail(item_invoice_head_id=sale.id, item_id=oil.id, quantity=1, total_cost=1000,
                                         total_price=1600, discount_amount=0, gross_price=1600))
        db.session.add(Payment(item_invoice_id=sale.id, payment_method='card', payment_direction='in',
                               payment_amount=1600, created_dttm=sale.created_dttm))
        db.session.commit()
    return app


def test_november_figures(shop):
    with shop.app_context():
        r = reports.sales_report(reports.Period(date(2026, 11, 1), date(2026, 11, 10)), today=TODAY)
        k = r['kpis']
        assert k['revenue'] == Decimal('7600')            # 4500 + 1500 + 1600; the job still in the bay is not counted
        assert k['revenue_services'] == Decimal('6000')
        assert k['gross_profit'] == Decimal('7600') - Decimal('1800') - Decimal('1000')  # wash 400 + wax 1000 + wash 400; shampoo 1000
        assert k['jobs'] == 2 and k['item_sales'] == 1
        assert k['avg_ticket'] == Decimal('3000')
        assert k['collected'] == Decimal('6100')          # 4500 cash + 1600 card
        assert k['outstanding'] == Decimal('1500')
        assert k['avg_minutes'] == 40
        assert k['customers'] == 2 and k['new_customers'] == 1 and k['returning_pct'] == 50
        assert [row['name'] for row in r['by_item']] == ['Body wash', 'Wax', 'Shampoo']
        assert [m['method'] for m in r['by_method']] == ['Cash', 'Card']
        assert r['unpaid_count'] == 1 and r['unpaid'][0]['plate'] == 'CAB-2222'
        assert sum(row['jobs'] for row in r['timeline']['rows']) == 2
        assert len(r['timeline']['rows']) == 10 and not r['timeline']['weekly']
        assert r['busy']['total'] == 3                    # every arrival, done or not
        assert r['busy']['counts'][1][10 - reports.HOURS[0]] == 1  # Tuesday 3 Nov, 10 am
        # The previous ten days hold the October job.
        assert r['before']['revenue'] == Decimal('1500')
        assert round(r['deltas']['revenue']) == round((7600 - 1500) / 1500 * 100)


def test_long_periods_are_shown_by_week(shop):
    with shop.app_context():
        r = reports.sales_report(reports.Period(date(2026, 8, 1), date(2026, 11, 10)), today=TODAY)
        assert r['timeline']['weekly']
        assert sum(row['services'] for row in r['timeline']['rows']) == 7500


def test_empty_period(app):
    with app.app_context():
        r = reports.sales_report(reports.Period(TODAY, TODAY), today=TODAY)
        assert r['kpis']['revenue'] == 0 and r['kpis']['avg_ticket'] is None and r['by_item'] == []


# --- the page ------------------------------------------------------------------

def test_only_owners_see_the_report(shop, owner, staff):
    assert staff.get('/app/reports/sales').status_code == 403
    page = owner.get('/app/reports/sales?range=custom&from=2026-11-01&to=2026-11-10')
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert '7,600' in html and 'Body wash' in html and 'CAB-2222' in html


@pytest.mark.parametrize('rng', ['today', '7d', '30d', 'month', 'last_month', '90d', 'custom'])
def test_every_preset_renders(owner, rng):
    assert owner.get(f'/app/reports/sales?range={rng}').status_code == 200


def test_menu_links_to_report_for_owners_only(owner, staff):
    assert '/app/reports/sales' in owner.get('/app/dashboard').get_data(as_text=True)
    assert '/app/reports/sales' not in staff.get('/app/dashboard').get_data(as_text=True)
