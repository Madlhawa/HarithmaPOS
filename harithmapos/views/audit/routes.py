"""The audit log page: every recorded change to prices, discounts, payments, pay, roles and settings. Owners only."""
from flask import Blueprint, render_template, request, url_for
from sqlalchemy import or_

from harithmapos.models import AuditLog, User
from harithmapos.permissions import owner_required

audit_blueprint = Blueprint('audit_blueprint', __name__)

PER_PAGE = 50
CATEGORIES = [
    ('', 'All'),
    ('prices', 'Prices'),
    ('discounts', 'Discounts'),
    ('payments', 'Payments'),
    ('deletions', 'Deletions'),
    ('staff', 'Staff and pay'),
    ('access', 'Users and settings'),
]


def link_for(row):
    """Where a row's "open" link goes, or None when that record is gone or has no page."""
    if row.action == 'deleted' and row.link_entity == row.entity:
        return None
    target = row.link_id
    if row.link_entity == 'invoice' and target:
        return url_for('invoice_blueprint.invoice_head_detail', invoice_head_id=target)
    if row.link_entity == 'item_sale' and target:
        return url_for('invoice_blueprint.item_invoice_head_detail', item_invoice_head_id=target)
    if row.link_entity == 'purchase_order' and target:
        return url_for('purchase_order_blueprint.purchase_order_head_detail', purchase_order_head_id=target)
    if row.link_entity == 'employee' and target:
        return url_for('employee_blueprint.employee_detail', employee_id=target)
    if row.link_entity == 'user' and target:
        return url_for('user_blueprint.update_user', user_id=target)
    if row.link_entity == 'item':
        return url_for('item_blueprint.item', query=row.label.split(': ', 1)[-1])
    if row.link_entity == 'setting':
        return url_for('settings_blueprint.settings')
    if row.link_entity in ('payment', 'salary_advance', 'payslip'):
        return {'payment': url_for('payment_blueprint.payment'),
                'salary_advance': url_for('staff_blueprint.advances'),
                'payslip': url_for('staff_blueprint.payroll_page')}[row.link_entity]
    return None


@audit_blueprint.route('/app/audit')
@owner_required
def audit_log():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    query = (request.args.get('query') or '').strip()
    user_id = request.args.get('user', type=int)

    rows = AuditLog.query
    if category in dict(CATEGORIES) and category:
        rows = rows.filter(AuditLog.category == category)
    if user_id:
        rows = rows.filter(AuditLog.user_id == user_id)
    if query:
        pattern = f"%{query}%"
        rows = rows.filter(or_(AuditLog.label.ilike(pattern), AuditLog.old_value.ilike(pattern),
                               AuditLog.new_value.ilike(pattern), AuditLog.field.ilike(pattern)))
    rows = rows.order_by(AuditLog.created_dttm.desc(), AuditLog.id.desc()).paginate(page=page, per_page=PER_PAGE)
    users = User.query.order_by(User.name).all()
    return render_template('audit.html', title='Audit log', rows=rows, categories=CATEGORIES,
                           category=category, query=query, user_id=user_id, users=users, link_for=link_for)
