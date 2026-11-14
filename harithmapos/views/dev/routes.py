"""The developer page: deployments, tests, users, attacks, errors and server health.

Only for the emails in HARITHMA_DEVELOPER_EMAILS (server .env). Everyone else,
owners included, gets a plain 404, so the page does not advertise itself.
"""
from functools import wraps

from flask import Blueprint, abort, render_template
from flask_login import current_user

from harithmapos import devtools, login_manager

dev_blueprint = Blueprint('dev_blueprint', __name__)


def developer_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if not devtools.user_is_developer():
            abort(404)
        return view(*args, **kwargs)
    return wrapped


@dev_blueprint.route('/app/dev')
@developer_required
def monitor():
    return render_template('dev/monitor.html', title='Developer', **devtools.monitor_page())
