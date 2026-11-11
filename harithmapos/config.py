import os


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


class Config:
    SECRET_KEY = os.environ.get('HARITHMA_SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('HARITHMA_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_USERNAME = os.environ.get('HARITHMA_EMAIL')
    MAIL_PASSWORD = os.environ.get('HARITHMA_PASSWORD')
    MAIL_SERVER = 'smtp.mailersend.net'
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_PORT = 587

    # Invoice screens stay open on the counter PC for hours. Tie the CSRF
    # token to the login session instead of the default one-hour clock,
    # otherwise "Complete" fails on any invoice left open over an hour.
    WTF_CSRF_TIME_LIMIT = None

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    # Set HARITHMA_COOKIE_SECURE=true in .env once the site is served over HTTPS.
    SESSION_COOKIE_SECURE = _env_bool('HARITHMA_COOKIE_SECURE')
    REMEMBER_COOKIE_SECURE = _env_bool('HARITHMA_COOKIE_SECURE')


RABBIT_MQ_HOST = os.environ.get('RABBIT_MQ_HOST')
RABBIT_MQ_USERNAME = os.environ.get('RABBIT_MQ_USERNAME')
RABBIT_MQ_PASSWORD = os.environ.get('RABBIT_MQ_PASSWORD')
PRINT_QUEUE = os.environ.get('HARITHMA_PRINT_QUEUE', 'harithmaq')
NOTIFYLK_USER_ID = os.environ.get('NOTIFYLK_USER_ID')
NOTIFYLK_API_KEY = os.environ.get('NOTIFYLK_API_KEY')
NOTIFYLK_API_URL = "https://app.notify.lk/api/v1/send"
NOTIFYLK_SENDER_ID = "Harithma"

# Shown on receipts and the customer status page.
BUSINESS_NAME = os.environ.get('HARITHMA_BUSINESS_NAME', 'Harithma Service Center')
BUSINESS_ADDRESS = os.environ.get('HARITHMA_BUSINESS_ADDRESS', 'Godigamuwa road, Dunagaha')
BUSINESS_PHONE = os.environ.get('HARITHMA_BUSINESS_PHONE', '')

APP_TIMEZONE = os.environ.get('HARITHMA_TIMEZONE', 'Asia/Colombo')
CURRENCY = 'Rs.'

# Stock-tracked items at or below this quantity are flagged as running low.
LOW_STOCK_THRESHOLD = 5

# How long the status link sent to a customer by SMS keeps working.
CUSTOMER_LINK_MAX_AGE_SECONDS = 36000

SERVICE_STATUS_WAITING = 0
SERVICE_STATUS_VACUUMING = 1
SERVICE_STATUS_WASHING = 2
SERVICE_STATUS_POLISHING = 3
SERVICE_STATUS_DONE = 4

SERVICE_STATUS_LIST = [
    'Waiting',
    'Vacuuming',
    'Washing',
    'Polishing',
    'Done'
]

SERVICE_STATUS_FORM_LIST = [
    (0, 'Waiting'),
    (1, 'Vacuuming'),
    (2, 'Washing'),
    (3, 'Polishing'),
    (4, 'Done')
]

PAYMENT_METHOD_FORM_LIST = [
    ('cash', 'Cash'),
    ('card', 'Card'),
    ('bt', 'Bank Transfer'),
    ('credit', 'Credit'),
    ('qr', 'QR')
]

PAYMENT_DIRECTION_FORM_LIST = [
    ('in', 'Money in'),
    ('out', 'Money out'),
]

PAYMENT_TYPE_FORM_LIST = [
    ('general', 'General'),
    ('wage', 'Employee Wage'),
    ('withdraw', 'Owner Withdrawal'),
]

UI_THEME_FORM_LIST = [
    ('light', 'Light'),
    ('dark', 'Dark')
]

# Predefined Unit of Measure choices.
# The stored value is the first element; older values are kept so existing
# items can still be edited.
UOM_FORM_LIST = [
    ('', 'Select unit'),
    ('Piece', 'Piece'),
    ('Job', 'Job (service / labour)'),
    ('Liter', 'Liter'),
    ('Milliliter', 'Milliliter'),
    ('Kilogram', 'Kilogram'),
    ('Gram', 'Gram'),
    ('Meter', 'Meter'),
    ('Bottle', 'Bottle'),
    ('Can', 'Can'),
    ('Set', 'Set'),
    ('Pair', 'Pair'),
    ('Gallon', 'Gallon'),
    ('Quart', 'Quart'),
    ('Pound', 'Pound'),
    ('Foot', 'Foot'),
    ('Yard', 'Yard'),
    ('Square Foot', 'Square Foot'),
    ('Square Meter', 'Square Meter'),
    ('Cubic Foot', 'Cubic Foot'),
    ('Cubic Meter', 'Cubic Meter')
]
