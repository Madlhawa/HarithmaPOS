"""The staff report. Run with: python -m pytest tests"""
from datetime import date, time, timedelta
from decimal import Decimal

import pytest

from harithmapos import db, config, payroll, reports, staff_reports
from harithmapos.models import (
    AttendanceDay, Customer, Employee, InvoiceHead, InvoiceStatusLog, SalaryAdvance, ShortLeave, Vehicle, WashBay,
)

TODAY = date(2026, 11, 12)
OCT = reports.Period(date(2026, 10, 1), date(2026, 10, 10))
RULES = payroll.Rules()


def at(day, hour, minute=0):
    return reports.datetime.combine(day, time(hour, minute), reports.LOCAL).astimezone(reports.UTC).replace(tzinfo=None)


@pytest.fixture
def crew(app):
    """Two people over 1-10 October 2026, plus one finished job each."""
    with app.app_context():
        a = Employee(name='Ajith', wage=60000, active=True)
        b = Employee(name='Bandula', wage=2500, pay_type='daily', active=True, joined_date=date(2026, 9, 1))
        bay = WashBay(name='Bay 1')
        cust = Customer(name='Kamal')
        db.session.add_all([a, b, bay, cust])
        db.session.flush()
        veh = Vehicle(number='CAB-1', owner_id=cust.id)
        db.session.add(veh)
        db.session.flush()

        def mark(emp, day, status, t_in=None, t_out=None, leave=None):
            late, early, ot = payroll.day_minutes(status, t_in, t_out, RULES)
            db.session.add(AttendanceDay(employee_id=emp.id, work_date=date(2026, 10, day), status=status,
                                         leave_type=leave, time_in=t_in, time_out=t_out, late_minutes=late,
                                         early_minutes=early, overtime_minutes=ot))

        # Ajith: 8 days present (2 late, 1 with overtime), 1 annual leave, 1 day off.
        for d in range(1, 9):
            arrive = time(8, 0) if d in (2, 5) else time(7, 25)
            leave_at = time(19, 0) if d == 3 else time(17, 30)
            mark(a, d, 'present', arrive, leave_at)
        mark(a, 9, 'leave', leave='annual')
        mark(a, 10, 'off')
        # Bandula: 6 present on time, 1 half day (casual), 1 absent; days 9-10 not marked.
        for d in range(1, 7):
            mark(b, d, 'present', time(7, 30), time(17, 30))
        mark(b, 7, 'half', time(7, 30), time(12, 30), leave='casual')
        mark(b, 8, 'absent')
        db.session.add(ShortLeave(employee_id=a.id, work_date=date(2026, 10, 4), time_from=time(11, 0),
                                  time_to=time(12, 0), minutes=60))
        db.session.add(SalaryAdvance(employee_id=a.id, advance_date=date(2026, 10, 6), amount=Decimal('5000')))
        for emp, price in ((a, 3000), (b, 1500)):
            inv = InvoiceHead(customer_id=cust.id, vehicle_id=veh.id, washbay_id=bay.id, employee_id=emp.id,
                              service_status=config.SERVICE_STATUS_DONE, created_dttm=at(date(2026, 10, 2), 9),
                              gross_price=price, total_cost=0)
            db.session.add(inv)
            db.session.flush()
            db.session.add(InvoiceStatusLog(invoice_id=inv.id, service_status=4, employee_id=emp.id,
                                            created_dttm=at(date(2026, 10, 2), 10)))
        db.session.commit()
        return {'a': a.id, 'b': b.id}


def test_per_employee_figures(app, crew):
    with app.app_context():
        r = staff_reports.staff_report(OCT, today=TODAY)
        rows = {s.employee.name: s for s in r['rows']}
        a, b = rows['Ajith'], rows['Bandula']
        assert (a.working_days, float(a.worked), a.off_days) == (9, 8.0, 1)       # day off not a working day
        assert round(a.attendance_rate) == round(8 / 9 * 100)
        assert (a.arrivals, a.on_time, a.late_count, a.late_minutes) == (8, 6, 2, 60)
        assert a.punctuality == 75
        assert a.overtime_minutes == 90 and a.short_count == 1 and a.short_minutes == 60
        assert float(a.paid_leave) == 1 and a.advances_given == 5000 and a.advances_open == 5000
        assert (a.jobs, a.revenue, a.avg_job_minutes) == (1, 3000, 60)
        assert a.unmarked == 0
        assert float(b.worked) == 6.5 and b.working_days == 8 and b.absent == 1
        assert float(b.leave_total) == 0.5 and b.unmarked == 2                      # 9-10 Oct not marked
        assert b.revenue_per_day == Decimal(1500) / Decimal('6.5')


def test_team_kpis_and_charts(app, crew):
    with app.app_context():
        r = staff_reports.staff_report(OCT, today=TODAY)
        k = r['kpis']
        assert k['late_count'] == 2 and k['absent'] == 1 and k['jobs'] == 2 and k['revenue'] == 4500
        assert round(k['attendance_rate']) == round(14.5 / 17 * 100)
        assert k['unmarked'] == 2
        day1 = r['daily']['rows'][0]
        assert (day1['present'], day1['absent']) == (2, 0)
        bins = {key: count for key, _, count, _ in r['arrival_bins']}
        assert bins['late_30'] == 2 and bins['slightly_early'] == 6 + 7          # 7:25 counts as up to 10 min early
        tue = r['weekday'][date(2026, 10, 6).weekday()]
        assert tue['arrivals'] == 2


def test_one_employee(app, crew):
    with app.app_context():
        r = staff_reports.staff_report(OCT, employee_id=crew['b'], today=TODAY)
        assert [s.employee.name for s in r['rows']] == ['Bandula']
        assert r['kpis']['advances_given'] == 0


def test_staff_cannot_open_the_report(staff):
    assert staff.get('/app/reports/staff').status_code == 403


@pytest.mark.parametrize('query', ['', '?range=today', '?range=7d', '?range=month', '?range=last_month', '?range=90d',
                                   '?range=custom&from=2026-10-01&to=2026-10-10',
                                   '?range=custom&from=2026-10-01&to=2026-10-10&employee=999'])
def test_report_renders(owner, crew, query):
    assert owner.get('/app/reports/staff' + query).status_code == 200


def test_report_shows_the_figures(owner, crew):
    html = owner.get('/app/reports/staff?range=custom&from=2026-10-01&to=2026-10-10').get_data(as_text=True)
    assert 'Ajith' in html and 'Bandula' in html and '75%' in html and '2 not marked' in html
    one = owner.get(f"/app/reports/staff?range=custom&from=2026-10-01&to=2026-10-10&employee={crew['a']}").get_data(as_text=True)
    assert 'Staff report: Ajith' in one


def test_sales_report_still_renders(owner):
    assert 'data-stacked="report-timeline"' in owner.get('/app/reports/sales').get_data(as_text=True)


def test_menu_has_both_reports_for_owners(owner):
    html = owner.get('/app/dashboard').get_data(as_text=True)
    assert '/app/reports/sales' in html and '/app/reports/staff' in html
