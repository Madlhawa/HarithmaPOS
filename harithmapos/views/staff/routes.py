"""Staff: the daily attendance register, short leaves, salary advances and payroll. Owners only."""
import logging
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from harithmapos import db, config, payroll
from harithmapos.models import (
    Employee, AttendanceDay, ShortLeave, SalaryAdvance, PayrollRun, Payslip, Payment,
)
from harithmapos.permissions import owner_required
from harithmapos.timeutils import utcnow, local_today

logger = logging.getLogger(__name__)

staff_blueprint = Blueprint('staff_blueprint', __name__)

STATUS_LABELS = dict(config.ATTENDANCE_STATUSES)
LEAVE_LABELS = dict(config.LEAVE_TYPES)
METHODS = [m for m in config.PAYMENT_METHOD_FORM_LIST if m[0] != 'credit']


def today():
    return local_today(config.APP_TIMEZONE)


def parse_date(text, fallback):
    try:
        return date.fromisoformat(text) if text else fallback
    except ValueError:
        return fallback


def parse_month(text, fallback):
    try:
        return datetime.strptime(text, '%Y-%m').date().replace(day=1) if text else fallback
    except ValueError:
        return fallback


def parse_time(text):
    text = (text or '').strip()
    if not text:
        return None
    try:
        h, m = (int(x) for x in text.split(':')[:2])
        return time(h, m)
    except ValueError:
        return None


def parse_amount(text):
    text = (text or '').replace(',', '').strip()
    if not text:
        return Decimal('0')
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    return value if value >= 0 else None


def active_employees(extra_ids=()):
    q = Employee.query.filter((Employee.active.is_(True)) | (Employee.id.in_(list(extra_ids) or [0])))
    return q.order_by(Employee.name).all()


# ---------------------------------------------------------------------------
# The daily register
# ---------------------------------------------------------------------------

@staff_blueprint.route('/app/attendance', methods=['GET'])
@owner_required
def attendance():
    day = parse_date(request.args.get('date'), today())
    rows = {r.employee_id: r for r in AttendanceDay.query.filter_by(work_date=day).all()}
    employees = active_employees(rows.keys())
    leaves = ShortLeave.query.filter_by(work_date=day).order_by(ShortLeave.time_from).all()
    rules = payroll.Rules.from_settings()
    return render_template(
        'staff/attendance.html', title='Attendance', day=day, today=today(),
        prev_day=day - timedelta(days=1), next_day=day + timedelta(days=1), employees=employees, rows=rows,
        short_leaves=leaves, rules=rules, statuses=config.ATTENDANCE_STATUSES, leave_types=config.LEAVE_TYPES,
        fmt=payroll.fmt_minutes,
    )


@staff_blueprint.route('/app/attendance', methods=['POST'])
@owner_required
def save_attendance():
    day = parse_date(request.form.get('date'), None)
    if day is None:
        abort(400)
    if day > today():
        flash("You can't mark attendance for a day that hasn't happened yet.", category='danger')
        return redirect(url_for('staff_blueprint.attendance', date=day.isoformat()))
    rules = payroll.Rules.from_settings()
    existing = {r.employee_id: r for r in AttendanceDay.query.filter_by(work_date=day).all()}
    employees = active_employees(existing.keys())
    valid_status = {s for s, _ in config.ATTENDANCE_STATUSES}
    valid_leave = {s for s, _ in config.LEAVE_TYPES}
    problems = []
    saved = cleared = 0
    for e in employees:
        status = request.form.get(f'status_{e.id}', '')
        row = existing.get(e.id)
        if status == '':
            if row is not None:
                db.session.delete(row)
                cleared += 1
            continue
        if status not in valid_status:
            problems.append(f'{e.name}: choose a status.')
            continue
        leave_type = request.form.get(f'leave_{e.id}') or None
        if status in (config.ATT_LEAVE, config.ATT_HALF):
            if leave_type not in valid_leave:
                leave_type = config.LEAVE_NOPAY if status == config.ATT_LEAVE else None
        else:
            leave_type = None
        time_in = parse_time(request.form.get(f'in_{e.id}'))
        time_out = parse_time(request.form.get(f'out_{e.id}'))
        if status not in (config.ATT_PRESENT, config.ATT_HALF):
            time_in = time_out = None
        if status == config.ATT_PRESENT and time_in is None:
            problems.append(f'{e.name}: enter the arrival time for a present day.')
            continue
        late, early, overtime = payroll.day_minutes(status, time_in, time_out, rules)
        if row is None:
            row = AttendanceDay(employee_id=e.id, work_date=day)
            db.session.add(row)
        row.status, row.leave_type, row.time_in, row.time_out = status, leave_type, time_in, time_out
        row.late_minutes, row.early_minutes, row.overtime_minutes = late, early, overtime
        row.note = (request.form.get(f'note_{e.id}') or '').strip()[:255] or None
        row.updated_by_id = current_user.id
        row.update_dttm = utcnow()
        saved += 1
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('Could not save attendance for %s', day)
        flash('The register could not be saved. Please try again.', category='danger')
        return redirect(url_for('staff_blueprint.attendance', date=day.isoformat()))
    for p in problems:
        flash(p, category='danger')
    if saved or cleared:
        flash(f'Register for {day:%a %d %b} saved: {saved} marked' + (f', {cleared} cleared.' if cleared else '.'),
              category='success')
    return redirect(url_for('staff_blueprint.attendance', date=day.isoformat()))


@staff_blueprint.route('/app/attendance/short-leave', methods=['POST'])
@owner_required
def add_short_leave():
    day = parse_date(request.form.get('date'), None)
    employee = db.session.get(Employee, request.form.get('employee_id', type=int) or 0)
    t_from, t_to = parse_time(request.form.get('time_from')), parse_time(request.form.get('time_to'))
    if day is None or employee is None:
        abort(400)
    if t_from is None or t_to is None or t_to <= t_from:
        flash('Enter when the short leave started and ended (the end must be later).', category='danger')
    else:
        minutes = (t_to.hour * 60 + t_to.minute) - (t_from.hour * 60 + t_from.minute)
        db.session.add(ShortLeave(employee_id=employee.id, work_date=day, time_from=t_from, time_to=t_to, minutes=minutes,
                                  reason=(request.form.get('reason') or '').strip()[:255] or None,
                                  created_by_id=current_user.id))
        db.session.commit()
        flash(f'Short leave of {payroll.fmt_minutes(minutes)} recorded for {employee.name}.', category='success')
    return redirect(url_for('staff_blueprint.attendance', date=(day or today()).isoformat()) + '#short-leaves')


@staff_blueprint.route('/app/attendance/short-leave/<int:leave_id>/delete', methods=['POST'])
@owner_required
def delete_short_leave(leave_id):
    leave = db.get_or_404(ShortLeave, leave_id)
    day = leave.work_date
    db.session.delete(leave)
    db.session.commit()
    flash('Short leave removed.', category='success')
    return redirect(url_for('staff_blueprint.attendance', date=day.isoformat()) + '#short-leaves')


# ---------------------------------------------------------------------------
# The month at a glance
# ---------------------------------------------------------------------------

def month_data(month, employees=None):
    first, last = payroll.month_bounds(month)
    days = AttendanceDay.query.filter(AttendanceDay.work_date.between(first, last)).all()
    leaves = ShortLeave.query.filter(ShortLeave.work_date.between(first, last)).all()
    by_emp_days, by_emp_leaves = {}, {}
    for d in days:
        by_emp_days.setdefault(d.employee_id, []).append(d)
    for sl in leaves:
        by_emp_leaves.setdefault(sl.employee_id, []).append(sl)
    if employees is None:
        employees = active_employees(set(by_emp_days) | set(by_emp_leaves))
    now = today()
    summaries = {e.id: payroll.summarise_month(by_emp_days.get(e.id, []), by_emp_leaves.get(e.id, []), month, now,
                                               joined=e.joined_date)
                 for e in employees}
    return employees, summaries


@staff_blueprint.route('/app/attendance/month', methods=['GET'])
@owner_required
def attendance_month():
    month = parse_month(request.args.get('month'), today().replace(day=1))
    first, last = payroll.month_bounds(month)
    employees, summaries = month_data(month)
    dates = [first + timedelta(days=i) for i in range(last.day)]
    return render_template(
        'staff/attendance_month.html', title='Attendance', month=month, dates=dates, employees=employees,
        summaries=summaries, today=today(), fmt=payroll.fmt_minutes,
        prev_month=(first - timedelta(days=1)).replace(day=1), next_month=last + timedelta(days=1),
    )


# ---------------------------------------------------------------------------
# Salary advances
# ---------------------------------------------------------------------------

@staff_blueprint.route('/app/advances', methods=['GET'])
@owner_required
def advances():
    show = request.args.get('show', 'open')
    q = SalaryAdvance.query
    if show != 'all':
        q = q.filter(SalaryAdvance.payslip_id.is_(None))
    items = q.order_by(SalaryAdvance.advance_date.desc(), SalaryAdvance.id.desc()).limit(300).all()
    outstanding = {}
    for a in SalaryAdvance.query.filter(SalaryAdvance.payslip_id.is_(None)).all():
        outstanding[a.employee_id] = outstanding.get(a.employee_id, Decimal(0)) + a.amount
    employees = active_employees()
    names = {e.id: e.name for e in Employee.query.all()}
    return render_template('staff/advances.html', title='Salary advances', items=items, show=show,
                           outstanding=outstanding, employees=employees, names=names, today=today(), methods=METHODS)


@staff_blueprint.route('/app/advances', methods=['POST'])
@owner_required
def add_advance():
    employee = db.session.get(Employee, request.form.get('employee_id', type=int) or 0)
    amount = parse_amount(request.form.get('amount'))
    when = parse_date(request.form.get('advance_date'), today())
    method = request.form.get('method') or 'cash'
    if employee is None:
        flash('Choose the employee.', category='danger')
    elif not amount:
        flash('Enter the amount given.', category='danger')
    elif when > today():
        flash("The date can't be in the future.", category='danger')
    else:
        note = (request.form.get('note') or '').strip()[:255] or None
        payment = Payment(employee_id=employee.id, payment_method=method if method in dict(METHODS) else 'cash',
                          payment_direction='out', payment_amount=amount, payment_type='advance',
                          remarks=f'Salary advance: {employee.name}' + (f' ({note})' if note else ''))
        db.session.add(payment)
        db.session.flush()
        db.session.add(SalaryAdvance(employee_id=employee.id, advance_date=when, amount=amount, note=note,
                                     payment_id=payment.id, created_by_id=current_user.id))
        db.session.commit()
        flash(f'Advance of {config.CURRENCY} {amount:,.2f} to {employee.name} recorded. '
              'It will be taken back on the next payroll.', category='success')
    return redirect(request.form.get('next') or url_for('staff_blueprint.advances'))


@staff_blueprint.route('/app/advances/<int:advance_id>/delete', methods=['POST'])
@owner_required
def delete_advance(advance_id):
    adv = db.get_or_404(SalaryAdvance, advance_id)
    if adv.is_recovered:
        flash('This advance has already been taken back on a payslip, so it cannot be deleted.', category='danger')
    else:
        payment = adv.payment
        db.session.delete(adv)
        if payment is not None:
            db.session.delete(payment)
        db.session.commit()
        flash('Advance deleted, with its payment.', category='success')
    return redirect(request.form.get('next') or url_for('staff_blueprint.advances'))


# ---------------------------------------------------------------------------
# Payroll
# ---------------------------------------------------------------------------

def payroll_employees(month):
    """Who is on this month's payroll: active staff with a wage, and anyone marked in the register."""
    first, last = payroll.month_bounds(month)
    marked = {eid for (eid,) in db.session.query(AttendanceDay.employee_id)
              .filter(AttendanceDay.work_date.between(first, last)).distinct()}
    return [e for e in active_employees(marked)
            if (e.wage or e.id in marked) and (e.joined_date is None or e.joined_date <= last)]


def open_advances(month):
    """Advances given up to the end of the month that are not yet taken back, by employee."""
    _, last = payroll.month_bounds(month)
    out = {}
    for a in (SalaryAdvance.query.filter(SalaryAdvance.payslip_id.is_(None), SalaryAdvance.advance_date <= last)
              .order_by(SalaryAdvance.advance_date).all()):
        out.setdefault(a.employee_id, []).append(a)
    return out


def draft_lines(month, form=None):
    """Work out every payslip for the month. form: posted allowances / deductions / advances."""
    rules = payroll.Rules.from_settings()
    employees = payroll_employees(month)
    _, summaries = month_data(month, employees)
    advances_by_emp = open_advances(month)
    lines = []
    for e in employees:
        s = summaries[e.id]
        advs = advances_by_emp.get(e.id, [])
        if form is not None:
            allowances = parse_amount(form.get(f'allow_{e.id}'))
            other = parse_amount(form.get(f'deduct_{e.id}'))
            chosen = {int(x) for x in form.getlist(f'adv_{e.id}') if x.isdigit()}
            advs_taken = [a for a in advs if a.id in chosen]
            note = (form.get(f'note_{e.id}') or '').strip()[:255] or None
        else:
            allowances, other, advs_taken, note = Decimal(0), Decimal(0), list(advs), None
        figures = payroll.compute_pay(e.pay_type, e.wage or 0, e.epf_enabled, s, rules,
                                      allowances or 0, sum((a.amount for a in advs_taken), Decimal(0)), other or 0)
        lines.append({'employee': e, 'summary': s, 'figures': figures, 'advances': advs, 'advances_taken': advs_taken,
                      'note': note, 'bad_input': allowances is None or other is None})
    return lines, rules


@staff_blueprint.route('/app/payroll', methods=['GET'])
@owner_required
def payroll_page():
    month = parse_month(request.args.get('month'), (today().replace(day=1) - timedelta(days=1)).replace(day=1))
    run = PayrollRun.query.filter_by(month=month).first()
    first, last = payroll.month_bounds(month)
    context = dict(title='Payroll', month=month, run=run, today=today(), fmt=payroll.fmt_minutes,
                   prev_month=(first - timedelta(days=1)).replace(day=1), next_month=last + timedelta(days=1),
                   pay_labels=dict(config.PAY_TYPE_FORM_LIST), methods=METHODS)
    if run is not None:
        slips = sorted(run.payslips, key=lambda p: p.employee.name)
        return render_template('staff/payroll.html', slips=slips, **context)
    lines, rules = draft_lines(month)
    return render_template('staff/payroll.html', lines=lines, rules=rules, **context)


@staff_blueprint.route('/app/payroll/finalise', methods=['POST'])
@owner_required
def finalise_payroll():
    month = parse_month(request.form.get('month'), None)
    if month is None:
        abort(400)
    back = url_for('staff_blueprint.payroll_page', month=month.strftime('%Y-%m'))
    if month > today().replace(day=1):
        flash("A month that hasn't started can't be paid.", category='danger')
        return redirect(back)
    if PayrollRun.query.filter_by(month=month).first():
        flash('This month is already finalised.', category='warning')
        return redirect(back)
    lines, rules = draft_lines(month, request.form)
    if request.form.get('action') == 'preview':
        first, last = payroll.month_bounds(month)
        for l in lines:
            if l['bad_input']:
                flash(f"{l['employee'].name}: allowances and deductions must be amounts of 0 or more.", category='danger')
        return render_template('staff/payroll.html', title='Payroll', month=month, run=None, today=today(),
                               fmt=payroll.fmt_minutes, lines=lines, rules=rules,
                               prev_month=(first - timedelta(days=1)).replace(day=1), next_month=last + timedelta(days=1),
                               pay_labels=dict(config.PAY_TYPE_FORM_LIST), methods=METHODS)
    bad = [l['employee'].name for l in lines if l['bad_input']]
    negative = [l['employee'].name for l in lines if l['figures'].net_pay < 0]
    if bad or negative:
        for name in bad:
            flash(f'{name}: allowances and deductions must be amounts of 0 or more.', category='danger')
        for name in negative:
            flash(f'{name}: deductions are more than the pay. Untick an advance or lower the other deductions.',
                  category='danger')
        return redirect(back)
    if not lines:
        flash('Nobody to pay this month: add a wage to your employees first.', category='warning')
        return redirect(back)
    run = PayrollRun(month=month, status='final', finalised_by_id=current_user.id)
    db.session.add(run)
    db.session.flush()
    for l in lines:
        s, f, e = l['summary'], l['figures'], l['employee']
        slip = Payslip(
            payroll_run_id=run.id, employee_id=e.id, pay_type=f.pay_type, rate=f.rate,
            days_in_month=s.days_in_month, days_present=s.present, paid_leave_days=s.paid_leave, nopay_days=s.nopay,
            unmarked_days=s.unmarked, late_count=s.late_count, late_minutes=s.late_minutes,
            short_leave_count=s.short_leave_count, short_leave_minutes=s.short_leave_minutes,
            overtime_minutes=s.overtime_minutes, basic_pay=f.basic_pay, nopay_deduction=f.nopay_deduction,
            overtime_pay=f.overtime_pay, allowances=f.allowances, gross_pay=f.gross_pay, epf_employee=f.epf_employee,
            advances=f.advances, other_deductions=f.other_deductions, net_pay=f.net_pay, epf_employer=f.epf_employer,
            etf_employer=f.etf_employer, note=l['note'],
        )
        db.session.add(slip)
        db.session.flush()
        for a in l['advances_taken']:
            a.payslip_id = slip.id
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('This month was finalised by someone else just now.', category='warning')
        return redirect(back)
    flash(f'Payroll for {month:%B %Y} finalised. Pay each person below when you hand over the money.',
          category='success')
    return redirect(back)


@staff_blueprint.route('/app/payroll/<int:run_id>/reopen', methods=['POST'])
@owner_required
def reopen_payroll(run_id):
    run = db.get_or_404(PayrollRun, run_id)
    back = url_for('staff_blueprint.payroll_page', month=run.month.strftime('%Y-%m'))
    if any(p.is_paid for p in run.payslips):
        flash('Some payslips are already paid. Undo those payments first (Payments page), then reopen.',
              category='danger')
        return redirect(back)
    for p in run.payslips:
        for a in SalaryAdvance.query.filter_by(payslip_id=p.id).all():
            a.payslip_id = None
    db.session.delete(run)
    db.session.commit()
    flash(f'{run.month:%B %Y} reopened as a draft. Advances it took back are open again.', category='success')
    return redirect(back)


@staff_blueprint.route('/app/payslip/<int:slip_id>/pay', methods=['POST'])
@owner_required
def pay_payslip(slip_id):
    slip = db.get_or_404(Payslip, slip_id)
    back = url_for('staff_blueprint.payroll_page', month=slip.run.month.strftime('%Y-%m'))
    if slip.is_paid:
        flash(f'{slip.employee.name} is already paid for this month.', category='warning')
        return redirect(back)
    method = request.form.get('method') or 'cash'
    payment = Payment(employee_id=slip.employee_id, payment_method=method if method in dict(METHODS) else 'cash',
                      payment_direction='out', payment_amount=slip.net_pay, payment_type='wage',
                      remarks=f'{slip.run.month:%B %Y} salary: {slip.employee.name}')
    db.session.add(payment)
    db.session.flush()
    slip.payment_id = payment.id
    db.session.commit()
    flash(f'{slip.employee.name} paid {config.CURRENCY} {slip.net_pay:,.2f}. It is on the Payments page as money out.',
          category='success')
    return redirect(back)


@staff_blueprint.route('/app/payslip/<int:slip_id>', methods=['GET'])
@owner_required
def view_payslip(slip_id):
    slip = db.get_or_404(Payslip, slip_id)
    return render_template('staff/payslip.html', title=f'Payslip {slip.employee.name}', slip=slip,
                           fmt=payroll.fmt_minutes, pay_labels=dict(config.PAY_TYPE_FORM_LIST),
                           advance_items=SalaryAdvance.query.filter_by(payslip_id=slip.id).all())
