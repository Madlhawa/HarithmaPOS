"""Attendance, leave and payroll arithmetic.

The rules, in one place (the numbers come from Settings > Staff and payroll):

Register (one row per employee per day; a day with no row is "not marked")
- Late: arrived after work start + grace. The minutes counted are from work
  start, so 25 minutes late with a 10 minute grace is 25 minutes late.
- Left early: left before work end.
- Overtime: stayed at least the overtime minimum past work end; all the
  minutes past work end then count.
- Late arrivals, early leaving and short leaves are recorded and reported.
  They do not change pay.

Days in a month
- Present = 1, half day = 0.5 worked + 0.5 of its leave type (no-pay if none).
- Leave: annual, casual and sick are paid; no-pay leave is not.
- Absent = a no-pay day. Day off = neither worked nor deducted.

Pay
- Monthly salary: salary - salary / divisor x no-pay days. In the month
  someone joins, the salary is pro-rated by calendar days from the joined date.
- Daily wage: day rate x days worked (leave is not paid for daily staff).
- Overtime: hours x hourly rate x overtime %. Hourly rate is salary / hour
  divisor for monthly staff, day rate / normal working hours for daily staff.
- EPF/ETF (when on for the employee) are worked out on earnings without
  overtime: basic - no-pay deduction + allowances.
- Net = basic - no-pay + overtime + allowances - EPF (8%) - advances
  - other deductions. Employer EPF (12%) and ETF (3%) are costs on top.
"""
import calendar
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from harithmapos import config, settings as app_settings

ZERO = Decimal('0')
CENT = Decimal('0.01')
PAID_LEAVE = {config.LEAVE_ANNUAL, config.LEAVE_CASUAL, config.LEAVE_SICK}


def money(value):
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def parse_hhmm(text, fallback):
    try:
        h, m = (int(x) for x in str(text).split(':')[:2])
        return time(h, m)
    except (ValueError, TypeError):
        return fallback


@dataclass(frozen=True)
class Rules:
    work_start: time = time(7, 30)
    work_end: time = time(17, 30)
    grace: int = 10
    overtime_min: int = 30
    annual_days: int = 14
    casual_days: int = 7
    day_divisor: int = 30
    hour_divisor: int = 240
    overtime_pct: int = 150
    epf_employee_pct: int = 8
    epf_employer_pct: int = 12
    etf_pct: int = 3

    @property
    def normal_minutes(self):
        return max(_minutes(self.work_end) - _minutes(self.work_start), 60)

    @classmethod
    def from_settings(cls):
        get = app_settings.get
        return cls(
            work_start=parse_hhmm(get('work_start'), time(7, 30)),
            work_end=parse_hhmm(get('work_end'), time(17, 30)),
            grace=get('late_grace_minutes'),
            overtime_min=get('overtime_min_minutes'),
            annual_days=get('annual_leave_days'),
            casual_days=get('casual_leave_days'),
            day_divisor=get('salary_day_divisor'),
            hour_divisor=get('overtime_hour_divisor'),
            overtime_pct=get('overtime_rate_pct'),
            epf_employee_pct=get('epf_employee_pct'),
            epf_employer_pct=get('epf_employer_pct'),
            etf_pct=get('etf_employer_pct'),
        )


def _minutes(t):
    return t.hour * 60 + t.minute


def day_minutes(status, time_in, time_out, rules):
    """(late, early, overtime) minutes for one register row."""
    if status not in (config.ATT_PRESENT, config.ATT_HALF):
        return 0, 0, 0
    start, end = _minutes(rules.work_start), _minutes(rules.work_end)
    late = early = overtime = 0
    if time_in is not None:
        diff = _minutes(time_in) - start
        if diff > rules.grace:
            late = diff
    if time_out is not None and status == config.ATT_PRESENT:
        out = _minutes(time_out)
        if time_in is not None and out < _minutes(time_in):
            out += 24 * 60  # worked past midnight
        if out < end:
            early = end - out
        elif out - end >= max(rules.overtime_min, 1):
            overtime = out - end
    return late, early, overtime


def month_bounds(month):
    first = month.replace(day=1)
    last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
    return first, last


@dataclass
class MonthSummary:
    days_in_month: int = 0
    employed_days: int = 0          # days of the month on or after the joined date
    days_counted: int = 0           # up to today for the current month
    present: Decimal = ZERO          # days worked, half days as 0.5
    paid_leave: Decimal = ZERO
    nopay: Decimal = ZERO
    off: int = 0
    unmarked: int = 0
    late_count: int = 0
    late_minutes: int = 0
    early_count: int = 0
    early_minutes: int = 0
    short_leave_count: int = 0
    short_leave_minutes: int = 0
    overtime_minutes: int = 0
    leave_by_type: dict = field(default_factory=dict)
    by_date: dict = field(default_factory=dict)


def summarise_month(days, short_leaves, month, today, joined=None):
    """days: AttendanceDay-like rows for one employee in the month.
    joined: the employee's joined date; days before it are not counted at all."""
    first, last = month_bounds(month)
    s = MonthSummary(days_in_month=last.day)
    start = max(first, joined) if joined else first
    s.employed_days = max((last - start).days + 1, 0)
    counted_to = min(last, today)
    s.days_counted = max((counted_to - start).days + 1, 0)
    half = Decimal('0.5')
    for d in days:
        s.by_date[d.work_date] = d
        if d.status == config.ATT_PRESENT:
            s.present += 1
        elif d.status == config.ATT_HALF:
            s.present += half
            if d.leave_type in PAID_LEAVE:
                s.paid_leave += half
            else:
                s.nopay += half
            key = d.leave_type or config.LEAVE_NOPAY
            s.leave_by_type[key] = s.leave_by_type.get(key, ZERO) + half
        elif d.status == config.ATT_LEAVE:
            key = d.leave_type or config.LEAVE_NOPAY
            s.leave_by_type[key] = s.leave_by_type.get(key, ZERO) + 1
            if key in PAID_LEAVE:
                s.paid_leave += 1
            else:
                s.nopay += 1
        elif d.status == config.ATT_ABSENT:
            s.nopay += 1
        elif d.status == config.ATT_OFF:
            s.off += 1
        if d.late_minutes:
            s.late_count += 1
            s.late_minutes += d.late_minutes
        if d.early_minutes:
            s.early_count += 1
            s.early_minutes += d.early_minutes
        s.overtime_minutes += d.overtime_minutes or 0
    for sl in short_leaves:
        s.short_leave_count += 1
        s.short_leave_minutes += sl.minutes or 0
    marked = {d.work_date for d in days if start <= d.work_date <= counted_to}
    s.unmarked = s.days_counted - len(marked)
    return s


@dataclass
class PayslipFigures:
    pay_type: str
    rate: Decimal
    basic_pay: Decimal
    nopay_deduction: Decimal
    overtime_pay: Decimal
    allowances: Decimal
    gross_pay: Decimal
    epf_employee: Decimal
    advances: Decimal
    other_deductions: Decimal
    net_pay: Decimal
    epf_employer: Decimal
    etf_employer: Decimal


def compute_pay(pay_type, rate, epf_enabled, summary, rules, allowances=0, advances=0, other_deductions=0):
    rate = money(rate)
    allowances, advances, other = money(allowances), money(advances), money(other_deductions)
    hours = Decimal(summary.overtime_minutes) / 60
    if pay_type == config.PAY_DAILY:
        basic = money(rate * summary.present)
        nopay = ZERO
        hourly = rate / (Decimal(rules.normal_minutes) / 60)
    else:
        basic = rate
        if summary.days_in_month and 0 < summary.employed_days < summary.days_in_month:
            # Joined during the month: pay the share of the month they were here.
            basic = money(rate * summary.employed_days / summary.days_in_month)
        nopay = min(money(rate / rules.day_divisor * summary.nopay), basic)
        hourly = rate / rules.hour_divisor
    overtime = money(hours * hourly * Decimal(rules.overtime_pct) / 100)
    gross = basic - nopay + overtime + allowances
    epf_base = basic - nopay + allowances
    if epf_enabled:
        epf_emp = money(epf_base * rules.epf_employee_pct / 100)
        epf_er = money(epf_base * rules.epf_employer_pct / 100)
        etf = money(epf_base * rules.etf_pct / 100)
    else:
        epf_emp = epf_er = etf = ZERO
    net = gross - epf_emp - advances - other
    return PayslipFigures(pay_type, rate, basic, nopay, overtime, allowances, gross, epf_emp, advances, other,
                          net, epf_er, etf)


def leave_taken(days):
    """{leave type: days} for a set of register rows (half days count 0.5)."""
    taken = {}
    for d in days:
        if d.status == config.ATT_LEAVE:
            amount = Decimal(1)
        elif d.status == config.ATT_HALF and d.leave_type:
            amount = Decimal('0.5')
        else:
            continue
        key = d.leave_type or config.LEAVE_NOPAY
        taken[key] = taken.get(key, ZERO) + amount
    return taken


def fmt_minutes(minutes):
    minutes = int(minutes or 0)
    if minutes < 60:
        return f'{minutes} min'
    return f'{minutes // 60} h {minutes % 60:02d} min'
