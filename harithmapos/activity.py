"""Who uses the app: sign-in events, last seen and unique users per day.

Everything here is best effort. A failure to record activity is logged and
never stops anyone from signing in or using a page.
"""
import logging
from datetime import timedelta

from flask import has_request_context, request
from flask_login import current_user

from harithmapos import config, db
from harithmapos.timeutils import local_today, utcnow

logger = logging.getLogger(__name__)

SEEN_EVERY = timedelta(seconds=60)


def _client():
    ip = (request.remote_addr or '')[:45] or None
    agent = (request.headers.get('User-Agent') or '')[:200] or None
    return ip, agent


def record_login(outcome, user=None, email=None):
    """outcome: ok, bad_password, unknown_email, switched_off or logout."""
    from harithmapos.models import LoginEvent
    try:
        ip, agent = _client()
        db.session.add(LoginEvent(user_id=user.id if user else None,
                                  email=(email or (user.email if user else None) or '')[:120] or None,
                                  outcome=outcome, ip=ip, user_agent=agent))
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Could not record a %s sign-in event", outcome)


def touch_current_user():
    """Before each request: note that the signed-in user is active (at most once a minute)."""
    from harithmapos.models import UserActivityDay
    if request.endpoint in (None, 'static') or not current_user.is_authenticated:
        return
    now = utcnow()
    last = current_user.last_seen_dttm
    if last and now - last < SEEN_EVERY:
        return
    try:
        current_user.last_seen_dttm = now
        today = local_today(config.APP_TIMEZONE)
        row = UserActivityDay.query.filter_by(user_id=current_user.id, day=today).first()
        if row:
            row.requests = (row.requests or 0) + 1
        else:
            db.session.add(UserActivityDay(user_id=current_user.id, day=today, requests=1))
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Could not record user activity")


class RequestContextFilter(logging.Filter):
    """Adds the request and user to every log line, so errors can be traced."""

    def filter(self, record):
        where = '-'
        if has_request_context():
            try:
                who = current_user.id if current_user.is_authenticated else 'anon'
            except Exception:
                who = '?'
            where = f"{request.method} {request.path} user={who}"
        record.where = where
        return True


def configure_logging(app):
    """Warnings and errors go to stderr (the systemd journal) in one parseable format:
    2026-11-14 08:41:06,123 ERROR harithmapos.views.x [POST /app/... user=1] message
    The developer page reads these lines back from the journal.
    """
    if app.testing:
        return
    root = logging.getLogger()
    if any(getattr(h, '_harithma', False) for h in root.handlers):
        return
    handler = logging.StreamHandler()
    handler._harithma = True
    handler.setLevel(logging.WARNING)
    handler.addFilter(RequestContextFilter())
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s [%(where)s] %(message)s'))
    root.addHandler(handler)
    if root.level > logging.WARNING or root.level == logging.NOTSET:
        root.setLevel(logging.WARNING)
