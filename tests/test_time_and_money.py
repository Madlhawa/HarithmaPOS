"""Moments are aware UTC everywhere; money is Decimal, rounded half up to the cent in one place."""
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from harithmapos import billing, db, payroll
from harithmapos.models import Customer, Payment
from harithmapos.template_helpers import iso_utc_filter, local_datetime_filter, money_filter
from harithmapos.timeutils import utcnow


def test_stored_moments_come_back_aware_utc(app):
    with app.app_context():
        colombo = timezone(timedelta(hours=5, minutes=30))
        p = Payment(payment_type='income', payment_direction='in', payment_method='cash', payment_amount=10,
                    created_dttm=datetime(2026, 11, 16, 1, 0, tzinfo=colombo))      # 01:00 in Colombo
        db.session.add(p)
        db.session.commit()
        pid = p.id
        db.session.expire_all()
        stored = db.session.get(Payment, pid).created_dttm
        assert stored == datetime(2026, 11, 15, 19, 30, tzinfo=timezone.utc) and stored.utcoffset() == timedelta(0)
        assert Customer.query.first().create_dttm.tzinfo is not None              # defaults too
        assert local_datetime_filter(stored, '%d %b %H:%M') == '16 Nov 01:00'     # shown in shop time
        assert iso_utc_filter(stored) == '2026-11-15T19:30:00Z'


def test_utcnow_and_day_bounds_compare_with_stored_values(app):
    from harithmapos.timeutils import local_day_bounds_utc
    with app.app_context():
        db.session.add(Payment(payment_type='income', payment_direction='in', payment_method='cash',
                               payment_amount=10, created_dttm=utcnow()))
        db.session.commit()
        lo, hi = local_day_bounds_utc()
        assert Payment.query.filter(Payment.created_dttm >= lo, Payment.created_dttm < hi).count() == 1


def test_one_rounding_rule_half_up():
    assert billing.money('2.345') == Decimal('2.35') and billing.money('2.344') == Decimal('2.34')
    assert payroll.money is billing.money
    assert money_filter(Decimal('2.345')) == '2.35'        # Python's format alone would print 2.34
    assert money_filter(Decimal('1234567.005')) == '1,234,567.01'
    assert billing.to_decimal(0.1) + billing.to_decimal(0.2) == Decimal('0.3')


def test_totals_are_sums_of_rounded_lines():
    lines = [billing.line_amounts('1', '0', '0.335', 0, 0), billing.line_amounts('1', '0', '0.335', 0, 0)]
    totals = billing.invoice_totals([type('L', (), l)() for l in lines])
    assert [l['gross_price'] for l in lines] == [Decimal('0.34'), Decimal('0.34')]
    assert totals['gross_price'] == Decimal('0.68')        # not 0.67 from rounding 0.670 once


def test_money_reaches_the_browser_as_a_number(app):
    with app.app_context():
        assert json.loads(app.json.dumps({'amount': Decimal('1500.50')})) == {'amount': 1500.5}
