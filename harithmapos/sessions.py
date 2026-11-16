"""How long a sign-in lasts.

Two kinds of device:

* Shared (the counter PC): "Keep me signed in" is left unticked. The sign-in
  ends when the browser closes, and after the idle time set on the Settings
  page (General) with no page opened or button pressed. The page then goes
  back to the sign-in screen by itself, so the next person never finds the
  last one's session open.
* Own phone or PC: "Keep me signed in" ticked. The sign-in lasts 30 days
  (REMEMBER_COOKIE_DURATION in config.py), browser restarts included, with no
  idle sign-out.

Live updates on the dashboard and floor board are not activity: a board left
open on an unattended counter still signs out.
"""
import time

from flask import flash, redirect, request, session, url_for
from flask_login import current_user, logout_user

from harithmapos import settings as app_settings

TRUSTED = '_trusted_device'
LAST_ACTIVE = '_last_active'
# The last-active time is written into the session cookie at most this often.
TOUCH_EVERY_SECONDS = 30
# Requests that keep a page up to date without anyone using it.
PASSIVE_ENDPOINTS = {'live_blueprint.live', 'static'}


def start(remember):
    """Call right after login_user()."""
    session[TRUSTED] = bool(remember)
    session[LAST_ACTIVE] = int(time.time())


def is_trusted_device():
    # A sign-in brought back from the 30-day cookie (Flask-Login marks it "not fresh")
    # was made with "Keep me signed in" ticked.
    return bool(session.get(TRUSTED)) or session.get('_fresh') is False


def idle_limit_seconds():
    """0 when this sign-in never times out."""
    if not current_user.is_authenticated or is_trusted_device():
        return 0
    return max(0, int(app_settings.get('idle_signout_minutes') or 0)) * 60


def _is_passive():
    return (request.endpoint in PASSIVE_ENDPOINTS or request.headers.get('X-Live-Refresh') == '1'
            or request.args.get('_auto') == '1')   # the boards' automatic safety-net reload


def enforce_idle_signout():
    """Before each request: sign out an idle shared device, otherwise note the activity."""
    if request.endpoint in (None, 'static') or not current_user.is_authenticated:
        return None
    limit = idle_limit_seconds()
    now = int(time.time())
    last = session.get(LAST_ACTIVE)
    if limit and last and now - last > limit:
        from harithmapos.activity import record_login
        record_login('timeout', current_user._get_current_object())
        logout_user()
        session.pop(TRUSTED, None)
        session.pop(LAST_ACTIVE, None)
        minutes = limit // 60
        flash(f"You were signed out after {minutes} minute{'s' if minutes != 1 else ''} without activity. "
              "Sign in again to carry on.", category='info')
        if request.method == 'GET' and not _is_passive():
            return redirect(url_for('user_blueprint.login', next=request.full_path.rstrip('?')))
        return redirect(url_for('user_blueprint.login'))
    if not _is_passive() and (not last or now - last >= TOUCH_EVERY_SECONDS):
        session[LAST_ACTIVE] = now
    return None


def register(app):
    app.before_request(enforce_idle_signout)
    app.jinja_env.globals['idle_limit_seconds'] = idle_limit_seconds
