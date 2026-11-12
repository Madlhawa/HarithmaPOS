"""Figures for the staff report (Reports > Staff).

Definitions (shown on the page too):
- Working days = register days that are not a day off (present, half day,
  leave or absent). Days not marked are counted separately.
- Attendance rate = days worked / working days. A half day is 0.5 worked.
- Punctuality = arrivals within the grace period / all arrivals with a time.
- Jobs and revenue come from finished service invoices assigned to the
  employee, dated by when the job was opened.
- Staff cost = gross pay + employer EPF and ETF from finalised payslips.
"""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from harithmapos import config, payroll, reports
from harithmapos.models import (
    AttendanceDay, Employee, InvoiceHead, PayrollRun, Payslip, SalaryAdvance, ShortLeave,
)

ZERO = Decimal('0')
WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
ARRIVAL_BINS = [
    ('early', 'More than 10 min early'),
    ('slightly_early', 'Up to 10 min early'),
    ('grace', 'On time (within grace)'),
    ('late_30', 'Late, up to 30 min'),
    ('late_60', 'Late, 30 to 60 min'),
    ('late_more', 'Late, over an hour'),
]
LATE_BINS = {'late_30', 'late_60', 'late_more'}


def _ratio(num, den):
    return float(num) / float(den) * 100 if den else None


def _pct_change(now, before):
    if now is None or before is None or not before:
        return None
    return (float(now) - float(before)) / abs(float(before)) * 100


class EmployeeStats:
    """Everything about one employee in one period."""

    def __init__(self, employee):
        self.employee = employee
        self.worked = ZERO
        self.working_days = 0
        self.off_days = 0
        self.absent = 0
        self.leave = defaultdict(lambda: ZERO)   # leave type -> days
        self.arrivals = 0
        self.on_time = 0
        self.late_count = 0
        self.late_minutes = 0
        self.early_count = 0
        self.early_minutes = 0
        self.overtime_minutes = 0
        self.short_count = 0
        self.short_minutes = 0
        self.unmarked = 0
        self.jobs = 0
        self.revenue = ZERO
        self.job_minutes = []
        self.advances_given = ZERO
        self.advances_count = 0
        self.advances_open = ZERO

    @property
    def attendance_rate(self):
        return _ratio(self.worked, self.working_days)

    @property
    def punctuality(self):
        return _ratio(self.on_time, self.arrivals)

    @property
    def paid_leave(self):
        return sum((v for k, v in self.leave.items() if k in payroll.PAID_LEAVE), ZERO)

    @property
    def nopay_leave(self):
        return self.leave.get(config.LEAVE_NOPAY, ZERO)

    @property
    def leave_total(self):
        return sum(self.leave.values(), ZERO)

    @property
    def avg_job_minutes(self):
        return sum(self.job_minutes) / len(self.job_minutes) if self.job_minutes else None

    @property
    def revenue_per_day(self):
        return (self.revenue / self.worked) if self.worked else None

    @property
    def has_activity(self):
        return bool(self.working_days or self.off_days or self.jobs or self.advances_given or self.short_count)


def _employees(employee_id):
    q = Employee.query
    if employee_id:
        q = q.filter(Employee.id == employee_id)
    return q.order_by(Employee.name).all()


def _arrival_bin(time_in, rules):
    diff = (time_in.hour * 60 + time_in.minute) - (rules.work_start.hour * 60 + rules.work_start.minute)
    if diff < -10:
        return 'early'
    if diff <= 0:
        return 'slightly_early'
    if diff <= rules.grace:
        return 'grace'
    if diff <= 30:
        return 'late_30'
    if diff <= 60:
        return 'late_60'
    return 'late_more'


def collect(period, employee_id=None, today=None, rules=None):
    """Per-employee stats plus the day-by-day rows used by the charts."""
    today = today or reports.local_today()
    rules = rules or payroll.Rules.from_settings()
    end = min(period.end, today)
    employees = _employees(employee_id)
    stats = {e.id: EmployeeStats(e) for e in employees}
    ids = list(stats) or [0]

    days = (AttendanceDay.query.filter(AttendanceDay.employee_id.in_(ids),
                                       AttendanceDay.work_date.between(period.start, end)).all())
    marked = defaultdict(set)
    daily = {}
    arrival_bins = {k: 0 for k, _ in ARRIVAL_BINS}
    weekday_arrivals = [0] * 7
    weekday_late = [0] * 7
    for d in days:
        s = stats[d.employee_id]
        marked[d.employee_id].add(d.work_date)
        row = daily.setdefault(d.work_date, {'present': 0, 'half': 0, 'leave': 0, 'absent': 0, 'off': 0})
        row[d.status] = row.get(d.status, 0) + 1
        if d.status == config.ATT_OFF:
            s.off_days += 1
            continue
        s.working_days += 1
        if d.status == config.ATT_PRESENT:
            s.worked += 1
        elif d.status == config.ATT_HALF:
            s.worked += Decimal('0.5')
            s.leave[d.leave_type or config.LEAVE_NOPAY] += Decimal('0.5')
        elif d.status == config.ATT_LEAVE:
            s.leave[d.leave_type or config.LEAVE_NOPAY] += 1
        elif d.status == config.ATT_ABSENT:
            s.absent += 1
        if d.time_in is not None:
            s.arrivals += 1
            weekday_arrivals[d.work_date.weekday()] += 1
            arrival_bins[_arrival_bin(d.time_in, rules)] += 1
            if d.late_minutes:
                s.late_count += 1
                s.late_minutes += d.late_minutes
                weekday_late[d.work_date.weekday()] += 1
            else:
                s.on_time += 1
        if d.early_minutes:
            s.early_count += 1
            s.early_minutes += d.early_minutes
        s.overtime_minutes += d.overtime_minutes or 0

    for e in employees:
        start = max(period.start, e.joined_date) if e.joined_date else period.start
        if start <= end and e.active:
            total = (end - start).days + 1
            stats[e.id].unmarked = total - len({d for d in marked[e.id] if d >= start})

    for sl in ShortLeave.query.filter(ShortLeave.employee_id.in_(ids),
                                      ShortLeave.work_date.between(period.start, end)).all():
        stats[sl.employee_id].short_count += 1
        stats[sl.employee_id].short_minutes += sl.minutes or 0

    lo, hi = period.utc_bounds()
    jobs = (InvoiceHead.query.filter(InvoiceHead.employee_id.in_(ids),
                                     InvoiceHead.created_dttm >= lo, InvoiceHead.created_dttm < hi,
                                     InvoiceHead.service_status == config.SERVICE_STATUS_DONE).all())
    minutes = reports._minutes_each(jobs)
    for j in jobs:
        s = stats[j.employee_id]
        s.jobs += 1
        s.revenue += j.gross_price or ZERO
        if j.id in minutes:
            s.job_minutes.append(minutes[j.id])

    for a in SalaryAdvance.query.filter(SalaryAdvance.employee_id.in_(ids)).all():
        s = stats[a.employee_id]
        if period.start <= a.advance_date <= period.end:
            s.advances_given += a.amount
            s.advances_count += 1
        if a.payslip_id is None:
            s.advances_open += a.amount

    return {
        'stats': stats,
        'daily': daily,
        'arrival_bins': arrival_bins,
        'weekday_arrivals': weekday_arrivals,
        'weekday_late': weekday_late,
        'end': end,
    }


def _team(stats):
    t = EmployeeStats(None)
    for s in stats:
        t.worked += s.worked
        t.working_days += s.working_days
        t.off_days += s.off_days
        t.absent += s.absent
        for k, v in s.leave.items():
            t.leave[k] += v
        for attr in ('arrivals', 'on_time', 'late_count', 'late_minutes', 'early_count', 'early_minutes',
                     'overtime_minutes', 'short_count', 'short_minutes', 'unmarked', 'jobs', 'advances_count'):
            setattr(t, attr, getattr(t, attr) + getattr(s, attr))
        t.revenue += s.revenue
        t.job_minutes.extend(s.job_minutes)
        t.advances_given += s.advances_given
        t.advances_open += s.advances_open
    return t


def _kpis(team, cost):
    return {
        'attendance_rate': team.attendance_rate,
        'punctuality': team.punctuality,
        'worked': float(team.worked),
        'late_count': team.late_count,
        'late_minutes': team.late_minutes,
        'absent': team.absent,
        'leave_total': float(team.leave_total),
        'paid_leave': float(team.paid_leave),
        'nopay_leave': float(team.nopay_leave),
        'short_count': team.short_count,
        'short_minutes': team.short_minutes,
        'overtime_minutes': team.overtime_minutes,
        'jobs': team.jobs,
        'revenue': float(team.revenue),
        'revenue_per_day': float(team.revenue_per_day) if team.revenue_per_day is not None else None,
        'avg_job_minutes': team.avg_job_minutes,
        'advances_given': float(team.advances_given),
        'advances_open': float(team.advances_open),
        'unmarked': team.unmarked,
        'staff_cost': cost,
    }


def _months_between(first, last):
    m = first.replace(day=1)
    out = []
    while m <= last:
        out.append(m)
        m = (m.replace(day=28) + timedelta(days=4)).replace(day=1)
    return out


def payroll_by_month(end, employee_id=None, months=6):
    """Gross pay and employer EPF/ETF per month for the months ending with `end` (finalised payrolls only)."""
    last = end.replace(day=1)
    first = last
    for _ in range(months - 1):
        first = (first - timedelta(days=1)).replace(day=1)
    rows = []
    runs = {r.month: r for r in PayrollRun.query.filter(PayrollRun.month.between(first, last)).all()}
    for m in _months_between(first, last):
        run = runs.get(m)
        gross = employer = net = ZERO
        finalised = run is not None
        if run:
            for p in run.payslips:
                if employee_id and p.employee_id != employee_id:
                    continue
                gross += p.gross_pay
                employer += p.epf_employer + p.etf_employer
                net += p.net_pay
        rows.append({'date': m.isoformat(), 'label': f'{m:%B %Y}', 'short': f'{m:%b}', 'span': f'{m:%B %Y}',
                     'gross': float(gross), 'employer': float(employer), 'net': float(net), 'finalised': finalised})
    return rows


def _cost_in_period(period, employee_id=None):
    """Staff cost of finalised months that fall inside the period."""
    total = ZERO
    first = period.start.replace(day=1)
    runs = PayrollRun.query.filter(PayrollRun.month.between(first, period.end)).all()
    for run in runs:
        if run.month < period.start:  # month only partly inside the period
            continue
        for p in run.payslips:
            if employee_id and p.employee_id != employee_id:
                continue
            total += p.gross_pay + p.epf_employer + p.etf_employer
    return float(total)


def _daily_rows(daily, period, end):
    weekly = period.days > 63
    rows = []
    if end < period.start:
        return {'weekly': weekly, 'rows': rows}
    d = period.start - timedelta(days=period.start.weekday()) if weekly else period.start
    while d <= end:
        if weekly:
            span_days = [d + timedelta(days=i) for i in range(7) if period.start <= d + timedelta(days=i) <= end]
            first, last = span_days[0], span_days[-1]
            label, span, short = f'Week of {first:%d %b}', f'{first:%d %b} to {last:%d %b}', f'{first:%d %b}'
            step = 7
        else:
            span_days = [d]
            label = span = f'{d:%a %d %b}'
            short = f'{d:%d %b}'
            step = 1
        row = {'date': d.isoformat(), 'label': label, 'span': span, 'short': short,
               'present': 0, 'half': 0, 'leave': 0, 'absent': 0}
        for day in span_days:
            for k in ('present', 'half', 'leave', 'absent'):
                row[k] += daily.get(day, {}).get(k, 0)
        rows.append(row)
        d += timedelta(days=step)
    return {'weekly': weekly, 'rows': rows}


def leave_balances(employee_id=None, today=None):
    """Annual and casual leave used this calendar year, for staff still working here."""
    today = today or reports.local_today()
    rules = payroll.Rules.from_settings()
    year_start = date(today.year, 1, 1)
    q = Employee.query.filter(Employee.active.is_(True))
    if employee_id:
        q = q.filter(Employee.id == employee_id)
    employees = q.order_by(Employee.name).all()
    days = AttendanceDay.query.filter(AttendanceDay.employee_id.in_([e.id for e in employees] or [0]),
                                      AttendanceDay.work_date.between(year_start, today)).all()
    by_emp = defaultdict(list)
    for d in days:
        by_emp[d.employee_id].append(d)
    out = []
    for e in employees:
        taken = payroll.leave_taken(by_emp[e.id])
        out.append({'employee': e,
                    'annual': (float(taken.get(config.LEAVE_ANNUAL, 0)), rules.annual_days),
                    'casual': (float(taken.get(config.LEAVE_CASUAL, 0)), rules.casual_days),
                    'sick': float(taken.get(config.LEAVE_SICK, 0)),
                    'nopay': float(taken.get(config.LEAVE_NOPAY, 0))})
    return out, today.year


def staff_report(period, employee_id=None, today=None):
    today = today or reports.local_today()
    rules = payroll.Rules.from_settings()
    now = collect(period, employee_id, today, rules)
    rows = [s for s in now['stats'].values() if s.has_activity or s.employee.active]
    team = _team(rows)
    kpis = _kpis(team, _cost_in_period(period, employee_id))

    before_period = period.previous
    before_data = collect(before_period, employee_id, today, rules)
    before = _kpis(_team(before_data['stats'].values()), _cost_in_period(before_period, employee_id))
    deltas = {k: _pct_change(kpis[k], before[k]) for k in kpis if k not in ('unmarked',)}

    advances = (SalaryAdvance.query.filter(SalaryAdvance.advance_date.between(period.start, period.end))
                .order_by(SalaryAdvance.advance_date.desc()))
    if employee_id:
        advances = advances.filter(SalaryAdvance.employee_id == employee_id)

    weekday_rate = [_ratio(l, a) for l, a in zip(now['weekday_late'], now['weekday_arrivals'])]
    balances, year = leave_balances(employee_id, today)
    return {
        'period': period,
        'previous': before_period,
        'rules': rules,
        'kpis': kpis,
        'before': before,
        'deltas': deltas,
        'rows': sorted(rows, key=lambda s: (-float(s.worked), s.employee.name)),
        'team': team,
        'daily': _daily_rows(now['daily'], period, now['end']),
        'arrival_bins': [(k, label, now['arrival_bins'][k], k in LATE_BINS) for k, label in ARRIVAL_BINS],
        'arrivals_total': sum(now['arrival_bins'].values()),
        'weekday': [{'day': WEEKDAYS[i], 'arrivals': now['weekday_arrivals'][i], 'late': now['weekday_late'][i],
                     'rate': weekday_rate[i]} for i in range(7)],
        'payroll_months': payroll_by_month(min(period.end, today), employee_id),
        'advances': advances.limit(50).all(),
        'balances': balances,
        'year': year,
    }
