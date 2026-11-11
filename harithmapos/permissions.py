"""Who may do what.

Owners can do everything. Counter staff can run services and item sales,
look after customers and vehicles, and take money in. Everything else
(deleting records, costs and margins, stock, suppliers, employees, wash bays,
users and money going out) is for owners only.
"""
from functools import wraps

from flask import abort, flash, request
from flask_login import current_user

from harithmapos import login_manager

OWNER_ONLY_MESSAGE = "Only an owner can do that. Ask an owner to do it for you."


def user_is_owner():
    """True when the person signed in is an owner. Safe to call from any template."""
    return bool(current_user and current_user.is_authenticated and current_user.is_owner)


def owner_required(view):
    """Like login_required, but the user must also be an owner.

    Pages answer with the 403 page. Buttons (POST) go back to where the user
    was with a message, since the page they came from is still useful.
    """
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if not current_user.is_owner:
            if request.method == 'POST':
                from harithmapos.views.utils import redirect_back
                flash(OWNER_ONLY_MESSAGE, category='warning')
                return redirect_back('dashboard_blueprint.dashboard')
            abort(403)
        return view(*args, **kwargs)
    return wrapped
