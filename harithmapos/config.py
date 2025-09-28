import os

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

RABBIT_MQ_HOST = os.environ.get('RABBIT_MQ_HOST')
RABBIT_MQ_USERNAME = os.environ.get('RABBIT_MQ_USERNAME')
RABBIT_MQ_PASSWORD = os.environ.get('RABBIT_MQ_PASSWORD')
NOTIFYLK_USER_ID = os.environ.get('NOTIFYLK_USER_ID')
NOTIFYLK_API_KEY = os.environ.get('NOTIFYLK_API_KEY')
NOTIFYLK_API_URL = "https://app.notify.lk/api/v1/send"
NOTIFYLK_SENDER_ID = "Harithma"


SERVICE_STATUS_LIST = [
    'Waiting',
    'Vacumming',
    'Washing',
    'Polishing',
    'Done'
]

SERVICE_STATUS_FORM_LIST = [
    (0, 'Waiting'), 
    (1, 'Vacumming'), 
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
    ('in', 'Inbound'),
    ('out', 'Outbound'),
]

PAYMENT_TYPE_FORM_LIST = [
    ('general', 'Genaral'),
    ('wage', 'Employee Wage'),
    ('withdraw', 'Owner Withdrawal'),
]

UI_THEME_FORM_LIST = [
    ('light', 'Light'),
    ('dark', 'Dark')
]

# Predefined Unit of Measure choices for car wash business
UOM_FORM_LIST = [
    ('', 'Select Unit of Measure'),
    ('Piece', 'Piece'),
    ('Liter', 'Liter'),
    ('Gallon', 'Gallon'),
    ('Quart', 'Quart'),
    ('Kilogram', 'Kilogram'),
    ('Gram', 'Gram'),
    ('Pound', 'Pound'),
    ('Foot', 'Foot'),
    ('Yard', 'Yard'),
    ('Meter', 'Meter'),
    ('Square Foot', 'Square Foot'),
    ('Square Meter', 'Square Meter'),
    ('Cubic Foot', 'Cubic Foot'),
    ('Cubic Meter', 'Cubic Meter')
]