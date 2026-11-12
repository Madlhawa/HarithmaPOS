"""The Settings page: business details, email, SMS, receipt printer and general values. Owners only."""
import logging

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user

from harithmapos import settings as app_settings
from harithmapos.permissions import owner_required
import harithmapos.views.utils as utils

logger = logging.getLogger(__name__)

settings_blueprint = Blueprint('settings_blueprint', __name__)

GROUP_KEYS = [key for key, _, _ in app_settings.GROUPS]


def _secret_status(key):
    """How a password or API key field should be described, without ever showing it."""
    if app_settings.secret_unreadable(key):
        return 'unreadable'
    if app_settings.is_saved(key):
        return 'saved' if app_settings.get(key) else 'empty'
    return 'env' if app_settings.get(key) else 'empty'


def _page(values=None, errors=None, status=200):
    current = {}
    secrets = {}
    for d in app_settings.DEFINITIONS:
        if d.kind == app_settings.SECRET:
            secrets[d.key] = _secret_status(d.key)
        else:
            current[d.key] = app_settings.get(d.key)
    if values:
        current.update(values)
    unsaved_groups = {
        group for group in GROUP_KEYS
        if not any(app_settings.is_saved(d.key) for d in app_settings.definitions_for(group))
    }
    return render_template(
        'settings.html',
        title='Settings',
        groups=[(key, label, hint, app_settings.definitions_for(key)) for key, label, hint in app_settings.GROUPS],
        values=current,
        secrets=secrets,
        errors=errors or {},
        unsaved_groups=unsaved_groups,
        placeholders=app_settings.SMS_PLACEHOLDERS,
    ), status


def _read_form(group):
    """Turn the posted form into {key: value} for one group. Returns (values, errors)."""
    values, errors = {}, {}
    for d in app_settings.definitions_for(group):
        raw = request.form.get(d.key, '')
        if d.kind == app_settings.BOOL:
            values[d.key] = d.key in request.form
        elif d.kind == app_settings.SECRET:
            if request.form.get(d.key + '__clear'):
                values[d.key] = ''
            elif raw:
                if len(raw) > 500:
                    errors[d.key] = 'That is too long.'
                else:
                    values[d.key] = raw
            # Empty and not cleared: keep what is there.
        elif d.kind == app_settings.INT:
            try:
                number = int(raw.strip())
            except ValueError:
                errors[d.key] = 'Enter a whole number.'
                continue
            if d.min_value is not None and number < d.min_value or d.max_value is not None and number > d.max_value:
                errors[d.key] = f'Enter a number from {d.min_value} to {d.max_value}.'
                continue
            values[d.key] = number
        elif d.kind == app_settings.TIME:
            text = raw.strip()
            try:
                hours, minutes = (int(x) for x in text.split(':')[:2])
                if not (0 <= hours < 24 and 0 <= minutes < 60):
                    raise ValueError
            except ValueError:
                errors[d.key] = 'Enter a time such as 07:30.'
                continue
            values[d.key] = f'{hours:02d}:{minutes:02d}'
        elif d.kind == app_settings.CHOICE:
            if raw not in dict(d.choices):
                errors[d.key] = 'Choose one of the options.'
                continue
            values[d.key] = raw
        else:
            text = raw.strip()
            if len(text) > d.max_length:
                errors[d.key] = f'Use at most {d.max_length} characters.'
                continue
            if d.placeholders:
                problem = app_settings.check_sms_template(text)
                if problem:
                    errors[d.key] = problem
                    continue
            values[d.key] = text
    return values, errors


@settings_blueprint.route('/app/settings', methods=['GET'])
@owner_required
def settings():
    return _page()


@settings_blueprint.route('/app/settings/<group>', methods=['POST'])
@owner_required
def save_settings(group):
    if group not in GROUP_KEYS:
        abort(404)
    values, errors = _read_form(group)
    if errors:
        flash('Some settings were not saved. Fix the fields marked below.', category='danger')
        shown = {k: v for k, v in values.items()}
        # Show what was typed, including the fields that were wrong.
        for key in errors:
            if app_settings.BY_KEY[key].kind != app_settings.SECRET:
                shown[key] = request.form.get(key, '')
        return _page(values=shown, errors=errors, status=422)
    try:
        app_settings.save(values, user=current_user)
    except Exception:
        logger.exception("Could not save %s settings", group)
        flash('The settings could not be saved. Please try again.', category='danger')
        return redirect(url_for('settings_blueprint.settings', _anchor=group))
    label = dict((key, label) for key, label, _ in app_settings.GROUPS)[group]
    flash(f'{label} saved.', category='success')
    return redirect(url_for('settings_blueprint.settings', _anchor=group))


@settings_blueprint.route('/app/settings/test/email', methods=['POST'])
@owner_required
def test_email():
    to = (request.form.get('to') or current_user.email).strip()
    try:
        utils.send_email(
            to, f"Test email from {app_settings.get('business_name')}",
            "This is a test from the Harithma POS Settings page. Email is working.")
        flash(f'Test email sent to {to}. Check the inbox (and the spam folder).', category='success')
    except utils.ServiceError as exc:
        flash(f'The test email was not sent. {exc}', category='danger')
    return redirect(url_for('settings_blueprint.settings', _anchor='email'))


@settings_blueprint.route('/app/settings/test/sms', methods=['POST'])
@owner_required
def test_sms():
    number = request.form.get('to', '')
    try:
        utils.send_sms(number, f"Test message from {app_settings.get('business_name')}. SMS is working.",
                       raise_errors=True)
        flash('Test SMS sent. It can take a minute to arrive.', category='success')
    except utils.ServiceError as exc:
        flash(f'The test SMS was not sent. {exc}', category='danger')
    return redirect(url_for('settings_blueprint.settings', _anchor='sms'))


@settings_blueprint.route('/app/settings/test/printer', methods=['POST'])
@owner_required
def test_printer():
    try:
        utils.check_printer_connection()
        flash(f"Connected to RabbitMQ and the queue \"{app_settings.get('print_queue')}\" is ready.",
              category='success')
    except utils.ServiceError as exc:
        flash(f'The printer queue could not be reached. {exc}', category='danger')
    return redirect(url_for('settings_blueprint.settings', _anchor='printer'))
