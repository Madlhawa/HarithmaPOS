"""Data for the developer page: the collector's snapshot plus who uses the app.

The snapshot (deployment/monitor-collect.py, run by root from cron every five
minutes) holds what the app cannot read itself: web server and SSH logs, the
app's journal, deploy history, GitHub Actions and server health.
"""
import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

from flask_login import current_user
from sqlalchemy import func

from harithmapos import config, db
from harithmapos.models import LoginEvent, User, UserActivityDay
from harithmapos.timeutils import local_today, to_local, utcnow

DEFAULT_SNAPSHOT = '/var/lib/harithma-monitor/snapshot.json'
STALE_AFTER = timedelta(minutes=15)
ONLINE_WITHIN = timedelta(minutes=5)
TIME_KEYS = {'time', 'last', 'started', 'updated', 'completed', 'collected_at', 'last_start', 'hour'}
OUTCOMES = {
    'ok': ('Signed in', 'good'),
    'logout': ('Signed out', 'muted'),
    'bad_password': ('Wrong password', 'bad'),
    'unknown_email': ('Unknown email', 'bad'),
    'switched_off': ('Account switched off', 'warn'),
}


def developer_emails():
    raw = os.environ.get('HARITHMA_DEVELOPER_EMAILS', '')
    return {e.strip().lower() for e in raw.split(',') if e.strip()}


def user_is_developer(user=None):
    """Developers are listed by email in HARITHMA_DEVELOPER_EMAILS on the server.
    It cannot be granted from inside the app, not even by an owner."""
    user = user or current_user
    try:
        return bool(user and user.is_authenticated and user.is_active
                    and user.email and user.email.lower() in developer_emails())
    except Exception:
        return False


def _parse_time(value):
    if not isinstance(value, str) or len(value) < 16:
        return value
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return value
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _times(node):
    """Turn ISO strings under time-like keys into naive UTC datetimes (what the filters expect)."""
    if isinstance(node, dict):
        return {k: (_parse_time(v) if k in TIME_KEYS else _times(v)) for k, v in node.items()}
    if isinstance(node, list):
        return [_times(v) for v in node]
    return node


def load_snapshot(path=None):
    path = path or os.environ.get('HARITHMA_MONITOR_FILE', DEFAULT_SNAPSHOT)
    try:
        with open(path) as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return None, 'The collector has not run yet (no snapshot file).'
    except PermissionError:
        return None, 'The app cannot read the snapshot file (check its group is harithma).'
    except (OSError, ValueError) as exc:
        return None, f'The snapshot file could not be read: {exc.__class__.__name__}.'
    return _times(data), None


def device(agent):
    """A short, readable name for a browser user-agent."""
    if not agent:
        return 'Unknown'
    a = agent.lower()
    os_name = ('Android' if 'android' in a else 'iPhone' if 'iphone' in a else 'iPad' if 'ipad' in a
               else 'Windows' if 'windows' in a else 'Mac' if 'mac os' in a else 'Linux' if 'linux' in a else '')
    browser = ('Edge' if 'edg/' in a else 'Samsung' if 'samsungbrowser' in a else 'Chrome' if 'chrome' in a
               else 'Firefox' if 'firefox' in a else 'Safari' if 'safari' in a else
               'curl' if 'curl' in a else 'Python' if 'python' in a else agent.split('/')[0][:20])
    return f'{browser} on {os_name}' if os_name else browser


def users_section(today=None):
    now = utcnow()
    today = today or local_today(config.APP_TIMEZONE)
    week_ago = now - timedelta(days=7)

    users = User.query.order_by(User.name).all()
    events_7d = LoginEvent.query.filter(LoginEvent.created_dttm >= week_ago).all()
    ok_by_user = Counter(e.user_id for e in events_7d if e.outcome == 'ok')
    bad_by_user = Counter(e.user_id for e in events_7d if e.outcome in ('bad_password', 'switched_off') and e.user_id)
    last_ip = {}
    for e in sorted(events_7d, key=lambda e: e.created_dttm):
        if e.outcome == 'ok':
            last_ip[e.user_id] = (e.ip, device(e.user_agent))

    rows = []
    for u in users:
        seen = u.last_seen_dttm
        rows.append({
            'user': u, 'last_seen': seen,
            'online': bool(seen and now - seen <= ONLINE_WITHIN),
            'today': bool(seen and to_local(seen, config.APP_TIMEZONE).date() == today),
            'sign_ins_7d': ok_by_user.get(u.id, 0),
            'failed_7d': bad_by_user.get(u.id, 0),
            'where': last_ip.get(u.id),
        })
    rows.sort(key=lambda r: (not r['online'], r['last_seen'] is None, -(r['last_seen'] or datetime.min).timestamp() if r['last_seen'] else 0))

    failed = [e for e in events_7d if e.outcome in ('bad_password', 'unknown_email', 'switched_off')]
    failed_ips = Counter(e.ip for e in failed).most_common(8)
    failed_emails = Counter((e.email or '').lower() for e in failed).most_common(8)

    start = today - timedelta(days=29)
    counts = dict(db.session.query(UserActivityDay.day, func.count(UserActivityDay.id))
                  .filter(UserActivityDay.day >= start).group_by(UserActivityDay.day).all())
    days = []
    for i in range(30):
        d = start + timedelta(days=i)
        days.append({'label': f'{d:%a %d %b}', 'span': f'{d:%a %d %b}', 'short': f'{d:%d %b}',
                     'users': counts.get(d, 0)})

    recent = (LoginEvent.query.order_by(LoginEvent.created_dttm.desc()).limit(40).all())
    return {
        'rows': rows,
        'online': sum(1 for r in rows if r['online']),
        'active_today': sum(1 for r in rows if r['today']),
        'sign_ins_today': sum(1 for e in events_7d if e.outcome == 'ok'
                              and to_local(e.created_dttm, config.APP_TIMEZONE).date() == today),
        'failed_7d': len(failed),
        'failed_ips': failed_ips,
        'failed_emails': failed_emails,
        'unique_30d': len({uid for (uid,) in db.session.query(UserActivityDay.user_id)
                           .filter(UserActivityDay.day >= start).distinct()}),
        'chart': {'rows': days},
        'recent': [{'event': e, 'label': OUTCOMES.get(e.outcome, (e.outcome, 'muted'))[0],
                    'tone': OUTCOMES.get(e.outcome, (e.outcome, 'muted'))[1], 'device': device(e.user_agent)}
                   for e in recent],
    }


def _hour_rows(hourly):
    rows = []
    for h in hourly or []:
        when = h.get('hour')
        local = to_local(when, config.APP_TIMEZONE) if isinstance(when, datetime) else None
        label = f'{local:%a %H:00}' if local else str(when)
        rows.append({'label': label, 'span': label, 'short': f'{local:%H:00}' if local else '',
                     'ok': h.get('ok', 0), 'client_error': h.get('client_error', 0),
                     'suspicious': h.get('suspicious', 0), 'server_error': h.get('server_error', 0)})
    return rows


def alerts(snap, users, now=None):
    """Things worth a look, most serious first: (level, text)."""
    now = now or utcnow()
    out = []
    if snap is None:
        return [('bad', 'No monitoring data: the collector is not running.')]
    collected = snap.get('collected_at')
    if isinstance(collected, datetime) and now - collected > STALE_AFTER:
        out.append(('bad', f'Monitoring data is {int((now - collected).total_seconds() // 60)} minutes old: check the cron job.'))
    for name, err in (snap.get('errors') or {}).items():
        out.append(('warn', f'The collector could not read {name}: {err}'))

    srv = snap.get('server') or {}
    for name, state in (srv.get('services') or {}).items():
        if state != 'active':
            out.append(('bad', f'Service {name} is {state}.'))
    disk = srv.get('disk') or {}
    if disk.get('total') and disk['used'] / disk['total'] > 0.85:
        out.append(('warn', f"Disk is {disk['used'] / disk['total']:.0%} full."))
    mem = srv.get('memory') or {}
    if mem.get('total') and mem.get('available') is not None and mem['available'] / mem['total'] < 0.10:
        out.append(('warn', 'Less than 10% of memory is free.'))
    days = srv.get('cert_days_left')
    if days is not None and days < 21:
        out.append(('bad' if days < 7 else 'warn', f'The HTTPS certificate expires in {days} days (it should renew itself at 30).'))
    nightly = srv.get('nightly_backup')
    nb_time = (nightly or {}).get('time')
    if not nightly:
        out.append(('bad', 'No nightly database backup found.'))
    elif isinstance(nb_time, datetime) and now - nb_time > timedelta(hours=26):
        out.append(('bad', f'The last nightly backup is {int((now - nb_time).total_seconds() // 3600)} hours old.'))
    if srv.get('security_updates'):
        out.append(('warn', f"{srv['security_updates']} security updates are waiting: run apt upgrade."))
    if srv.get('reboot_required'):
        out.append(('info', 'The server wants a restart to finish installing updates.'))

    runs = ((snap.get('github') or {}).get('runs') or [])
    main_runs = [r for r in runs if r.get('name') == 'Test and deploy' and r.get('branch') == 'main']
    if main_runs and main_runs[0].get('conclusion') == 'failure':
        r = main_runs[0]
        failed = next((j for j in r.get('jobs', []) if j.get('conclusion') == 'failure'), None)
        what = f"{failed['name']} failed" if failed else 'failed'
        out.append(('bad', f"The latest pipeline run ({r['sha']}) {what}: {r.get('message') or ''}"))
    deploys = snap.get('deploys') or []
    if deploys and deploys[0].get('result') == 'failed':
        out.append(('bad', f"The last {deploys[0].get('action')} failed: {deploys[0].get('note') or ''}"))

    app = snap.get('app') or {}
    if app.get('errors_24h'):
        out.append(('bad', f"{app['errors_24h']} app errors in the last 24 hours."))
    web = snap.get('web') or {}
    if (web.get('status_24h') or {}).get('5xx'):
        out.append(('warn', f"{web['status_24h']['5xx']} requests failed with a server error (5xx) in 24 hours."))
    if users and users['failed_7d'] >= 10:
        out.append(('warn', f"{users['failed_7d']} failed sign-ins in 7 days."))
    order = {'bad': 0, 'warn': 1, 'info': 2}
    return sorted(out, key=lambda a: order.get(a[0], 3))


def monitor_page():
    snap, problem = load_snapshot()
    users = users_section()
    web = (snap or {}).get('web') or {}
    return {
        'snap': snap,
        'problem': problem,
        'users': users,
        'alerts': alerts(snap, users),
        'hours': {'rows': _hour_rows(web.get('hourly'))},
        'now': utcnow(),
    }


def strip_ansi(text):
    return re.sub(r'\x1b\[[0-9;]*m', '', text or '')
