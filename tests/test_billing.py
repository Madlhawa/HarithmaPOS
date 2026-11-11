"""Tests for the money, phone and time rules. Run with: python -m pytest tests"""
from datetime import date, datetime
from decimal import Decimal as D
from types import SimpleNamespace as Line

from harithmapos.billing import amount_to_record, invoice_totals, line_amounts, money, purchase_totals
from harithmapos.textutils import format_phone, normalize_phone, normalize_plate
from harithmapos.timeutils import elapsed_text, local_day_bounds_utc, to_local


def test_line_with_item_discount_and_extra_discount():
    a = line_amounts(2, '1500', '2000', discount_pct=10, additional_discount=100)
    assert a['total_price'] == D('4000.00')
    assert a['total_cost'] == D('3000.00')
    assert a['discount_amount'] == D('500.00')       # 400 automatic + 100 extra
    assert a['gross_price'] == D('3500.00')


def test_discount_can_never_exceed_the_line_price():
    a = line_amounts(1, 0, '500', discount_pct=50, additional_discount=10000)
    assert a['discount_amount'] == D('500.00')
    assert a['additional_discount'] == D('250.00')
    assert a['gross_price'] == D('0.00')


def test_fractional_quantities_round_to_cents():
    a = line_amounts(D('1.5'), '1033.33', '1333.33')
    assert a['total_price'] == D('2000.00')         # 1999.995 rounds half up


def _lines():
    return [Line(total_cost=D('300'), total_price=D('1000'), discount_amount=D('100'), gross_price=D('900')),
            Line(total_cost=D('2000'), total_price=D('2500'), discount_amount=D('0'), gross_price=D('2500'))]


def test_invoice_totals_with_bill_discount_and_part_payment():
    t = invoice_totals(_lines(), bill_discount=400, paid=1000)
    assert t['total_price'] == D('3500.00')
    assert t['total_discount'] == D('500.00')
    assert t['gross_price'] == D('3000.00')
    assert t['remaining_amount'] == D('2000.00')


def test_bill_discount_is_capped_at_the_bill():
    t = invoice_totals(_lines(), bill_discount=99999)
    assert t['gross_price'] == D('0.00')
    assert t['discount_amount'] == D('3400.00')


def test_overpayment_shows_as_change_and_only_the_bill_is_recorded():
    t = invoice_totals(_lines(), paid=5000)
    assert t['remaining_amount'] == D('-1600.00')
    assert amount_to_record(5000, t['gross_price']) == D('3400.00')
    assert amount_to_record(1000, t['gross_price']) == D('1000.00')


def test_empty_invoice_is_zero():
    t = invoice_totals([], bill_discount=None, paid=None)
    assert t['gross_price'] == D('0.00') and t['remaining_amount'] == D('0.00')


def test_purchase_orders_are_owed_at_cost_not_selling_price():
    t = purchase_totals(_lines(), discount_pct=10, paid=500)
    assert t['total_cost'] == D('2300.00')
    assert t['gross_price'] == D('2070.00')
    assert t['remaining_amount'] == D('1570.00')


def test_money_rounds_half_up():
    assert money('2.345') == D('2.35')
    assert money(None) == D('0.00')


def test_phone_numbers_are_stored_as_nine_digits():
    for typed in ['0771234567', '077 123 4567', '+94 77 123 4567', '771234567', '0094771234567']:
        assert normalize_phone(typed) == '771234567', typed
    assert normalize_phone('') is None
    assert format_phone('771234567') == '077 123 4567'


def test_plates_are_upper_case_and_trimmed():
    assert normalize_plate('  cab-1234 ') == 'CAB-1234'
    assert normalize_plate('wp  kd   5678') == 'WP KD 5678'


def test_today_means_the_colombo_calendar_day():
    # 00:00 to 24:00 in Colombo is 18:30 the day before to 18:30 UTC.
    start, end = local_day_bounds_utc(date(2026, 11, 11))
    assert start == datetime(2026, 11, 10, 18, 30)
    assert end == datetime(2026, 11, 11, 18, 30)
    assert to_local(datetime(2026, 11, 10, 20, 0)).date() == date(2026, 11, 11)


def test_elapsed_text():
    now = datetime(2026, 1, 1, 12, 0)
    assert elapsed_text(datetime(2026, 1, 1, 11, 48), now) == '12m'
    assert elapsed_text(datetime(2026, 1, 1, 9, 45), now) == '2h 15m'
