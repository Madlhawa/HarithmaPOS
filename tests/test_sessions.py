"""How long a sign-in lasts: 30 days when trusted, idle sign-out on shared computers."""
from datetime import timedelta

import pytest

from harithmapos import sessions
from harithmapos import settings as app_settings
from harithmapos.models import LoginEvent
from conftest import PASSWORD


class Clock:
    def __init__(self):
        self.now = 1_800_000_000

    def time(self):
        return self.now

    def wait(self, minutes):
        self.now += minutes * 60


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(sessions.time, 'time', c.time)
    return c


def _sign_in(app, remember=False):
    client = app.test_client()
    data = {'email': 'staff@example.com', 'password': PASSWORD}
    if remember:
        data['remember'] = 'y'
    assert client.post('/app/login', data=data).status_code == 302
    return client


def _signed_in(client):
    r = client.get('/app/dashboard')
    return r.status_code == 200


def test_remember_me_lasts_30_days(app):
    assert app.config['REMEMBER_COOKIE_DURATION'] == timedelta(days=30)


def test_shared_computer_signs_out_after_an_idle_hour(app, clock):
    client = _sign_in(app)
    clock.wait(61)
    r = client.get('/app/invoice/head')
    assert r.status_code == 302 and '/app/login' in r.headers['Location']
    assert 'next=' in r.headers['Location'] and 'invoice' in r.headers['Location']
    assert not _signed_in(client)
    with app.app_context():
        assert LoginEvent.query.filter_by(outcome='timeout').count() == 1
    # The sign-in page says why.
    assert 'without activity' in client.get('/app/login').get_data(as_text=True)


def test_activity_keeps_a_shared_computer_signed_in(app, clock):
    client = _sign_in(app)
    for _ in range(4):
        clock.wait(50)
        assert _signed_in(client)


def test_live_updates_are_not_activity(app, clock):
    client = _sign_in(app)
    clock.wait(40)
    assert client.get('/app/dashboard', headers={'X-Live-Refresh': '1'}).status_code == 200
    clock.wait(10)
    assert client.get('/app/dashboard?_auto=1').status_code == 200   # the boards' automatic reload
    clock.wait(15)
    assert not _signed_in(client)


def test_keep_me_signed_in_never_idles_out(app, clock):
    client = _sign_in(app, remember=True)
    clock.wait(60 * 24 * 3)
    assert _signed_in(client)


def test_idle_time_comes_from_settings(app, clock):
    with app.app_context():
        app_settings.save({'idle_signout_minutes': 10})
    client = _sign_in(app)
    clock.wait(11)
    assert not _signed_in(client)


def test_zero_switches_idle_sign_out_off(app, clock):
    with app.app_context():
        app_settings.save({'idle_signout_minutes': 0})
    client = _sign_in(app)
    clock.wait(60 * 24)
    assert _signed_in(client)


def test_page_carries_the_idle_limit_only_on_shared_computers(app, clock):
    shared = _sign_in(app).get('/app/dashboard').get_data(as_text=True)
    assert 'data-idle-seconds="3600"' in shared
    own = _sign_in(app, remember=True).get('/app/dashboard').get_data(as_text=True)
    assert 'data-idle-seconds' not in own


def test_button_press_after_timeout_goes_to_sign_in(app, clock):
    client = _sign_in(app)
    clock.wait(61)
    r = client.post('/app/customer/quick', data={'name': 'X Y', 'number': 'ABC-1234'})
    assert r.status_code == 302 and r.headers['Location'].endswith('/app/login')
