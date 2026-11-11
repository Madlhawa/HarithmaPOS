"""The Settings page and the services that read it. Run with: python -m pytest tests"""
import smtplib

import pytest

from harithmapos import db, config, settings as app_settings
from harithmapos.models import Item, Setting
import harithmapos.views.utils as utils


def saved(app, key):
    with app.test_request_context():
        return app_settings.get(key)


# --- access -----------------------------------------------------------------

def test_only_owners_can_open_or_save_settings(staff, owner, app):
    assert staff.get('/app/settings').status_code == 403
    staff.post('/app/settings/business', data={'business_name': 'Hacked'})
    assert saved(app, 'business_name') != 'Hacked'
    assert owner.get('/app/settings').status_code == 200
    for path in ['/app/settings/test/email', '/app/settings/test/sms', '/app/settings/test/printer']:
        assert staff.post(path).status_code == 302  # sent back with a message, nothing sent


# --- saving -----------------------------------------------------------------

def test_unsaved_settings_fall_back_to_defaults(app):
    with app.test_request_context():
        assert app_settings.get('business_name') == config.BUSINESS_NAME
        assert app_settings.get('low_stock_threshold') == config.LOW_STOCK_THRESHOLD
        assert app_settings.get('print_queue') == config.PRINT_QUEUE


def test_save_business_details(owner, app):
    response = owner.post('/app/settings/business', data={
        'business_name': 'Harithma Kandy', 'business_address': '1 Main St', 'business_phone': '081 222 3333'})
    assert response.status_code == 302
    assert saved(app, 'business_name') == 'Harithma Kandy'
    with app.test_request_context():
        assert app_settings.business()['phone'] == '081 222 3333'


def test_low_stock_threshold_is_used(owner, app):
    with app.test_request_context():
        assert not Item.query.one().is_low_stock          # 10 in stock, threshold 5
    owner.post('/app/settings/general', data={'low_stock_threshold': '12', 'customer_link_hours': '10'})
    with app.test_request_context():
        assert Item.query.one().is_low_stock
    assert 'Engine oil' in owner.get('/app/item?stock=low').get_data(as_text=True)


def test_bad_numbers_are_refused_and_nothing_is_saved(owner, app):
    response = owner.post('/app/settings/general', data={'low_stock_threshold': 'lots', 'customer_link_hours': '10'})
    assert response.status_code == 422
    assert 'Enter a whole number.' in response.get_data(as_text=True)
    assert saved(app, 'customer_link_hours') == config.CUSTOMER_LINK_MAX_AGE_SECONDS // 3600
    response = owner.post('/app/settings/email', data={
        'mail_server': 'smtp.example.com', 'mail_port': '70000', 'mail_security': 'starttls'})
    assert response.status_code == 422


def test_sms_text_with_unknown_word_is_refused(owner, app):
    response = owner.post('/app/settings/sms', data={
        'sms_sender_id': 'Harithma', 'notifylk_user_id': '1',
        'sms_start_message': 'Hi {name}', 'sms_done_message': 'Done {vehicle}'})
    assert response.status_code == 422
    assert '{name} is not a known word' in response.get_data(as_text=True)


def test_sms_texts_are_filled_in():
    text = app_settings.render_sms('Hi {customer}, {vehicle} is ready at {business}.',
                                   customer='Kamal', vehicle='CAB-1234', business='Harithma', link='x')
    assert text == 'Hi Kamal, CAB-1234 is ready at Harithma.'


# --- secrets ----------------------------------------------------------------

def email_form(**extra):
    form = {'mail_server': 'smtp.example.com', 'mail_port': '587', 'mail_security': 'starttls',
            'mail_username': 'pos@example.com', 'mail_sender': ''}
    form.update(extra)
    return form


def test_secrets_are_encrypted_never_shown_and_kept_when_left_empty(owner, app):
    owner.post('/app/settings/email', data=email_form(mail_password='s3cret-pass'))
    with app.app_context():
        raw = db.session.get(Setting, 'mail_password').value
    assert raw and 's3cret-pass' not in raw
    assert saved(app, 'mail_password') == 's3cret-pass'
    assert 's3cret-pass' not in owner.get('/app/settings').get_data(as_text=True)

    owner.post('/app/settings/email', data=email_form(mail_password=''))
    assert saved(app, 'mail_password') == 's3cret-pass'

    owner.post('/app/settings/email', data=email_form(mail_password__clear='1'))
    assert saved(app, 'mail_password') == ''


def test_secret_saved_under_another_secret_key_is_reported(owner, app):
    owner.post('/app/settings/sms', data={'sms_enabled': 'on', 'notifylk_user_id': '1', 'notifylk_api_key': 'key-1',
                                          'sms_sender_id': 'Harithma', 'sms_start_message': 'a', 'sms_done_message': 'b'})
    app.config['SECRET_KEY'] = 'a-different-key'
    with app.test_request_context():
        assert app_settings.get('notifylk_api_key') == ''
        assert app_settings.secret_unreadable('notifylk_api_key')


# --- services use the saved settings ----------------------------------------

def sms_form(**extra):
    form = {'sms_enabled': 'on', 'notifylk_user_id': 'u-42', 'notifylk_api_key': 'k-42', 'sms_sender_id': 'HarithmaPOS',
            'sms_start_message': 'Started {vehicle}', 'sms_done_message': 'Done {vehicle}'}
    form.update(extra)
    return form


class FakeResponse:
    status_code = 200

    def json(self):
        return {'status': 'success'}


def test_sms_uses_saved_account(owner, app, monkeypatch):
    sent = {}
    monkeypatch.setattr(utils.requests, 'get', lambda url, params, timeout: sent.update(params) or FakeResponse())
    owner.post('/app/settings/sms', data=sms_form())
    with app.test_request_context():
        assert utils.send_sms('0771234567', 'hello')
    assert sent['user_id'] == 'u-42' and sent['api_key'] == 'k-42' and sent['sender_id'] == 'HarithmaPOS'
    assert sent['to'] == '94771234567'


def test_sms_switched_off_sends_nothing(owner, app, monkeypatch):
    monkeypatch.setattr(utils.requests, 'get', lambda *a, **k: pytest.fail('SMS should not be sent'))
    form = sms_form()
    del form['sms_enabled']
    owner.post('/app/settings/sms', data=form)
    with app.test_request_context():
        assert not utils.send_sms('0771234567', 'hello')
        with pytest.raises(utils.ServiceError, match='switched off'):
            utils.send_sms('0771234567', 'hello', raise_errors=True)


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=None, **kwargs):
        self.host, self.port, self.calls = host, port, []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.calls.append('starttls')

    def login(self, user, password):
        if password != 'right':
            raise smtplib.SMTPAuthenticationError(535, b'bad')
        self.calls.append(('login', user))

    def send_message(self, message):
        self.calls.append(('send', message['From'], message['To']))


def test_test_email_uses_saved_smtp_settings(owner, app, monkeypatch):
    FakeSMTP.instances = []
    monkeypatch.setattr(utils.smtplib, 'SMTP', FakeSMTP)
    owner.post('/app/settings/email', data=email_form(mail_password='right', mail_sender='shop@example.com'))
    response = owner.post('/app/settings/test/email', data={'to': 'me@example.com'}, follow_redirects=True)
    assert 'Test email sent to me@example.com' in response.get_data(as_text=True)
    smtp = FakeSMTP.instances[-1]
    assert (smtp.host, smtp.port) == ('smtp.example.com', 587)
    assert smtp.calls == ['starttls', ('login', 'pos@example.com'), ('send', 'shop@example.com', 'me@example.com')]


def test_test_email_reports_wrong_password(owner, app, monkeypatch):
    monkeypatch.setattr(utils.smtplib, 'SMTP', FakeSMTP)
    owner.post('/app/settings/email', data=email_form(mail_password='wrong'))
    response = owner.post('/app/settings/test/email', data={'to': 'me@example.com'}, follow_redirects=True)
    assert 'refused the username or password' in response.get_data(as_text=True)


def test_printer_switched_off_does_not_connect(owner, app, monkeypatch):
    monkeypatch.setattr(utils.pika, 'BlockingConnection', lambda *a, **k: pytest.fail('should not connect'))
    owner.post('/app/settings/printer', data={'rabbitmq_host': 'printer.local', 'rabbitmq_port': '5672',
                                              'rabbitmq_username': 'u', 'print_queue': 'q'})  # switch left off
    with app.test_request_context():
        assert not utils.printer_enabled()
        assert utils.send_print_invoice('{}') is False


def test_printer_uses_saved_connection(owner, app, monkeypatch):
    seen = {}

    class FakeChannel:
        def queue_declare(self, queue):
            seen['queue'] = queue

        def basic_publish(self, exchange, routing_key, body):
            seen['published'] = (routing_key, body)

    class FakeConnection:
        def __init__(self, parameters):
            seen['host'], seen['port'] = parameters.host, parameters.port

        def channel(self):
            return FakeChannel()

        def close(self):
            pass

    monkeypatch.setattr(utils.pika, 'BlockingConnection', FakeConnection)
    owner.post('/app/settings/printer', data={'printer_enabled': 'on', 'rabbitmq_host': 'printer.local',
                                              'rabbitmq_port': '5673', 'rabbitmq_username': 'u',
                                              'rabbitmq_password': 'p', 'print_queue': 'receipts'})
    with app.test_request_context():
        assert utils.send_print_invoice('{"id": 1}')
    assert seen == {'host': 'printer.local', 'port': 5673, 'queue': 'receipts', 'published': ('receipts', '{"id": 1}')}
