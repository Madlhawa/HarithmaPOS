"""Sales figures for the Reports page.

Everything is worked out in Python from the rows of one period, so the same
code runs on PostgreSQL and on the SQLite test database, and the figures on
the page always agree with each other.

Definitions (shown on the page too):
- A service invoice counts as a sale once it is Done; an item sale counts as
  soon as it has something on it. Both are dated by when they were opened.
- Revenue is what the customer owes after discounts (gross_price).
- Gross profit is revenue minus the cost of what was sold (total_cost).
- Collected is money that came in (payments in) during the period, whatever
  the invoice date.
- Outstanding is what is still owed on the period's sales.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from harithmapos import config
from harithmapos.models import (
    Customer, Employee, InvoiceDetail, InvoiceHead, InvoiceStatusLog, Item, ItemInvoiceDetail,
    ItemInvoiceHead, Payment, WashBay,
)

ZERO = Decimal('0')
LOCAL = ZoneInfo(config.APP_TIMEZONE)
UTC = ZoneInfo('UTC')
WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
HOURS = list(range(6, 21))  # 6 am to 8 pm; earlier and later arrivals fold into the edges
METHOD_LABELS = dict(config.PAYMENT_METHOD_FORM_LIST)

PRESETS = [
    ('today', 'Today'),
    ('7d', 'Last 7 days'),
    ('30d', 'Last 30 days'),
    ('month', 'This month'),
    ('last_month', 'Last month'),
    ('90d', 'Last 90 days'),
]


@dataclass(frozen=True)
class Period:
    start: date  # first local day, inclusive
    end: date    # last local day, inclusive
    key: str = 'custom'

    @property
    def days(self):
        return (self.end - self.start).days + 1

    @property
    def previous(self):
        end = self.start - timedelta(days=1)
        return Period(end - timedelta(days=self.days - 1), end, 'previous')

    def utc_bounds(self):
        """[from, to) as the naive UTC datetimes the database stores."""
        lo = datetime.combine(self.start, time.min, LOCAL).astimezone(UTC).replace(tzinfo=None)
        hi = datetime.combine(self.end + timedelta(days=1), time.min, LOCAL).astimezone(UTC).replace(tzinfo=None)
        return lo, hi

    @property
    def label(self):
        if self.start == self.end:
            return f'{self.start:%d %b %Y}'
        if self.start.year == self.end.year:
            return f'{self.start:%d %b} to {self.end:%d %b %Y}'
        return f'{self.start:%d %b %Y} to {self.end:%d %b %Y}'


def local_today():
    return datetime.now(LOCAL).date()


def period_from_args(key=None, start=None, end=None, today=None):
    """Turn the page's query string into a Period. Unknown input falls back to the last 30 days."""
    today = today or local_today()
    if key == 'custom' and start and end:
        try:
            lo, hi = date.fromisoformat(start), date.fromisoformat(end)
        except ValueError:
            lo = hi = None
        if lo and hi:
            lo, hi = min(lo, hi), max(lo, hi)
            hi = min(hi, today)
            lo = max(lo, hi - timedelta(days=366))
            return Period(lo, hi, 'custom')
    if key == 'today':
        return Period(today, today, key)
    if key == '7d':
        return Period(today - timedelta(days=6), today, key)
    if key == 'month':
        return Period(today.replace(day=1), today, key)
    if key == 'last_month':
        last = today.replace(day=1) - timedelta(days=1)
        return Period(last.replace(day=1), last, key)
    if key == '90d':
        return Period(today - timedelta(days=89), today, key)
    return Period(today - timedelta(days=29), today, '30d')


def to_local(dt):
    return dt.replace(tzinfo=UTC).astimezone(LOCAL)


def _d(value):
    return value if isinstance(value, Decimal) else Decimal(str(value or 0))


def _pct_change(now, before):
    now, before = _d(now), _d(before)
    if before == 0:
        return None
    return float((now - before) / abs(before) * 100)


# ---------------------------------------------------------------------------
# Loading one period
# ---------------------------------------------------------------------------

def _load(period):
    lo, hi = period.utc_bounds()
    services = (InvoiceHead.query
                .filter(InvoiceHead.created_dttm >= lo, InvoiceHead.created_dttm < hi)
                .filter(InvoiceHead.service_status == config.SERVICE_STATUS_DONE)
                .all())
    sales = (ItemInvoiceHead.query
             .filter(ItemInvoiceHead.created_dttm >= lo, ItemInvoiceHead.created_dttm < hi)
             .filter(ItemInvoiceHead.gross_price > 0)
             .all())
    payments_in = (Payment.query
                   .filter(Payment.created_dttm >= lo, Payment.created_dttm < hi)
                   .filter(Payment.payment_direction == 'in')
                   .all())
    return services, sales, payments_in


def _kpis(period, services, sales, payments_in, with_customers=True):
    revenue_services = sum((_d(s.gross_price) for s in services), ZERO)
    revenue_items = sum((_d(s.gross_price) for s in sales), ZERO)
    revenue = revenue_services + revenue_items
    cost = sum((_d(s.total_cost) for s in services), ZERO) + sum((_d(s.total_cost) for s in sales), ZERO)
    discounts = sum((_d(s.total_discount) for s in services), ZERO) + sum((_d(s.total_discount) for s in sales), ZERO)
    outstanding = sum((max(_d(s.gross_price) - _d(s.paid_amount), ZERO) for s in list(services) + list(sales)), ZERO)
    collected = sum((_d(p.payment_amount) for p in payments_in), ZERO)
    jobs = len(services)

    kpis = {
        'revenue': revenue,
        'revenue_services': revenue_services,
        'revenue_items': revenue_items,
        'gross_profit': revenue - cost,
        'margin_pct': float((revenue - cost) / revenue * 100) if revenue else None,
        'jobs': jobs,
        'item_sales': len(sales),
        'avg_ticket': (revenue_services / jobs) if jobs else None,
        'collected': collected,
        'outstanding': outstanding,
        'discounts': discounts,
        'avg_minutes': _avg_minutes(services),
    }
    if with_customers:
        served = {s.customer_id for s in services} | {s.customer_id for s in sales if s.customer_id}
        kpis['customers'] = len(served)
        kpis['new_customers'] = _count_new_customers(served, period)
        kpis['returning_pct'] = (float((len(served) - kpis['new_customers']) / len(served) * 100) if served else None)
    return kpis


def _done_times(services):
    """{invoice id: when it was marked Done} from the stage history."""
    ids = [s.id for s in services]
    done = {}
    for chunk in (ids[i:i + 500] for i in range(0, len(ids), 500)):
        rows = (InvoiceStatusLog.query
                .filter(InvoiceStatusLog.invoice_id.in_(chunk))
                .filter(InvoiceStatusLog.service_status == config.SERVICE_STATUS_DONE)
                .all())
        for r in rows:
            if r.invoice_id not in done or r.created_dttm < done[r.invoice_id]:
                done[r.invoice_id] = r.created_dttm
    return done


def _minutes_each(services):
    done = _done_times(services)
    out = {}
    for s in services:
        finished = done.get(s.id)
        if finished and finished > s.created_dttm:
            minutes = (finished - s.created_dttm).total_seconds() / 60
            if minutes <= 12 * 60:  # a job left open overnight would distort the average
                out[s.id] = minutes
    return out


def _avg_minutes(services):
    minutes = list(_minutes_each(services).values())
    return sum(minutes) / len(minutes) if minutes else None


def _count_new_customers(customer_ids, period):
    """Customers whose first visit ever falls inside the period."""
    if not customer_ids:
        return 0
    lo, _ = period.utc_bounds()
    ids = list(customer_ids)
    seen_before = set()
    for chunk in (ids[i:i + 500] for i in range(0, len(ids), 500)):
        seen_before |= {cid for (cid,) in InvoiceHead.query.with_entities(InvoiceHead.customer_id)
                        .filter(InvoiceHead.customer_id.in_(chunk), InvoiceHead.created_dttm < lo).distinct()}
        seen_before |= {cid for (cid,) in ItemInvoiceHead.query.with_entities(ItemInvoiceHead.customer_id)
                        .filter(ItemInvoiceHead.customer_id.in_(chunk), ItemInvoiceHead.created_dttm < lo).distinct()}
    return len(set(ids) - seen_before)


# ---------------------------------------------------------------------------
# The breakdowns
# ---------------------------------------------------------------------------

def _timeline(period, services, sales):
    """Revenue per day, or per week (starting Monday) for periods longer than nine weeks."""
    weekly = period.days > 63
    buckets = []
    if weekly:
        first = period.start - timedelta(days=period.start.weekday())
        d = first
        while d <= period.end:
            buckets.append(d)
            d += timedelta(days=7)
    else:
        buckets = [period.start + timedelta(days=i) for i in range(period.days)]
    index = {b: i for i, b in enumerate(buckets)}
    rows = [{'date': b.isoformat(), 'services': 0.0, 'sales': 0.0, 'jobs': 0} for b in buckets]

    def bucket(dt):
        day = to_local(dt).date()
        return day - timedelta(days=day.weekday()) if weekly else day

    for s in services:
        i = index.get(bucket(s.created_dttm))
        if i is not None:
            rows[i]['services'] += float(_d(s.gross_price))
            rows[i]['jobs'] += 1
    for s in sales:
        i = index.get(bucket(s.created_dttm))
        if i is not None:
            rows[i]['sales'] += float(_d(s.gross_price))
    for r, b in zip(rows, buckets):
        if weekly:
            last = min(b + timedelta(days=6), period.end)
            r['label'] = f'Week of {max(b, period.start):%d %b}'
            r['short'] = f'{max(b, period.start):%d %b}'
            r['span'] = f'{max(b, period.start):%d %b} to {last:%d %b}'
        else:
            r['label'] = f'{b:%a %d %b}'
            r['short'] = f'{b:%d %b}'
            r['span'] = r['label']
        r['services'] = round(r['services'], 2)
        r['sales'] = round(r['sales'], 2)
    return {'weekly': weekly, 'rows': rows}


def _by_item(services, sales, limit=10):
    """What earned the money: revenue and quantity per service or item, largest first."""
    totals = defaultdict(lambda: {'revenue': ZERO, 'qty': ZERO, 'profit': ZERO})
    service_ids = [s.id for s in services]
    sale_ids = [s.id for s in sales]
    for model, fk, ids in ((InvoiceDetail, InvoiceDetail.invoice_head_id, service_ids),
                           (ItemInvoiceDetail, ItemInvoiceDetail.item_invoice_head_id, sale_ids)):
        for chunk in (ids[i:i + 500] for i in range(0, len(ids), 500)):
            for line in model.query.filter(fk.in_(chunk)).all():
                t = totals[line.item_id]
                t['revenue'] += _d(line.gross_price)
                t['qty'] += _d(line.quantity)
                t['profit'] += _d(line.gross_price) - _d(line.total_cost)
    if not totals:
        return []
    items = {i.id: i for i in Item.query.filter(Item.id.in_(list(totals))).all()}
    rows = []
    for item_id, t in totals.items():
        item = items.get(item_id)
        rows.append({
            'name': item.name if item else f'Item {item_id}',
            'kind': 'Service' if item is not None and not item.tracks_stock else 'Item',
            'revenue': float(t['revenue']),
            'qty': float(t['qty']),
            'profit': float(t['profit']),
        })
    rows.sort(key=lambda r: r['revenue'], reverse=True)
    if len(rows) > limit:
        rest = rows[limit - 1:]
        rows = rows[:limit - 1] + [{
            'name': f'{len(rest)} others', 'kind': '', 'other': True,
            'revenue': sum(r['revenue'] for r in rest), 'qty': sum(r['qty'] for r in rest),
            'profit': sum(r['profit'] for r in rest),
        }]
    total = sum(r['revenue'] for r in rows) or 1
    for r in rows:
        r['share'] = r['revenue'] / total * 100
    return rows


def _by_method(payments_in):
    totals = defaultdict(lambda: ZERO)
    counts = defaultdict(int)
    for p in payments_in:
        totals[p.payment_method or 'cash'] += _d(p.payment_amount)
        counts[p.payment_method or 'cash'] += 1
    total = sum(totals.values(), ZERO)
    rows = [{'method': METHOD_LABELS.get(m, m.title()), 'amount': float(a), 'count': counts[m],
             'share': float(a / total * 100) if total else 0} for m, a in totals.items()]
    rows.sort(key=lambda r: r['amount'], reverse=True)
    return rows


def _busy_times(period):
    """Vehicles arriving, by weekday and hour (every service started, done or not)."""
    lo, hi = period.utc_bounds()
    grid = [[0] * len(HOURS) for _ in WEEKDAYS]
    rows = (InvoiceHead.query.with_entities(InvoiceHead.created_dttm)
            .filter(InvoiceHead.created_dttm >= lo, InvoiceHead.created_dttm < hi).all())
    for (created,) in rows:
        local = to_local(created)
        h = min(max(local.hour, HOURS[0]), HOURS[-1])
        grid[local.weekday()][h - HOURS[0]] += 1
    weeks = max(period.days / 7, 1)
    return {
        'weekdays': WEEKDAYS,
        'hours': [f'{h % 12 or 12}{"am" if h < 12 else "pm"}' for h in HOURS],
        'counts': grid,
        'per_week': [[round(c / weeks, 1) for c in row] for row in grid],
        'max': max((c for row in grid for c in row), default=0),
        'total': len(rows),
    }


def _by_employee(services):
    minutes = _minutes_each(services)
    data = defaultdict(lambda: {'jobs': 0, 'revenue': ZERO, 'minutes': []})
    for s in services:
        d = data[s.employee_id]
        d['jobs'] += 1
        d['revenue'] += _d(s.gross_price)
        if s.id in minutes:
            d['minutes'].append(minutes[s.id])
    names = {e.id: e.name for e in Employee.query.filter(Employee.id.in_(list(data) or [0])).all()}
    rows = [{'name': names.get(k, 'Unknown'), 'jobs': v['jobs'], 'revenue': float(v['revenue']),
             'avg_minutes': (sum(v['minutes']) / len(v['minutes'])) if v['minutes'] else None}
            for k, v in data.items()]
    rows.sort(key=lambda r: r['revenue'], reverse=True)
    return rows


def _by_bay(services):
    data = defaultdict(lambda: {'jobs': 0, 'revenue': ZERO})
    for s in services:
        data[s.washbay_id]['jobs'] += 1
        data[s.washbay_id]['revenue'] += _d(s.gross_price)
    names = {b.id: b.name for b in WashBay.query.filter(WashBay.id.in_(list(data) or [0])).all()}
    rows = [{'name': names.get(k, 'Unknown'), 'jobs': v['jobs'], 'revenue': float(v['revenue'])} for k, v in data.items()]
    rows.sort(key=lambda r: r['revenue'], reverse=True)
    return rows


def _top_customers(services, sales, limit=10):
    data = defaultdict(lambda: {'visits': 0, 'spend': ZERO, 'last': None})
    for s in list(services) + [s for s in sales if s.customer_id]:
        d = data[s.customer_id]
        d['visits'] += 1
        d['spend'] += _d(s.gross_price)
        d['last'] = max(d['last'], s.created_dttm) if d['last'] else s.created_dttm
    top = sorted(data.items(), key=lambda kv: kv[1]['spend'], reverse=True)[:limit]
    names = {c.id: c for c in Customer.query.filter(Customer.id.in_([k for k, _ in top] or [0])).all()}
    return [{'id': k, 'name': names[k].name if k in names else 'Unknown', 'contact': names[k].contact if k in names else '',
             'visits': v['visits'], 'spend': float(v['spend']), 'last': to_local(v['last']).date()} for k, v in top]


def _unpaid(services, sales, today, limit=10):
    rows = []
    for s in services:
        owed = _d(s.gross_price) - _d(s.paid_amount)
        if owed > 0:
            rows.append({'kind': 'service', 'id': s.id, 'customer': s.customer.name if s.customer else '',
                         'plate': s.vehicle.number if s.vehicle else '', 'owed': float(owed),
                         'date': to_local(s.created_dttm).date()})
    for s in sales:
        owed = _d(s.gross_price) - _d(s.paid_amount)
        if owed > 0:
            rows.append({'kind': 'sale', 'id': s.id, 'customer': s.customer.name if s.customer else 'Walk-in',
                         'plate': '', 'owed': float(owed), 'date': to_local(s.created_dttm).date()})
    for r in rows:
        r['age_days'] = (today - r['date']).days
    rows.sort(key=lambda r: r['date'])
    return rows[:limit], len(rows)


# ---------------------------------------------------------------------------
# The page
# ---------------------------------------------------------------------------

def sales_report(period, today=None):
    today = today or local_today()
    services, sales, payments_in = _load(period)
    now = _kpis(period, services, sales, payments_in)

    prev_period = period.previous
    p_services, p_sales, p_payments = _load(prev_period)
    before = _kpis(prev_period, p_services, p_sales, p_payments, with_customers=True)

    deltas = {k: _pct_change(now[k], before[k]) for k in
              ('revenue', 'gross_profit', 'jobs', 'avg_ticket', 'collected', 'outstanding', 'discounts',
               'customers', 'avg_minutes', 'item_sales')
              if now.get(k) is not None and before.get(k) is not None}
    unpaid, unpaid_count = _unpaid(services, sales, today)
    return {
        'period': period,
        'previous': prev_period,
        'kpis': now,
        'before': before,
        'deltas': deltas,
        'timeline': _timeline(period, services, sales),
        'by_item': _by_item(services, sales),
        'by_method': _by_method(payments_in),
        'busy': _busy_times(period),
        'by_employee': _by_employee(services),
        'by_bay': _by_bay(services),
        'top_customers': _top_customers(services, sales),
        'unpaid': unpaid,
        'unpaid_count': unpaid_count,
    }
