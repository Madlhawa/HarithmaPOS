import os

class Config:
    SECRET_KEY = os.environ.get('HARITHMA_SECRET_KEY')
    SQLALCHEMY_DATABASE_URI =  os.environ.get('HARITHMA_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_USERNAME = os.environ.get('HARITHMA_EMAIL')
    MAIL_PASSWORD = os.environ.get('HARITHMA_PASSWORD')
    MAIL_SERVER = 'smtp.mailersend.net'
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_PORT = 587

SERVICE_STATUS_LIST = [
    'Waiting',
    'Vacumming',
    'Washing',
    'Drying',
    'Polishing',
    'Done'
]

SERVICE_STATUS_FORM_LIST = [
    ('0', 'Waiting'), 
    ('1', 'Vacumming'), 
    ('2', 'Washing'), 
    ('3', 'Drying'), 
    ('4', 'Polishing'), 
    ('5', 'Done')
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