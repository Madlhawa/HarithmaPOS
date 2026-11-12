"""Attendance, advances and payroll. Run with: python -m pytest tests"""
from datetime import date, time, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from harithmapos import db, config, payroll
from harithmapos.models import Employee, AttendanceDay, ShortLeave, SalaryAdvance, PayrollRun, Payslip, Payment

RULES = payroll.Rules()   # 07:30-17:30, 10 min grace, overtime from 30 min, /30 days, /240 hours, 150%
OCT = date(2026, 10, 1)


# --- the rules ----------------------------------------------------------------

@pytest.mark.parametrize('status, t_in, t_out, expected', [
    ('present', time(7, 30), time(17, 30), (0, 0, 0)),
    ('present', time(7, 40), time(17, 30), (0, 0, 0)),        # inside the grace period
    ('present', time(7, 55), time(17, 30), (25, 0, 0)),       # late counts from work start
    ('present', time(7, 30), time(16, 0), (0, 90, 0)),        # left early
    ('present', time(7, 30), time(17, 50), (0, 0, 0)),        # 20 min over: below the overtime minimum
    ('present', time(7, 30), time(19, 0), (0, 0, 90)),        # overtime
    ('half', time(8, 0), time(12, 0), (30, 0, 0)),            # half days: late counts, early does not
    ('leave', None, None, (0, 0, 0)),
])
def test_day_minutes(status, t_in, t_out, expected):
    assert payroll.day_minutes(status, t_in, t_out, RULES) == expected


def row(day, status, leave=None, late=0, ot=0):
    return SimpleNamespace(work_date=date(2026, 10, day), status=status, leave_type=leave,
                           late_minutes=late, early_minutes=0, overtime_minutes=ot)


def test_month_summary_counts_each_kind_of_day():
    days = [row(1, 'present', late=20), row(2, 'present', ot=120), row(3, 'half', 'casual'), row(4, 'half'),
            row(5, 'leave', 'annual'), row(6, 'leave', 'nopay'), row(7, 'absent'), row(8, 'off')]
    leaves = [SimpleNamespace(minutes=60), SimpleNamespace(minutes=30)]
    s = payroll.summarise_month(days, leaves, OCT, today=date(2026, 11, 12))
    assert s.present == Decimal('3')                   # 2 full + 2 halves
    assert s.paid_leave == Decimal('1.5')              # half casual + annual
    assert s.nopay == Decimal('2.5')                   # half with no leave type + no-pay leave + absent
    assert s.off == 1
    assert s.unmarked == 31 - 8
    assert (s.late_count, s.late_minutes, s.overtime_minutes) == (1, 20, 120)
    assert (s.short_leave_count, s.short_leave_minutes) == (2, 90)


def test_current_month_only_counts_days_so_far():
    s = payroll.summarise_month([row(1, 'present')], [], OCT, today=date(2026, 10, 5))
    assert s.days_counted == 5 and s.unmarked == 4


def test_monthly_pay():
    s = payroll.MonthSummary(present=Decimal(25), nopay=Decimal(2), overtime_minutes=240)
    f = payroll.compute_pay('monthly', 60000, True, s, RULES, allowances=1000, advances=5000, other_deductions=500)
    assert f.basic_pay == Decimal('60000.00')
    assert f.nopay_deduction == Decimal('4000.00')     # 60000 / 30 x 2
    assert f.overtime_pay == Decimal('1500.00')        # 4 h x 60000/240 x 1.5
    assert f.gross_pay == Decimal('58500.00')          # 60000 - 4000 + 1500 + 1000
    assert f.epf_employee == Decimal('4560.00')        # 8% of 57000 (no overtime)
    assert f.epf_employer == Decimal('6840.00') and f.etf_employer == Decimal('1710.00')
    assert f.net_pay == Decimal('58500') - Decimal('4560') - 5000 - 500


def test_daily_pay_without_epf():
    s = payroll.MonthSummary(present=Decimal('20.5'), paid_leave=Decimal(1), overtime_minutes=60)
    f = payroll.compute_pay('daily', 2500, False, s, RULES)
    assert f.basic_pay == Decimal('51250.00')          # leave is not paid to daily staff
    assert f.overtime_pay == Decimal('375.00')         # 1 h x 2500/10 h x 1.5
    assert f.epf_employee == 0 and f.epf_employer == 0
    assert f.net_pay == Decimal('51625.00')


def test_nopay_never_goes_below_zero_salary():
    s = payroll.MonthSummary(nopay=Decimal(40))
    assert payroll.compute_pay('monthly', 30000, False, s, RULES).basic_pay - \
        payroll.compute_pay('monthly', 30000, False, s, RULES).nopay_deduction == 0


# --- the pages ------------------------------------------------------------------

@pytest.fixture
def team(app):
    with app.app_context():
        a = Employee(name='Ajith', wage=Decimal('60000'), pay_type='monthly', epf_enabled=True)
        b = Employee(name='Bandula', wage=Decimal('2500'), pay_type='daily', epf_enabled=False)
        db.session.add_all([a, b])
        db.session.commit()
        return {'a': a.id, 'b': b.id}


def test_staff_cannot_open_staff_pages(staff):
    for path in ['/app/attendance', '/app/attendance/month', '/app/advances', '/app/payroll']:
        assert staff.get(path).status_code == 403


def test_register_saves_and_works_out_minutes(app, owner, team):
    resp = owner.post('/app/attendance', data={
        'date': '2026-10-05',
        f"status_{team['a']}": 'present', f"in_{team['a']}": '07:55', f"out_{team['a']}": '19:00', f"note_{team['a']}": 'bus late',
        f"status_{team['b']}": 'leave', f"leave_{team['b']}": 'casual', f"in_{team['b']}": '08:00',
    })
    assert resp.status_code == 302
    with app.app_context():
        a = AttendanceDay.query.filter_by(employee_id=team['a']).one()
        b = AttendanceDay.query.filter_by(employee_id=team['b']).one()
        assert (a.late_minutes, a.overtime_minutes, a.note) == (25, 90, 'bus late')
        assert (b.status, b.leave_type, b.time_in) == ('leave', 'casual', None)
    # Setting back to "not marked" removes the row.
    owner.post('/app/attendance', data={'date': '2026-10-05', f"status_{team['a']}": '', f"status_{team['b']}": 'leave',
                                        f"leave_{team['b']}": 'casual'})
    with app.app_context():
        assert AttendanceDay.query.filter_by(employee_id=team['a']).count() == 0
    page = owner.get('/app/attendance?date=2026-10-05').get_data(as_text=True)
    assert 'Bandula' in page and 'Short leaves' in page


def test_present_needs_an_arrival_time_and_future_days_are_refused(app, owner, team):
    owner.post('/app/attendance', data={'date': '2026-10-06', f"status_{team['a']}": 'present'})
    owner.post('/app/attendance', data={'date': '2099-01-01', f"status_{team['a']}": 'absent'})
    with app.app_context():
        assert AttendanceDay.query.count() == 0


def test_short_leave(app, owner, team):
    owner.post('/app/attendance/short-leave', data={'date': '2026-10-05', 'employee_id': team['a'],
                                                     'time_from': '11:00', 'time_to': '12:15', 'reason': 'bank'})
    owner.post('/app/attendance/short-leave', data={'date': '2026-10-05', 'employee_id': team['a'],
                                                     'time_from': '12:00', 'time_to': '11:00'})  # backwards: refused
    with app.app_context():
        leave = ShortLeave.query.one()
        assert leave.minutes == 75


def test_advance_creates_and_deletes_its_payment(app, owner, team):
    owner.post('/app/advances', data={'employee_id': team['a'], 'amount': '5,000', 'advance_date': '2026-10-10',
                                      'method': 'cash'})
    with app.app_context():
        adv = SalaryAdvance.query.one()
        assert adv.amount == 5000 and adv.payment.payment_type == 'advance' and adv.payment.payment_direction == 'out'
        adv_id = adv.id
    owner.post(f'/app/advances/{adv_id}/delete')
    with app.app_context():
        assert SalaryAdvance.query.count() == 0 and Payment.query.count() == 0


def mark_october(owner, team, days=range(1, 32)):
    for d in days:
        owner.post('/app/attendance', data={
            'date': f'2026-10-{d:02d}',
            f"status_{team['a']}": 'absent' if d == 15 else 'present', f"in_{team['a']}": '07:30', f"out_{team['a']}": '17:30',
            f"status_{team['b']}": 'present', f"in_{team['b']}": '07:30', f"out_{team['b']}": '17:30',
        })


def test_payroll_from_draft_to_paid(app, owner, team):
    mark_october(owner, team)
    owner.post('/app/advances', data={'employee_id': team['a'], 'amount': '5000', 'advance_date': '2026-10-10'})
    with app.app_context():
        adv_id = SalaryAdvance.query.one().id

    draft = owner.get('/app/payroll?month=2026-10').get_data(as_text=True)
    assert 'Finalise payroll' in draft and 'Ajith' in draft and 'Bandula' in draft

    form = {'month': '2026-10', 'action': 'preview', f"allow_{team['a']}": '1000', f"adv_{team['a']}": str(adv_id)}
    preview = owner.post('/app/payroll/finalise', data=form)
    assert preview.status_code == 200 and '1,000.00' in preview.get_data(as_text=True)
    with app.app_context():
        assert PayrollRun.query.count() == 0       # preview saves nothing

    form['action'] = 'finalise'
    owner.post('/app/payroll/finalise', data=form)
    with app.app_context():
        run = PayrollRun.query.one()
        a = Payslip.query.filter_by(employee_id=team['a']).one()
        b = Payslip.query.filter_by(employee_id=team['b']).one()
        assert a.nopay_days == 1 and a.nopay_deduction == 2000           # 60000 / 30
        assert a.gross_pay == Decimal('59000.00')                         # 60000 - 2000 + 1000 allowance
        assert a.epf_employee == Decimal('4720.00') and a.advances == 5000
        assert a.net_pay == Decimal('59000') - Decimal('4720') - 5000
        assert b.basic_pay == Decimal('77500.00') and b.epf_employee == 0  # 31 days x 2500
        assert db.session.get(SalaryAdvance, adv_id).payslip_id == a.id
        slip_id, run_id = a.id, run.id

    assert owner.get(f'/app/payslip/{slip_id}').status_code == 200
    owner.post(f'/app/payslip/{slip_id}/pay', data={'method': 'bt'})
    with app.app_context():
        slip = db.session.get(Payslip, slip_id)
        assert slip.is_paid and slip.payment.payment_type == 'wage' and slip.payment.payment_amount == slip.net_pay
        payment_id = slip.payment_id

    # Paid payslips block reopening; deleting the payment makes it unpaid again, then reopening works.
    owner.post(f'/app/payroll/{run_id}/reopen')
    with app.app_context():
        assert PayrollRun.query.count() == 1
    owner.post(f'/app/payment/{payment_id}/delete')
    owner.post(f'/app/payroll/{run_id}/reopen')
    with app.app_context():
        assert PayrollRun.query.count() == 0 and Payslip.query.count() == 0
        assert db.session.get(SalaryAdvance, adv_id).payslip_id is None


def test_a_taken_back_advance_cannot_be_deleted(app, owner, team):
    owner.post('/app/advances', data={'employee_id': team['a'], 'amount': '5000', 'advance_date': '2026-10-10'})
    with app.app_context():
        adv = SalaryAdvance.query.one()
        adv_id, payment_id = adv.id, adv.payment_id
    owner.post('/app/payroll/finalise', data={'month': '2026-10', 'action': 'finalise', f"adv_{team['a']}": str(adv_id)})
    owner.post(f'/app/advances/{adv_id}/delete')
    owner.post(f'/app/payment/{payment_id}/delete')
    with app.app_context():
        assert db.session.get(SalaryAdvance, adv_id) is not None
        assert db.session.get(Payment, payment_id) is not None


def test_pay_cannot_go_negative(app, owner, team):
    owner.post('/app/payroll/finalise', data={'month': '2026-10', 'action': 'finalise',
                                              f"deduct_{team['b']}": '999999'})
    with app.app_context():
        assert PayrollRun.query.count() == 0


@pytest.mark.parametrize('path', ['/app/attendance', '/app/attendance/month', '/app/attendance/month?month=2026-10',
                                  '/app/advances', '/app/advances?show=all', '/app/payroll', '/app/payroll?month=2026-11',
                                  '/app/employee', '/app/employee?show=all'])
def test_pages_render(owner, team, path):
    assert owner.get(path).status_code == 200


def test_employee_page_shows_leave_balance(app, owner, team):
    owner.post('/app/attendance', data={'date': '2026-10-05', f"status_{team['a']}": 'leave', f"leave_{team['a']}": 'annual'})
    page = owner.get(f"/app/employee/{team['a']}").get_data(as_text=True)
    assert '1 of 14 used' in page and '13 left' in page


def test_employee_pay_settings_save(app, owner, team):
    owner.post(f"/app/employee/{team['b']}/update", data={'name': 'Bandula', 'pay_type': 'daily', 'wage': '2750',
                                                          'epf_number': 'E-123', 'epf_enabled': 'y'})
    with app.app_context():
        e = db.session.get(Employee, team['b'])
        assert (e.wage, e.epf_number, e.epf_enabled, e.active) == (Decimal('2750'), 'E-123', True, False)


def test_joiner_mid_month_is_prorated_and_not_flagged_before_joining():
    s = payroll.summarise_month([row(16, 'present')], [], OCT, today=date(2026, 11, 12), joined=date(2026, 10, 16))
    assert s.employed_days == 16 and s.unmarked == 15        # 16-31 Oct: one day marked
    f = payroll.compute_pay('monthly', 31000, False, s, RULES)
    assert f.basic_pay == Decimal('16000.00')                 # 31000 x 16/31


def test_not_on_payroll_before_joining(app, owner, team):
    with app.app_context():
        db.session.get(Employee, team['a']).joined_date = date(2026, 11, 5)
        db.session.commit()
    page = owner.get('/app/payroll?month=2026-10').get_data(as_text=True)
    assert 'Bandula' in page and 'Ajith' not in page
