"""Jinja filters and globals shared by every template."""

from decimal import Decimal, InvalidOperation

from harithmapos import config
from harithmapos.billing import to_decimal
from harithmapos.permissions import user_is_owner
from harithmapos import settings as app_settings
from harithmapos.textutils import format_phone
from harithmapos.timeutils import to_local, elapsed_text, utcnow

# How each service status is drawn: (key used in CSS classes, label on the
# button that moves a vehicle INTO this status).
SERVICE_STATUS_META = [
    {'id': 0, 'key': 'waiting', 'label': 'Waiting', 'action': 'Back to waiting'},
    {'id': 1, 'key': 'vacuuming', 'label': 'Vacuuming', 'action': 'Start vacuuming'},
    {'id': 2, 'key': 'washing', 'label': 'Washing', 'action': 'Start washing'},
    {'id': 3, 'key': 'polishing', 'label': 'Polishing', 'action': 'Start polishing'},
    {'id': 4, 'key': 'done', 'label': 'Done', 'action': 'Finish'},
]


def money_filter(value, places=2):
    """12500 -> '12,500.00'. None is shown as 0.00."""
    try:
        amount = to_decimal(value)
    except (InvalidOperation, ValueError, TypeError):
        return value
    return f"{amount:,.{places}f}"


def quantity_filter(value):
    """Drop pointless zeros: 2.0000 -> '2', 0.5000 -> '0.5'."""
    if value is None:
        return ''
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return value
    text = f"{amount:f}"
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text or '0'


def km_filter(value):
    """45000 -> '45,000'."""
    if value is None or value == '':
        return ''
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value


def local_datetime_filter(dt, fmt='%d %b %Y, %I:%M %p'):
    local = to_local(dt, config.APP_TIMEZONE)
    return local.strftime(fmt) if local else ''


def local_date_filter(dt, fmt='%d %b %Y'):
    return local_datetime_filter(dt, fmt)


def local_time_filter(dt, fmt='%I:%M %p'):
    return local_datetime_filter(dt, fmt).lstrip('0')


def iso_utc_filter(dt):
    """Naive UTC datetime -> ISO string with a Z, safe for JavaScript's Date()."""
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ') if dt else ''


def elapsed_filter(dt):
    return elapsed_text(dt)


def status_meta(status):
    try:
        return SERVICE_STATUS_META[int(status)]
    except (IndexError, ValueError, TypeError):
        return {'id': status, 'key': 'unknown', 'label': f"Status {status}", 'action': ''}


def register_template_helpers(app):
    app.add_template_filter(money_filter, 'money')
    app.add_template_filter(quantity_filter, 'qty')
    app.add_template_filter(km_filter, 'km')
    app.add_template_filter(local_datetime_filter, 'local_dt')
    app.add_template_filter(local_date_filter, 'local_date')
    app.add_template_filter(local_time_filter, 'local_time')
    app.add_template_filter(iso_utc_filter, 'iso_utc')
    app.add_template_filter(elapsed_filter, 'elapsed')
    app.add_template_filter(format_phone, 'phone')

    # Older names, kept so any template or branch still using them keeps working.
    app.add_template_filter(quantity_filter, 'format_quantity')
    app.add_template_filter(elapsed_filter, 'elapsed_time')
    app.add_template_filter(lambda dt: local_datetime_filter(dt, '%b-%d %I:%M %p'), 'to_ist')

    # Fixed values are Jinja globals so that imported macros can use them too.
    app.jinja_env.globals.update(
        SERVICE_STATUSES=SERVICE_STATUS_META,
        status_meta=status_meta,
        PAYMENT_METHODS=config.PAYMENT_METHOD_FORM_LIST,
        PAYMENT_METHOD_LABELS=dict(config.PAYMENT_METHOD_FORM_LIST),
        PAYMENT_DIRECTIONS=config.PAYMENT_DIRECTION_FORM_LIST,
        PAYMENT_TYPES=config.PAYMENT_TYPE_FORM_LIST,
        PAYMENT_TYPE_LABELS=dict(config.PAYMENT_TYPE_FORM_LIST),
        UOM_CHOICES=config.UOM_FORM_LIST,
        UI_THEMES=config.UI_THEME_FORM_LIST,
        CURRENCY=config.CURRENCY,
        SERVICE_STATUS_DONE=config.SERVICE_STATUS_DONE,
        ROLES=config.ROLE_FORM_LIST,
        # A function, so it also works inside imported macros.
        is_owner=user_is_owner,
        # Change this when app.css / app.js change so browsers fetch the new files.
        ASSET_VERSION='5',
    )

    @app.context_processor
    def inject_now():
        return {'now_utc': utcnow()}

    @app.context_processor
    def inject_settings():
        # Read from the Settings page, so these are worked out per request.
        return {
            'BUSINESS': app_settings.business(),
            'LOW_STOCK_THRESHOLD': app_settings.low_stock_threshold(),
        }
