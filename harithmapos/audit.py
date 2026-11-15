"""Audit log: record every change to prices, discounts, payments, pay, roles and settings.

A SQLAlchemy hook watches every save (flush), so a change is recorded however it
is made: any page, the ledger, a CLI command. Before the save it notes the old
and new values of the watched fields; after the save (when new rows have ids) it
writes one audit_log row per change on the same connection, inside the same
transaction, so a change and its record are saved or rolled back together.
"""
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from flask import has_request_context, request
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from harithmapos import models
from harithmapos.timeutils import utcnow

logger = logging.getLogger(__name__)

MONEY, PCT, TEXT, BOOL, CHOICE = 'money', 'pct', 'text', 'bool', 'choice'


@dataclass(frozen=True)
class Watch:
    entity: str
    category: str
    fields: dict                      # field name -> (label, kind)
    on_create: bool = False
    on_delete: bool = False
    describe: object = None           # obj -> (label, link_entity, link_id)
    summary: object = None            # obj -> text for created/deleted rows
    create_if: object = None          # obj -> bool: only record the creation when this is true


def _money(value):
    if value is None or value == '':
        return ''
    try:
        return f"{Decimal(str(value)):,.2f}"
    except (InvalidOperation, ValueError):
        return str(value)


def _name(obj, rel, attr='name'):
    try:
        target = getattr(obj, rel)
        return getattr(target, attr) if target is not None else ''
    except Exception:        # a related row that is gone or cannot be loaded
        return ''


def _item_name(line):
    """The item on an invoice or order line, also for a line that is not saved yet."""
    name = _name(line, 'item')
    if name or not getattr(line, 'item_id', None):
        return name
    from sqlalchemy.orm import object_session
    session = object_session(line)
    item = session.get(models.Item, line.item_id) if session is not None else None
    return item.name if item is not None else ''


def _payment_for(p):
    if p.invoice_id:
        return f"service invoice #{p.invoice_id}", 'invoice', p.invoice_id
    if p.item_invoice_id:
        return f"item sale #{p.item_invoice_id}", 'item_sale', p.item_invoice_id
    if p.purchase_order_id:
        return f"purchase order #{p.purchase_order_id}", 'purchase_order', p.purchase_order_id
    return '', 'payment', None


def _payment_label(p):
    what, link, link_id = _payment_for(p)
    person = _name(p, 'employee') or _name(p, 'customer')
    text = f"Payment #{p.id}" + (f" for {what}" if what else '') + (f" ({person})" if person and not what else '')
    return text, link, link_id


def _payment_summary(p):
    direction = {'in': 'in', 'out': 'out'}.get(p.payment_direction, p.payment_direction or '')
    method = dict(models.config.PAYMENT_METHOD_FORM_LIST).get(p.payment_method, p.payment_method or '')
    return f"{models.config.CURRENCY} {_money(p.payment_amount)} {direction}, {method}".strip(', ')


def _line_summary(line):
    return f"{_qty(line.quantity)} × {_item_name(line)} = {_money(line.gross_price if hasattr(line, 'gross_price') else line.total_cost)}"


def _qty(value):
    try:
        text = f"{Decimal(str(value)):f}"
    except (InvalidOperation, ValueError, TypeError):
        return str(value or '')
    return (text.rstrip('0').rstrip('.') if '.' in text else text) or '0'


def _line_discount_summary(line):
    return f"{_line_summary(line)}, discount {_money(line.additional_discount)}"


def _has_line_discount(line):
    try:
        return Decimal(str(line.additional_discount or 0)) > 0
    except (InvalidOperation, ValueError):
        return False


def _head_summary(head):
    return f"total {_money(head.gross_price)}, paid {_money(head.paid_amount)}"


def _setting_label(s):
    from harithmapos import settings as app_settings
    definition = app_settings.BY_KEY.get(s.key)
    return f"Setting: {definition.label if definition else s.key}", 'setting', None


WATCHES = {
    models.Item: Watch(
        'item', 'prices',
        {'unit_price': ('Price', MONEY), 'unit_cost': ('Cost', MONEY), 'discount_pct': ('Discount %', PCT),
         'name': ('Name', TEXT)},
        on_create=True, on_delete=True,
        describe=lambda o: (f"Item: {o.name}", 'item', o.id),
        summary=lambda o: f"price {_money(o.unit_price)}, cost {_money(o.unit_cost)}"
                          + (f", discount {_qty(o.discount_pct)}%" if o.discount_pct else '')),
    models.InvoiceHead: Watch(
        'invoice', 'discounts', {'discount_amount': ('Bill discount', MONEY)},
        on_delete=True,
        describe=lambda o: (f"Service invoice #{o.id} ({_name(o, 'vehicle', 'number')})", 'invoice', o.id),
        summary=_head_summary),
    models.InvoiceDetail: Watch(
        'invoice_line', 'discounts', {'additional_discount': ('Line discount', MONEY)},
        on_create=True, create_if=_has_line_discount, on_delete=True,
        describe=lambda o: (f"Service invoice #{o.invoice_head_id}: {_item_name(o)}", 'invoice', o.invoice_head_id),
        summary=_line_summary),
    models.ItemInvoiceHead: Watch(
        'item_sale', 'discounts', {'discount_amount': ('Bill discount', MONEY)},
        on_delete=True,
        describe=lambda o: (f"Item sale #{o.id}", 'item_sale', o.id),
        summary=_head_summary),
    models.ItemInvoiceDetail: Watch(
        'item_sale_line', 'discounts', {'additional_discount': ('Line discount', MONEY)},
        on_create=True, create_if=_has_line_discount, on_delete=True,
        describe=lambda o: (f"Item sale #{o.item_invoice_head_id}: {_item_name(o)}", 'item_sale', o.item_invoice_head_id),
        summary=_line_summary),
    models.PurchaseOrderHead: Watch(
        'purchase_order', 'discounts', {'discount_pct': ('Discount %', PCT)},
        on_delete=True,
        describe=lambda o: (f"Purchase order #{o.id} ({_name(o, 'supplier')})", 'purchase_order', o.id),
        summary=_head_summary),
    models.PurchaseOrderDetail: Watch(
        'purchase_order_line', 'discounts', {},
        on_delete=True,
        describe=lambda o: (f"Purchase order #{o.purchase_order_head_id}: {_item_name(o)}", 'purchase_order', o.purchase_order_head_id),
        summary=_line_summary),
    models.Payment: Watch(
        'payment', 'payments',
        {'payment_amount': ('Amount', MONEY), 'payment_method': ('Paid by', CHOICE),
         'payment_direction': ('Direction', TEXT), 'payment_type': ('Type', TEXT),
         'invoice_id': ('Service invoice', TEXT), 'item_invoice_id': ('Item sale', TEXT),
         'purchase_order_id': ('Purchase order', TEXT), 'remarks': ('Note', TEXT)},
        on_create=True, on_delete=True, describe=_payment_label, summary=_payment_summary),
    models.Employee: Watch(
        'employee', 'staff',
        {'wage': ('Pay rate', MONEY), 'pay_type': ('Paid', TEXT), 'epf_enabled': ('EPF', BOOL), 'active': ('Active', BOOL)},
        on_create=True, on_delete=True,
        describe=lambda o: (f"Employee: {o.name}", 'employee', o.id),
        summary=lambda o: f"pay rate {_money(o.wage)} ({o.pay_type})"),
    models.SalaryAdvance: Watch(
        'salary_advance', 'staff', {'amount': ('Amount', MONEY)},
        on_create=True, on_delete=True,
        describe=lambda o: (f"Salary advance: {_name(o, 'employee')}", 'salary_advance', o.id),
        summary=lambda o: f"{models.config.CURRENCY} {_money(o.amount)}" + (f", {o.note}" if o.note else '')),
    models.Payslip: Watch(
        'payslip', 'staff', {'allowances': ('Allowances', MONEY), 'other_deductions': ('Other deductions', MONEY)},
        describe=lambda o: (f"Payslip: {_name(o, 'employee')}", 'payslip', o.id)),
    models.User: Watch(
        'user', 'access', {'role': ('Role', TEXT), 'active': ('Active', BOOL), 'email': ('Email', TEXT)},
        on_create=True, on_delete=True,
        describe=lambda o: (f"User: {o.name}", 'user', o.id),
        summary=lambda o: f"{o.role}"),
    models.Setting: Watch(
        'setting', 'access', {'value': ('Value', TEXT)}, on_create=True,
        describe=_setting_label, summary=lambda o: _setting_value(o, o.value)),
}


def _setting_value(setting, value):
    from harithmapos import settings as app_settings
    definition = app_settings.BY_KEY.get(setting.key)
    if definition is not None and definition.kind == app_settings.SECRET:
        return '(hidden)' if value else '(empty)'
    return value


def _same(old, new, kind):
    if kind in (MONEY, PCT):
        try:
            return Decimal(str(old or 0)) == Decimal(str(new or 0))
        except (InvalidOperation, ValueError):
            return str(old) == str(new)
    if kind == BOOL:
        return bool(old) == bool(new)
    return (old if old is not None else '') == (new if new is not None else '')


def _show(value, kind):
    if value is None or value == '':
        return ''
    if kind == MONEY:
        return _money(value)
    if kind == PCT:
        return _qty(value) + '%'
    if kind == BOOL:
        return 'Yes' if value else 'No'
    if kind == CHOICE:
        return dict(models.config.PAYMENT_METHOD_FORM_LIST).get(value, str(value))
    return str(value)[:255]


def _who():
    if not has_request_context():
        return None, None
    try:
        from flask_login import current_user
        user_id = current_user.id if current_user and current_user.is_authenticated else None
    except Exception:
        user_id = None
    return user_id, f"{request.method} {request.path}"[:120]


def _row(obj, watch, action, field_name=None, old='', new=''):
    try:
        label, link_entity, link_id = watch.describe(obj)
    except Exception:
        label, link_entity, link_id = f"{watch.entity} #{getattr(obj, 'id', '')}", None, None
    category = 'deletions' if action == 'deleted' else watch.category
    return {
        'category': category, 'action': action, 'entity': watch.entity,
        'entity_id': getattr(obj, 'id', None) if isinstance(getattr(obj, 'id', None), int) else None,
        'link_entity': link_entity, 'link_id': link_id, 'label': (label or '')[:200],
        'field': field_name, 'old_value': (old or '')[:255] or None, 'new_value': (new or '')[:255] or None,
    }


def _summary(obj, watch):
    try:
        return watch.summary(obj) if watch.summary else ''
    except Exception:
        return ''


def _keep_old_values():
    """Make SQLAlchemy load a watched field's saved value before it is overwritten, so the log has "from"."""
    def _noop(target, value, oldvalue, initiator):
        return value
    for cls, watch in WATCHES.items():
        for name in watch.fields:
            event.listen(getattr(cls, name), 'set', _noop, active_history=True, retval=True)


_keep_old_values()


@event.listens_for(Session, 'before_flush')
def _before_flush(session, flush_context, instances):
    pending = session.info.setdefault('audit_pending', [])
    with session.no_autoflush:
        for obj in list(session.dirty):
            watch = WATCHES.get(type(obj))
            if watch is None or not session.is_modified(obj, include_collections=False):
                continue
            state = inspect(obj)
            for name, (label, kind) in watch.fields.items():
                history = state.attrs[name].history
                if not history.has_changes():
                    continue
                old = history.deleted[0] if history.deleted else None
                new = history.added[0] if history.added else None
                if _same(old, new, kind):
                    continue
                if watch.entity == 'setting':
                    pending.append(('row', _row(obj, watch, 'changed', label,
                                                _setting_value(obj, old), _setting_value(obj, new))))
                else:
                    pending.append(('row', _row(obj, watch, 'changed', label, _show(old, kind), _show(new, kind))))
        for obj in list(session.deleted):
            watch = WATCHES.get(type(obj))
            if watch is not None and watch.on_delete:
                pending.append(('row', _row(obj, watch, 'deleted', old=_summary(obj, watch))))
        for obj in list(session.new):
            watch = WATCHES.get(type(obj))
            if watch is not None and watch.on_create and (watch.create_if is None or watch.create_if(obj)):
                pending.append(('new', obj))       # its id is known after the flush


@event.listens_for(Session, 'after_flush')
def _after_flush(session, flush_context):
    pending = session.info.pop('audit_pending', None)
    if not pending:
        return
    user_id, path = _who()
    rows = []
    with session.no_autoflush:
        for kind, payload in pending:
            if kind == 'new':
                watch = WATCHES[type(payload)]
                text = _line_discount_summary(payload) if watch.create_if is _has_line_discount else _summary(payload, watch)
                payload = _row(payload, watch, 'created', new=text)
            payload.update(user_id=user_id, path=path, created_dttm=utcnow())
            rows.append(payload)
    # A savepoint, so that if the record cannot be written the real change still goes through.
    connection = session.connection()
    savepoint = connection.begin_nested()
    try:
        connection.execute(models.AuditLog.__table__.insert(), rows)
        savepoint.commit()
    except Exception:
        savepoint.rollback()
        logger.exception("Could not write %d audit log row(s)", len(rows))


@event.listens_for(Session, 'after_rollback')
def _after_rollback(session):
    session.info.pop('audit_pending', None)
