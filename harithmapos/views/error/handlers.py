from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_wtf.csrf import CSRFError

from harithmapos import db

error_blueprint = Blueprint('error_blueprint', __name__)


@error_blueprint.app_errorhandler(404)
def error_404(error):
    return render_template('error/404.html', title='Page not found'), 404


@error_blueprint.app_errorhandler(403)
def error_403(error):
    return render_template('error/403.html', title='Not allowed'), 403


@error_blueprint.app_errorhandler(405)
def error_405(error):
    # Usually an old bookmark or link to an action that now needs a button press.
    return render_template(
        'error/404.html',
        title='Use the button',
        heading='That action needs a button',
        message='This address changes data, so it only works from the button on the page. '
                'Go back and use the button there.',
    ), 405


@error_blueprint.app_errorhandler(CSRFError)
def error_csrf(error):
    """The form's security token did not match, usually after signing out in another tab."""
    flash("That page had been open too long. Please try again.", category='warning')
    target = request.referrer if request.referrer and request.referrer.startswith(request.host_url) else None
    return redirect(target or url_for('user_blueprint.login'))


@error_blueprint.app_errorhandler(500)
def error_500(error):
    # Leave the database session usable for the next request.
    db.session.rollback()
    return render_template('error/500.html', title='Something went wrong'), 500
