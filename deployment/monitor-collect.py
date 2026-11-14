#!/usr/bin/env python3
"""Collects what the developer page shows that only root can read.

Runs from cron every 5 minutes as root and writes one summary file the app can
read (owner root, group harithma, mode 640):

    /var/lib/harithma-monitor/snapshot.json

It reads the nginx access and error logs, the SSH log, the app's journal, the
deploy history, GitHub Actions (public API, cached) and basic server health.
Only summaries and recent entries are written, never passwords or keys.

Installed root-owned (the repository belongs to the app user):
    sudo install -o root -g root -m 755 deployment/monitor-collect.py /usr/local/bin/harithma-monitor-collect
Uses only the Python standard library.
"""
import glob
import gzip
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

OUT_DIR = '/var/lib/harithma-monitor'
OUT_FILE = os.path.join(OUT_DIR, 'snapshot.json')
CACHE_FILE = os.path.join(OUT_DIR, 'github-cache.json')
APP_GROUP = 'harithma'
SERVICE = 'harithma-pos'
REPO = 'Madlhawa/HarithmaPOS'
DEPLOY_HISTORY = '/var/lib/harithma-deploy/history.jsonl'
NIGHTLY_DIR = '/root/backups/nightly'
PREDEPLOY_DIR = '/root/backups/predeploy'
CERT = '/etc/letsencrypt/live/harithma.lk/cert.pem'
DB_NAME = 'harithma_pos'

UTC = timezone.utc
NOW = datetime.now(UTC)
DAY = NOW - timedelta(hours=24)
WEEK = NOW - timedelta(days=7)

# What attackers and scanners look for. First match names the request.
PROBES = [
    ('Secrets and config files', r'(^|/)\.(env|git|svn|aws|ssh|htaccess|htpasswd|DS_Store)|/config\.(json|ya?ml|php)|credentials|/\.well-known/security\.txt\.bak|web\.config|id_rsa'),
    ('WordPress', r'wp-(admin|login|content|includes|config|json)|xmlrpc\.php|/wordpress'),
    ('PHP and admin panels', r'\.php\b|phpmyadmin|/pma\b|/myadmin|/adminer|/administrator|/manager/html|/console\b|/druid|/jenkins|/hudson|/telescope|/_profiler|/solr|/actuator|/geoserver'),
    ('Path traversal', r'\.\./|%2e%2e|/etc/passwd|/proc/self|win\.ini'),
    ('SQL injection', r"union(\s|%20|\+)+select|select(\s|%20|\+).+from|'(\s|%20)*or(\s|%20)|sleep\(|benchmark\("),
    ('Script injection', r'<script|%3cscript|javascript:|onerror='),
    ('Router and device exploits', r'/boaform|/HNAP1|/cgi-bin|/SDK/|/GponForm|/setup\.cgi|/shell\b|/goform|/remote/|/owa/|/autodiscover|/ecp/|/vpn/|/global-protect|/sslvpn|/dana-na|/ReportServer'),
    ('Other server software', r'\.(asp|aspx|jsp|cgi|do|action)\b'),
]
PROBE_RES = [(label, re.compile(rx, re.I)) for label, rx in PROBES]
GOOD_METHODS = {'GET', 'POST', 'HEAD', 'OPTIONS'}
BOT_UA = re.compile(r'bot|crawl|spider|slurp|curl|wget|python|go-http|zgrab|masscan|nmap|scan|httpclient|java/|libwww|okhttp|headless', re.I)

LINE = re.compile(r'^(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<req>[^"]*)" (?P<status>\d{3}) (?P<bytes>\S+) "(?P<ref>[^"]*)" "(?P<ua>[^"]*)"')


def read_lines(pattern):
    """Lines of a log and its rotated copies (.1, .2.gz ...), oldest first."""
    files = sorted(glob.glob(pattern + '*'), key=os.path.getmtime)
    for path in files:
        opener = gzip.open if path.endswith('.gz') else open
        try:
            with opener(path, 'rt', errors='replace') as handle:
                for line in handle:
                    yield line.rstrip('\n')
        except OSError:
            continue


def classify(method, path, status, request_line):
    if status == 429:
        return 'Rate limited (sign-in)'
    if not method or method not in GOOD_METHODS:
        return 'Malformed or unusual request' if status >= 400 or not method else 'Unusual method'
    for label, rx in PROBE_RES:
        if rx.search(path):
            return label
    return None


def nginx():
    hourly = defaultdict(lambda: Counter())
    daily = defaultdict(lambda: {'requests': 0, 'ips': set(), 'visitors': set(), 'suspicious': 0})
    status_24 = Counter()
    ips_24, visitors_24 = set(), set()
    requests_24 = 0
    probe_kinds = Counter()
    probe_ips = defaultdict(lambda: {'count': 0, 'kinds': Counter(), 'last': None, 'statuses': Counter()})
    recent_probes = []
    not_found = Counter()
    server_errors = []
    slow_paths = Counter()

    for line in read_lines('/var/log/nginx/access.log'):
        m = LINE.match(line)
        if not m:
            continue
        try:
            ts = datetime.strptime(m['ts'], '%d/%b/%Y:%H:%M:%S %z').astimezone(UTC)
        except ValueError:
            continue
        if ts < WEEK:
            continue
        parts = m['req'].split(' ')
        method = parts[0] if len(parts) == 3 else ''
        path = parts[1] if len(parts) == 3 else m['req'][:120]
        status = int(m['status'])
        ip, ua = m['ip'], m['ua']
        kind = classify(method, path, status, m['req'])
        day = ts.date().isoformat()
        d = daily[day]
        d['requests'] += 1
        d['ips'].add(ip)
        if kind:
            d['suspicious'] += 1
        elif not BOT_UA.search(ua) and not path.startswith('/static'):
            d['visitors'].add(ip)

        if ts < DAY:
            continue
        requests_24 += 1
        ips_24.add(ip)
        status_24[f"{status // 100}xx"] += 1
        hour = ts.replace(minute=0, second=0, microsecond=0).isoformat()
        if kind:
            hourly[hour]['suspicious'] += 1
            probe_kinds[kind] += 1
            p = probe_ips[ip]
            p['count'] += 1
            p['kinds'][kind] += 1
            p['statuses'][status] += 1
            p['last'] = ts.isoformat()
            recent_probes.append({'time': ts.isoformat(), 'ip': ip, 'kind': kind, 'method': method or '-',
                                  'path': path[:160], 'status': status, 'agent': ua[:120]})
        elif status >= 500:
            hourly[hour]['server_error'] += 1
            server_errors.append({'time': ts.isoformat(), 'ip': ip, 'method': method, 'path': path[:160], 'status': status})
        elif status >= 400:
            hourly[hour]['client_error'] += 1
            if status == 404:
                not_found[path[:120]] += 1
        else:
            hourly[hour]['ok'] += 1
            if not BOT_UA.search(ua) and not path.startswith('/static'):
                visitors_24.add(ip)

    hours = []
    start = NOW.replace(minute=0, second=0, microsecond=0) - timedelta(hours=23)
    for i in range(24):
        h = (start + timedelta(hours=i)).isoformat()
        c = hourly.get(h, Counter())
        hours.append({'hour': h, 'ok': c['ok'], 'client_error': c['client_error'],
                      'suspicious': c['suspicious'], 'server_error': c['server_error']})
    top_ips = sorted(probe_ips.items(), key=lambda kv: -kv[1]['count'])[:15]
    return {
        'requests_24h': requests_24,
        'unique_ips_24h': len(ips_24),
        'visitors_24h': len(visitors_24),
        'status_24h': dict(status_24),
        'suspicious_24h': sum(probe_kinds.values()),
        'suspicious_ips_24h': len(probe_ips),
        'probe_kinds_24h': probe_kinds.most_common(),
        'top_probe_ips': [{'ip': ip, 'count': v['count'], 'kinds': [k for k, _ in v['kinds'].most_common(3)],
                           'blocked': sum(n for s, n in v['statuses'].items() if s >= 400 or s in (301, 302)),
                           'last': v['last']} for ip, v in top_ips],
        'recent_probes': recent_probes[-60:][::-1],
        'not_found_24h': not_found.most_common(10),
        'server_errors_24h': server_errors[-30:][::-1],
        'hourly': hours,
        'daily': [{'day': day, 'requests': v['requests'], 'unique_ips': len(v['ips']),
                   'visitors': len(v['visitors']), 'suspicious': v['suspicious']}
                  for day, v in sorted(daily.items())][-7:],
    }


# Broken or hostile clients failing the TLS handshake: counted, not listed.
TLS_NOISE = re.compile(r'while SSL handshaking|SSL_do_handshake\(\) failed')


def nginx_errors():
    out, tls_noise = [], 0
    for line in read_lines('/var/log/nginx/error.log'):
        m = re.match(r'^(\d{4}/\d\d/\d\d \d\d:\d\d:\d\d) \[(\w+)\] \d+#\d+: (?:\*\d+ )?(.*)$', line)
        if not m:
            continue
        ts = datetime.strptime(m[1], '%Y/%m/%d %H:%M:%S').replace(tzinfo=UTC)
        if ts < WEEK or m[2] not in ('error', 'crit', 'alert', 'emerg'):
            continue
        if TLS_NOISE.search(m[3]):
            tls_noise += 1
            continue
        msg = re.sub(r', client: [^,]+', '', m[3])
        out.append({'time': ts.isoformat(), 'level': m[2], 'message': msg[:300]})
    return {'entries': out[-20:][::-1], 'tls_noise_7d': tls_noise}


def ssh():
    failed = Counter()
    users = Counter()
    accepted = []
    attempts = 0
    year = NOW.year
    for line in read_lines('/var/log/auth.log'):
        if 'sshd[' not in line:
            continue
        try:
            ts = datetime.strptime(f"{year} {line[:15]}", '%Y %b %d %H:%M:%S').replace(tzinfo=UTC)
        except ValueError:
            continue
        if ts > NOW + timedelta(days=1):
            ts = ts.replace(year=year - 1)
        if ts < DAY:
            continue
        m = re.search(r'Accepted (\w+) for (\S+) from (\S+)', line)
        if m:
            accepted.append({'time': ts.isoformat(), 'method': m[1], 'user': m[2], 'ip': m[3]})
            continue
        m = (re.search(r'Invalid user (\S*) from (\S+)', line)
             or re.search(r'Failed \w+ for (?:invalid user )?(\S+) from (\S+)', line)
             or re.search(r'Connection (?:closed|reset) by authenticating user (\S+) (\S+) port \d+ \[preauth\]', line))
        if m:
            attempts += 1
            users[m[1] or '(empty)'] += 1
            failed[m[2]] += 1
    return {'failed_24h': attempts, 'attacking_ips_24h': len(failed), 'top_ips': failed.most_common(10),
            'top_users': users.most_common(10), 'accepted_24h': accepted[-20:][::-1]}


LOG_START = re.compile(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d+ (WARNING|ERROR|CRITICAL) ')
GUNICORN = re.compile(r'^\[[^\]]+\] \[\d+\] \[(ERROR|CRITICAL|WARNING)\] ')


def app_journal():
    try:
        raw = subprocess.run(['journalctl', '-u', SERVICE, '--since', '-7d', '-o', 'json', '--no-pager'],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception as exc:
        return {'error': str(exc)}
    entries, current = [], None
    starts, stops = [], 0
    for row in raw.splitlines():
        try:
            j = json.loads(row)
        except ValueError:
            continue
        msg = j.get('MESSAGE')
        if isinstance(msg, list):
            msg = bytes(msg).decode('utf-8', 'replace')
        msg = msg or ''
        ts = datetime.fromtimestamp(int(j.get('__REALTIME_TIMESTAMP', 0)) / 1e6, UTC)
        if j.get('_COMM') == 'systemd' or j.get('SYSLOG_IDENTIFIER') == 'systemd':
            if msg.startswith('Started '):
                starts.append(ts.isoformat())
            elif 'Failed' in msg or 'failed' in msg:
                entries.append({'time': ts.isoformat(), 'level': 'ERROR', 'source': 'systemd', 'where': '',
                                'message': msg[:300], 'lines': []})
            continue
        m = LOG_START.match(msg)
        g = GUNICORN.match(msg)
        if m:
            rest = msg[m.end():]
            mm = re.match(r'(\S+) \[([^\]]*)\] (.*)', rest)
            current = {'time': ts.isoformat(), 'level': m[1], 'source': mm[1] if mm else '',
                       'where': mm[2] if mm else '', 'message': (mm[3] if mm else rest)[:500], 'lines': []}
            entries.append(current)
        elif g:
            current = {'time': ts.isoformat(), 'level': g[1], 'source': 'gunicorn', 'where': '',
                       'message': msg[g.end():][:500], 'lines': []}
            entries.append(current)
        elif current is not None and (msg.startswith((' ', '\t', 'Traceback')) or re.match(r'^[\w.]+(Error|Exception|Warning)\b', msg)):
            if len(current['lines']) < 40:
                current['lines'].append(msg[:300])
        else:
            current = None
    errors_24 = [e for e in entries if e['time'] >= DAY.isoformat()]
    return {
        'entries': entries[-40:][::-1],
        'errors_24h': sum(1 for e in errors_24 if e['level'] in ('ERROR', 'CRITICAL')),
        'warnings_24h': sum(1 for e in errors_24 if e['level'] == 'WARNING'),
        'errors_7d': sum(1 for e in entries if e['level'] in ('ERROR', 'CRITICAL')),
        'restarts_7d': len(starts),
        'last_start': starts[-1] if starts else None,
    }


def deploys():
    rows = []
    try:
        with open(DEPLOY_HISTORY) as handle:
            for line in handle:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return rows[-30:][::-1]


def github():
    """Recent workflow runs. Finished runs' jobs are cached; the API allows 60 calls an hour."""
    try:
        with open(CACHE_FILE) as handle:
            cache = json.load(handle)
    except (OSError, ValueError):
        cache = {}
    jobs_cache = cache.get('jobs', {})

    def get(url):
        req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json',
                                                   'User-Agent': 'harithma-monitor'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.load(resp)

    try:
        data = get(f'https://api.github.com/repos/{REPO}/actions/runs?per_page=20')
    except Exception as exc:
        return {'error': f'GitHub could not be reached: {exc.__class__.__name__}', 'runs': cache.get('runs', [])}

    runs = []
    for r in data.get('workflow_runs', []):
        if r.get('name', '').startswith('Graph Update'):
            continue
        rid = str(r['id'])
        key = f"{rid}:{r.get('run_attempt', 1)}"
        jobs = jobs_cache.get(key)
        if jobs is None and r['status'] == 'completed' and len(jobs_cache) < 500:
            try:
                jd = get(r['jobs_url'])
                jobs = [{'name': j['name'], 'conclusion': j['conclusion'],
                         'started': j.get('started_at'), 'completed': j.get('completed_at'),
                         'failed_step': next((s['name'] for s in j.get('steps', []) if s.get('conclusion') == 'failure'), None)}
                        for j in jd.get('jobs', [])]
                jobs_cache[key] = jobs
            except Exception:
                jobs = None
        started = r.get('run_started_at') or r.get('created_at')
        runs.append({
            'id': r['id'], 'name': r['name'], 'event': r['event'], 'branch': r.get('head_branch'),
            'sha': r['head_sha'][:7], 'message': ((r.get('head_commit') or {}).get('message') or '').split('\n')[0][:120],
            'actor': (r.get('actor') or {}).get('login'), 'status': r['status'], 'conclusion': r.get('conclusion'),
            'started': started, 'updated': r.get('updated_at'), 'attempt': r.get('run_attempt', 1),
            'url': r.get('html_url'), 'jobs': jobs or [],
        })
    cache = {'runs': runs, 'jobs': dict(list(jobs_cache.items())[-300:])}
    write_json(CACHE_FILE, cache, mode=0o600)
    return {'runs': runs}


def run(cmd, timeout=20):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ''


def newest(pattern):
    files = glob.glob(pattern)
    if not files:
        return None
    path = max(files, key=os.path.getmtime)
    st = os.stat(path)
    return {'name': os.path.basename(path), 'size': st.st_size,
            'time': datetime.fromtimestamp(st.st_mtime, UTC).isoformat()}


def apt_updates():
    """(pending, security) package updates. apt-check is slow, so it runs at most once an hour."""
    cache = os.path.join(OUT_DIR, 'apt-cache.json')
    try:
        if time.time() - os.path.getmtime(cache) < 3600:
            with open(cache) as handle:
                return tuple(json.load(handle))
    except (OSError, ValueError):
        pass
    result = (None, None)
    if os.path.exists('/usr/lib/update-notifier/apt-check'):
        try:
            out = subprocess.run(['/usr/lib/update-notifier/apt-check'], capture_output=True, text=True, timeout=120)
            text = (out.stderr or out.stdout).strip()     # apt-check prints "pending;security" on stderr
            if ';' in text:
                a, b = text.split(';')[:2]
                result = (int(a), int(b))
        except Exception:
            pass
    write_json(cache, list(result), mode=0o600)
    return result


def server():
    mem = {}
    with open('/proc/meminfo') as handle:
        for line in handle:
            k, v = line.split(':', 1)
            mem[k] = int(v.split()[0]) * 1024
    disk = shutil.disk_usage('/')
    with open('/proc/uptime') as handle:
        uptime = float(handle.read().split()[0])
    cert_end = run(['openssl', 'x509', '-enddate', '-noout', '-in', CERT]).replace('notAfter=', '')
    cert_days = None
    if cert_end:
        try:
            cert_days = (datetime.strptime(cert_end, '%b %d %H:%M:%S %Y %Z').replace(tzinfo=UTC) - NOW).days
        except ValueError:
            pass
    pending, security = apt_updates()
    services = {name: run(['systemctl', 'is-active', name]) or 'unknown'
                for name in (SERVICE, 'nginx', 'postgresql', 'cron', 'ufw')}
    db_size = run(['sudo', '-u', 'postgres', 'psql', '-tA', '-d', DB_NAME, '-c',
                   f"select pg_database_size('{DB_NAME}')"])
    return {
        'hostname': os.uname().nodename,
        'uptime_seconds': int(uptime),
        'load': list(os.getloadavg()),
        'cpus': os.cpu_count(),
        'memory': {'total': mem.get('MemTotal'), 'available': mem.get('MemAvailable'),
                   'swap_total': mem.get('SwapTotal'), 'swap_free': mem.get('SwapFree')},
        'disk': {'total': disk.total, 'used': disk.used, 'free': disk.free},
        'services': services,
        'cert_days_left': cert_days,
        'db_size': int(db_size) if db_size.isdigit() else None,
        'nightly_backup': newest(os.path.join(NIGHTLY_DIR, '*.dump')),
        'predeploy_backups': len(glob.glob(os.path.join(PREDEPLOY_DIR, '*.dump'))),
        'updates_pending': pending,
        'security_updates': security,
        'reboot_required': os.path.exists('/var/run/reboot-required'),
    }


def write_json(path, data, mode=0o640, group=None):
    tmp = path + '.tmp'
    with open(tmp, 'w') as handle:
        json.dump(data, handle, default=str)
    os.chmod(tmp, mode)
    if group:
        shutil.chown(tmp, user='root', group=group)
    os.replace(tmp, path)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.chmod(OUT_DIR, 0o750)
    shutil.chown(OUT_DIR, user='root', group=APP_GROUP)
    started = time.time()
    snapshot = {'collected_at': NOW.isoformat(), 'errors': {}}
    for name, fn in (('web', nginx), ('web_errors', nginx_errors), ('ssh', ssh), ('app', app_journal),
                     ('deploys', deploys), ('github', github), ('server', server)):
        try:
            snapshot[name] = fn()
        except Exception as exc:  # one broken source must not hide the others
            snapshot['errors'][name] = f'{exc.__class__.__name__}: {exc}'[:300]
    snapshot['took_seconds'] = round(time.time() - started, 2)
    write_json(OUT_FILE, snapshot, mode=0o640, group=APP_GROUP)


if __name__ == '__main__':
    main()
