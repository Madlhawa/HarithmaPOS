"""Settings an owner can change on the Settings page.

Each setting is stored as one row in the `setting` table. A setting that has
never been saved falls back to its default, which for the outside services is
the value in the environment (.env), so an existing install keeps working
until someone saves the page.

Passwords and API keys are encrypted in the database with a key derived from
HARITHMA_SECRET_KEY, so a database backup alone does not reveal them. If the
secret key changes, saved secrets can no longer be read and must be entered
again (the page says so).
"""
import base64
import hashlib
import logging
from dataclasses import dataclass, field

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app, g, has_app_context
from sqlalchemy.exc import SQLAlchemyError

from harithmapos import db, config

logger = logging.getLogger(__name__)

TEXT, INT, BOOL, SECRET, CHOICE, LONGTEXT = 'text', 'int', 'bool', 'secret', 'choice', 'longtext'

# Words that can be used in the SMS texts, with an example for the preview.
SMS_PLACEHOLDERS = {
    'customer': 'Kamal',
    'vehicle': 'CAB-1234',
    'business': 'Harithma Service Center',
    'link': 'https://example.com/invoice/abc',
}


@dataclass(frozen=True)
class Definition:
    key: str
    label: str
    group: str
    kind: str = TEXT
    default: object = ''
    hint: str = ''
    max_length: int = 255
    min_value: int = None
    max_value: int = None
    choices: tuple = field(default_factory=tuple)
    placeholders: tuple = field(default_factory=tuple)


GROUPS = [
    ('business', 'Business details', 'Shown on receipts, the customer status page and in SMS texts.'),
    ('email', 'Email', 'Used to send password reset links.'),
    ('sms', 'SMS (notify.lk)', 'Texts customers when a service starts and finishes.'),
    ('printer', 'Receipt printer (RabbitMQ)', 'Completed invoices are sent to this queue for the print agent at the counter.'),
    ('general', 'General', ''),
]

DEFINITIONS = [
    # Business
    Definition('business_name', 'Business name', 'business', default=config.BUSINESS_NAME, max_length=100),
    Definition('business_address', 'Address', 'business', default=config.BUSINESS_ADDRESS),
    Definition('business_phone', 'Phone', 'business', default=config.BUSINESS_PHONE, max_length=30),

    # Email
    Definition('mail_server', 'SMTP server', 'email', default=config.Config.MAIL_SERVER,
               hint='For example smtp.mailersend.net or smtp.gmail.com'),
    Definition('mail_port', 'Port', 'email', INT, default=config.Config.MAIL_PORT, min_value=1, max_value=65535,
               hint='Usually 587 for STARTTLS, 465 for SSL.'),
    Definition('mail_security', 'Security', 'email', CHOICE,
               default='ssl' if config.Config.MAIL_USE_SSL else ('starttls' if config.Config.MAIL_USE_TLS else 'none'),
               choices=(('starttls', 'STARTTLS'), ('ssl', 'SSL/TLS'), ('none', 'None (not recommended)'))),
    Definition('mail_username', 'Username', 'email', default=config.Config.MAIL_USERNAME or ''),
    Definition('mail_password', 'Password', 'email', SECRET, default=config.Config.MAIL_PASSWORD or ''),
    Definition('mail_sender', 'Send from', 'email', default='',
               hint='The From address. Leave empty to use the username.'),

    # SMS
    Definition('sms_enabled', 'Send SMS to customers', 'sms', BOOL, default=True),
    Definition('notifylk_user_id', 'notify.lk user ID', 'sms', default=config.NOTIFYLK_USER_ID or ''),
    Definition('notifylk_api_key', 'notify.lk API key', 'sms', SECRET, default=config.NOTIFYLK_API_KEY or ''),
    Definition('sms_sender_id', 'Sender ID', 'sms', default=config.NOTIFYLK_SENDER_ID, max_length=11,
               hint='The name customers see. It must be approved on your notify.lk account.'),
    Definition('sms_start_message', 'Service started text', 'sms', LONGTEXT, max_length=480,
               default="Hi {customer}, Your vehicle {vehicle}'s service has been started. "
                       "For more details please view: {link}",
               placeholders=('customer', 'vehicle', 'business', 'link')),
    Definition('sms_done_message', 'Service finished text', 'sms', LONGTEXT, max_length=480,
               default="Hi {customer}, Your vehicle {vehicle}'s service has been completed.",
               placeholders=('customer', 'vehicle', 'business', 'link')),

    # Printer
    Definition('printer_enabled', 'Send receipts to the printer', 'printer', BOOL, default=True),
    Definition('rabbitmq_host', 'RabbitMQ host', 'printer', default=config.RABBIT_MQ_HOST or ''),
    Definition('rabbitmq_port', 'Port', 'printer', INT, default=5672, min_value=1, max_value=65535),
    Definition('rabbitmq_username', 'Username', 'printer', default=config.RABBIT_MQ_USERNAME or ''),
    Definition('rabbitmq_password', 'Password', 'printer', SECRET, default=config.RABBIT_MQ_PASSWORD or ''),
    Definition('print_queue', 'Queue name', 'printer', default=config.PRINT_QUEUE, max_length=100),

    # General
    Definition('low_stock_threshold', 'Running low at', 'general', INT, default=config.LOW_STOCK_THRESHOLD,
               min_value=0, max_value=100000, hint='Stock items at or below this quantity are flagged as running low.'),
    Definition('customer_link_hours', 'Customer status link works for (hours)', 'general', INT,
               default=config.CUSTOMER_LINK_MAX_AGE_SECONDS // 3600, min_value=1, max_value=24 * 30,
               hint='How long the link in the "service started" SMS keeps working.'),
]

BY_KEY = {d.key: d for d in DEFINITIONS}


def definitions_for(group):
    return [d for d in DEFINITIONS if d.group == group]


# ---------------------------------------------------------------------------
# Encryption of secrets
# ---------------------------------------------------------------------------

def _fernet():
    secret = current_app.config['SECRET_KEY']
    digest = hashlib.sha256(b'harithma-settings:' + secret.encode('utf-8')).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt(value):
    return _fernet().encrypt(value.encode('utf-8')).decode('ascii')


def _decrypt(value):
    try:
        return _fernet().decrypt(value.encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError):
        return None


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def _stored():
    """All saved rows as {key: raw text}, read once per request."""
    from harithmapos.models import Setting
    if has_app_context() and '_harithma_settings' in g:
        return g._harithma_settings
    try:
        rows = {row.key: row.value for row in Setting.query.all()}
    except SQLAlchemyError:
        # For example the table is not created yet because a migration has
        # not run. Use the defaults rather than break every page.
        logger.exception("Could not read settings; using defaults")
        db.session.rollback()
        rows = {}
    if has_app_context():
        g._harithma_settings = rows
    return rows


def _convert(definition, raw):
    if definition.kind == INT:
        try:
            return int(raw)
        except (TypeError, ValueError):
            return definition.default
    if definition.kind == BOOL:
        return str(raw).lower() in ('1', 'true', 'yes', 'on')
    return raw if raw is not None else ''


def get(key):
    definition = BY_KEY[key]
    stored = _stored()
    if key not in stored:
        return definition.default
    raw = stored[key]
    if definition.kind == SECRET:
        if not raw:
            return ''
        value = _decrypt(raw)
        if value is None:
            logger.warning("Saved setting %s cannot be decrypted (was HARITHMA_SECRET_KEY changed?)", key)
            return ''
        return value
    return _convert(definition, raw)


def is_saved(key):
    return key in _stored()


def secret_unreadable(key):
    """True when a secret is saved but cannot be decrypted with the current secret key."""
    raw = _stored().get(key)
    return bool(raw) and _decrypt(raw) is None


def has_value(key):
    return bool(get(key))


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------

def save(values, user=None):
    """Save {key: python value}. Secrets are encrypted; '' clears a secret."""
    from harithmapos.models import Setting
    from harithmapos.timeutils import utcnow
    for key, value in values.items():
        definition = BY_KEY[key]
        if definition.kind == SECRET:
            raw = _encrypt(value) if value else ''
        elif definition.kind == BOOL:
            raw = 'true' if value else 'false'
        else:
            raw = '' if value is None else str(value)
        row = db.session.get(Setting, key)
        if row is None:
            row = Setting(key=key)
            db.session.add(row)
        row.value = raw
        row.update_dttm = utcnow()
        row.updated_by_id = user.id if user is not None else None
    db.session.commit()
    if has_app_context():
        g.pop('_harithma_settings', None)


# ---------------------------------------------------------------------------
# Helpers used around the app
# ---------------------------------------------------------------------------

def low_stock_threshold():
    return get('low_stock_threshold')


def customer_link_max_age_seconds():
    return get('customer_link_hours') * 3600


def business():
    return {
        'name': get('business_name'),
        'address': get('business_address'),
        'phone': get('business_phone'),
    }


class _Blank(dict):
    def __missing__(self, key):
        raise KeyError(key)


def render_sms(template, **values):
    """Fill {customer}, {vehicle}, {business}, {link} into an SMS text."""
    return template.format_map(_Blank(values))


def check_sms_template(template):
    """Return an error message if the text uses an unknown {word} or stray braces, else None."""
    try:
        render_sms(template, **SMS_PLACEHOLDERS)
    except KeyError as exc:
        names = ', '.join('{' + p + '}' for p in SMS_PLACEHOLDERS)
        return f"{{{exc.args[0]}}} is not a known word. You can use {names}."
    except (ValueError, IndexError):
        return "Curly brackets are only for the words {customer}, {vehicle}, {business} and {link}."
    return None
