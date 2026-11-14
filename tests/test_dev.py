"""The developer page, sign-in tracking and the monitoring collector."""
import importlib.util
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from conftest import PASSWORD, sign_in
from harithmapos import db, devtools
from harithmapos.models import LoginEvent, User, UserActivityDay

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def iso(minutes_ago=0):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


@pytest.fixture
def snapshot(tmp_path, monkeypatch):
    data = {
        'collected_at': iso(2), 'took_seconds': 3.2, 'errors': {},
        'web': {'requests_24h': 120, 'unique_ips_24h': 30, 'visitors_24h': 12, 'status_24h': {'2xx': 80, '4xx': 39, '5xx': 1},
                'suspicious_24h': 25, 'suspicious_ips_24h': 4, 'probe_kinds_24h': [['WordPress', 20], ['Path traversal', 5]],
                'top_probe_ips': [{'ip': '203.0.113.9', 'count': 20, 'kinds': ['WordPress'], 'blocked': 20, 'last': iso(30)}],
                'recent_probes': [{'time': iso(30), 'ip': '203.0.113.9', 'kind': 'WordPress', 'method': 'GET',
                                   'path': '/wp-login.php', 'status': 404, 'agent': 'zgrab'}],
                'not_found_24h': [['/favicon.ico', 3]], 'server_errors_24h': [{'time': iso(40), 'ip': '1.2.3.4', 'method': 'GET', 'path': '/app/x', 'status': 502}],
                'hourly': [{'hour': iso(60 * (23 - i)), 'ok': i, 'client_error': 1, 'suspicious': 2, 'server_error': 0} for i in range(24)],
                'daily': []},
        'web_errors': {'entries': [{'time': iso(50), 'level': 'error', 'message': 'connect() failed while connecting to upstream'}], 'tls_noise_7d': 12},
        'ssh': {'failed_24h': 300, 'attacking_ips_24h': 40, 'top_ips': [['198.51.100.7', 90]], 'top_users': [['root', 200]],
                'accepted_24h': [{'time': iso(10), 'method': 'publickey', 'user': 'root', 'ip': '192.0.2.1'}]},
        'app': {'entries': [{'time': iso(20), 'level': 'ERROR', 'source': 'harithmapos.views.invoice.routes',
                             'where': 'POST /app/invoice/head/5 user=1', 'message': 'Could not save service invoice 5',
                             'lines': ['Traceback (most recent call last):', 'ValueError: boom']}],
                'errors_24h': 1, 'warnings_24h': 0, 'errors_7d': 1, 'restarts_7d': 4, 'last_start': iso(60)},
        'deploys': [{'time': iso(15), 'action': 'deploy', 'result': 'success', 'trigger': 'github', 'from': 'aaaaaaa1',
                     'to': 'bbbbbbb2', 'subject': 'Add the developer page', 'seconds': 9, 'backup': 'x.dump',
                     'tests_passed': 160, 'tests_failed': 0, 'tests_skipped': 0, 'tests_seconds': 80.5, 'run_id': 42, 'note': ''}],
        'github': {'runs': [{'id': 42, 'name': 'Test and deploy', 'event': 'push', 'branch': 'main', 'sha': 'bbbbbbb',
                             'message': 'Add the developer page', 'actor': 'dev', 'status': 'completed', 'conclusion': 'success',
                             'started': iso(18), 'updated': iso(15), 'attempt': 1, 'url': 'https://github.com/x/y/actions/runs/42',
                             'jobs': [{'name': 'Tests', 'conclusion': 'success'}, {'name': 'Deploy to harithma.lk', 'conclusion': 'success'}]}]},
        'server': {'hostname': 'box', 'uptime_seconds': 90000, 'load': [0.1, 0.2, 0.3], 'cpus': 1,
                   'memory': {'total': 1000, 'available': 400, 'swap_total': 2000, 'swap_free': 1900},
                   'disk': {'total': 100, 'used': 40, 'free': 60},
                   'services': {'harithma-pos': 'active', 'nginx': 'active'}, 'cert_days_left': 80, 'db_size': 12000000,
                   'nightly_backup': {'name': 'a.dump', 'size': 200000, 'time': iso(600)}, 'predeploy_backups': 3,
                   'updates_pending': 0, 'security_updates': 0, 'reboot_required': False},
    }
    path = tmp_path / 'snapshot.json'
    path.write_text(json.dumps(data))
    monkeypatch.setenv('HARITHMA_MONITOR_FILE', str(path))
    monkeypatch.setenv('HARITHMA_DEVELOPER_EMAILS', 'Owner@Example.com, someone@else.lk')
    return data


def test_hidden_from_everyone_else(app, monkeypatch):
    monkeypatch.setenv('HARITHMA_DEVELOPER_EMAILS', 'someone@else.lk')
    owner = sign_in(app, 'owner@example.com')
    assert owner.get('/app/dev').status_code == 404                  # owners too: it is not an owner page
    assert '/app/dev' not in owner.get('/app/dashboard').get_data(as_text=True)
    assert sign_in(app, 'staff@example.com').get('/app/dev').status_code == 404
    assert app.test_client().get('/app/dev').status_code == 302      # signed out: to the sign-in page


def test_page_for_the_developer(app, snapshot):
    client = sign_in(app, 'owner@example.com')
    html = client.get('/app/dev').get_data(as_text=True)
    for text in ('Needs attention', 'bbbbbbb', '160 passed', 'Add the developer page', 'Sign-in activity',
                 '/wp-login.php', '203.0.113.9', 'Could not save service invoice 5', 'ValueError: boom',
                 'Successful SSH logins', 'connect() failed', 'Olivia Owner'):
        assert text in html, text
    assert '1 app error in the last 24 hours.' in html
    assert '/app/dev' in client.get('/app/dashboard').get_data(as_text=True)


def test_page_without_snapshot(app, monkeypatch, tmp_path):
    monkeypatch.setenv('HARITHMA_DEVELOPER_EMAILS', 'owner@example.com')
    monkeypatch.setenv('HARITHMA_MONITOR_FILE', str(tmp_path / 'missing.json'))
    html = sign_in(app, 'owner@example.com').get('/app/dev').get_data(as_text=True)
    assert 'The collector has not run yet' in html and 'Users' in html


def test_sign_in_events(app):
    client = app.test_client()
    client.post('/app/login', data={'email': 'owner@example.com', 'password': 'wrong'})
    client.post('/app/login', data={'email': 'nobody@example.com', 'password': 'x'})
    client.post('/app/login', data={'email': 'owner@example.com', 'password': PASSWORD})
    client.get('/app/logout')
    with app.app_context():
        outcomes = [e.outcome for e in LoginEvent.query.order_by(LoginEvent.id)]
        assert outcomes == ['bad_password', 'unknown_email', 'ok', 'logout']
        unknown = LoginEvent.query.filter_by(outcome='unknown_email').one()
        assert unknown.user_id is None and unknown.email == 'nobody@example.com'


def test_activity_is_recorded_once_a_minute(app):
    client = sign_in(app, 'staff@example.com')
    client.get('/app/dashboard')
    client.get('/app/dashboard')
    with app.app_context():
        user = User.query.filter_by(email='staff@example.com').one()
        assert user.last_seen_dttm is not None
        day = UserActivityDay.query.filter_by(user_id=user.id).one()
        assert day.requests == 1                                    # throttled
        page = devtools.users_section()
        assert page['online'] == 1 and page['active_today'] == 1


def test_alerts(app):
    old = (datetime.now(timezone.utc) - timedelta(minutes=40)).replace(tzinfo=None)
    snap = {'collected_at': old, 'errors': {'ssh': 'PermissionError'},
            'server': {'services': {'nginx': 'failed'}, 'disk': {'total': 100, 'used': 95},
                       'cert_days_left': 5, 'nightly_backup': None},
            'github': {'runs': [{'name': 'Test and deploy', 'branch': 'main', 'sha': 'abc1234', 'conclusion': 'failure',
                                 'message': 'oops', 'jobs': [{'name': 'Tests', 'conclusion': 'failure'}]}]},
            'deploys': [], 'app': {}, 'web': {}}
    with app.app_context():
        found = devtools.alerts(snap, {'failed_7d': 0})
    texts = ' '.join(t for _, t in found)
    assert found[0][0] == 'bad'
    for part in ('minutes old', 'could not read ssh', 'nginx is failed', 'Disk is 95% full', 'expires in 5 days',
                 'No nightly database backup', 'Tests failed'):
        assert part in texts, part
    assert devtools.alerts(None, None)[0][0] == 'bad'


def test_device_names():
    assert devtools.device('Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36') == 'Chrome on Android'
    assert devtools.device('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) AppleWebKit/605 Version/17.0 Mobile/15E148 Safari/604.1') == 'Safari on iPhone'
    assert devtools.device(None) == 'Unknown'


def _collector():
    spec = importlib.util.spec_from_file_location('collector', os.path.join(ROOT, 'deployment', 'monitor-collect.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('method,path,status,kind', [
    ('GET', '/.env', 404, 'Secrets and config files'),
    ('GET', '/.git/config', 404, 'Secrets and config files'),
    ('POST', '/wp-login.php', 404, 'WordPress'),
    ('GET', '/cgi-bin/luci', 404, 'Router and device exploits'),
    ('GET', '/x?id=1%20union%20select%201', 404, 'SQL injection'),
    ('GET', '/static/../../etc/passwd', 400, 'Path traversal'),
    ('', '\\x16\\x03\\x01', 400, 'Malformed or unusual request'),
    ('POST', '/app/login', 429, 'Rate limited (sign-in)'),
    ('GET', '/app/dashboard', 200, None),
    ('GET', '/invoice/eyJpbnZvaWNl', 200, None),
    ('GET', '/static/css/app.css?v=18', 200, None),
])
def test_collector_classifies_requests(method, path, status, kind):
    assert _collector().classify(method, path, status, f'{method} {path} HTTP/1.1') == kind


def test_collector_reads_log_lines():
    line = '203.0.113.9 - - [14/Nov/2026:00:13:09 +0000] "GET /SDK/webLanguage HTTP/1.1" 301 178 "-" "Mozilla/5.0"'
    m = _collector().LINE.match(line)
    assert m and m['ip'] == '203.0.113.9' and m['status'] == '301' and m['req'].startswith('GET /SDK')
