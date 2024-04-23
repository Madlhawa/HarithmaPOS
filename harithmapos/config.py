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