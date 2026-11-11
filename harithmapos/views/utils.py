import json
import logging
import os
import secrets
from decimal import Decimal

import pika
import requests
from PIL import Image
from flask import url_for, current_app, flash, request, redirect
from flask_mail import Message
from sqlalchemy.exc import IntegrityError

import harithmapos.config as config
from harithmapos import db, mail
from harithmapos.textutils import normalize_phone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Small parsing helpers
# ---------------------------------------------------------------------------

def get_id(id_name_string):
    """Parse the id out of an old-style "12 | Name" label. Kept for compatibility."""
    return int(str(id_name_string).split('|')[0].strip())


def parse_int(value):
    """'12' -> 12, '' / None / 'abc' -> None."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return None


# Define a custom JSON encoder that handles Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


# ---------------------------------------------------------------------------
# Request / response helpers
# ---------------------------------------------------------------------------

def flash_form_errors(form):
    """Tell the user exactly which field was wrong instead of 'validation failed'."""
    for field_name, errors in form.errors.items():
        field = getattr(form, field_name, None)
        label = field.label.text if field is not None and getattr(field, 'label', None) else field_name
        for error in errors:
            flash(f"{label}: {error}", category='danger')


def is_safe_redirect_target(target):
    """Only allow redirects to a path on this site (blocks open-redirect tricks)."""
    if not target or not isinstance(target, str):
        return False
    return target.startswith('/') and not target.startswith('//') and '\\' not in target


def redirect_back(default_endpoint, **values):
    """Go back to the page named in a 'next' field if it is safe, else to a default."""
    target = request.form.get('next') or request.args.get('next')
    if is_safe_redirect_target(target):
        return redirect(target)
    return redirect(url_for(default_endpoint, **values))


def delete_record(record, label, blockers=()):
    """Delete a row, but refuse politely when other records still depend on it.

    blockers is an iterable of (count, description) pairs, for example
    [(Vehicle.query.filter_by(owner_id=c.id).count(), 'vehicles')].
    Returns True when the row was deleted.
    """
    in_use = [description for count, description in blockers if count]
    if in_use:
        flash(f"{label} can't be deleted because it still has {', '.join(in_use)}.", category='warning')
        return False
    try:
        db.session.delete(record)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(f"{label} can't be deleted because other records still refer to it.", category='warning')
        return False
    flash(f"{label} deleted.", category='success')
    return True


# ---------------------------------------------------------------------------
# Outside services: receipt printer queue, SMS, e-mail
# ---------------------------------------------------------------------------

def send_print_invoice(message, queue=None):
    """Queue a receipt for the print agent. Returns True if it was queued.

    Never raises: a printer or RabbitMQ outage must not stop a sale from
    being saved.
    """
    queue = queue or config.PRINT_QUEUE
    if not config.RABBIT_MQ_HOST:
        logger.warning("RABBIT_MQ_HOST is not set; skipping receipt printing")
        return False
    try:
        credentials = pika.PlainCredentials(config.RABBIT_MQ_USERNAME, config.RABBIT_MQ_PASSWORD)
        parameters = pika.ConnectionParameters(
            host=config.RABBIT_MQ_HOST,
            credentials=credentials,
            connection_attempts=1,
            socket_timeout=5,
            blocked_connection_timeout=5,
        )
        connection = pika.BlockingConnection(parameters)
        try:
            channel = connection.channel()
            channel.queue_declare(queue=queue)
            channel.basic_publish(exchange='', routing_key=queue, body=message)
        finally:
            connection.close()
    except Exception:
        logger.exception("Could not queue the receipt for printing")
        return False
    return True


def send_sms(recipient, message):
    """Send a text through notify.lk. Returns True if the gateway accepted it."""
    number = normalize_phone(recipient)
    if not number or len(number) != 9 or set(number) == {'0'}:
        logger.warning("SMS not sent: no usable phone number")
        return False
    if not (config.NOTIFYLK_USER_ID and config.NOTIFYLK_API_KEY):
        logger.warning("SMS not sent: NOTIFYLK_USER_ID / NOTIFYLK_API_KEY are not set")
        return False

    payload = {
        "user_id": config.NOTIFYLK_USER_ID,
        "api_key": config.NOTIFYLK_API_KEY,
        "sender_id": config.NOTIFYLK_SENDER_ID,
        "to": f"94{number}",
        "message": message
    }
    try:
        response = requests.get(config.NOTIFYLK_API_URL, params=payload, timeout=10)
    except requests.RequestException as exc:
        # Log the error type only: the request URL contains the API key.
        logger.error("SMS request failed: %s", type(exc).__name__)
        return False

    if response.status_code != 200:
        logger.error("SMS gateway answered HTTP %s", response.status_code)
        return False
    try:
        body = response.json()
    except ValueError:
        body = {}
    if isinstance(body, dict) and str(body.get('status', '')).lower() == 'error':
        logger.error("SMS gateway rejected the message")
        return False
    return True


def save_image(form_image):
    random_hex = secrets.token_hex(8)
    _, file_extention = os.path.splitext(form_image.filename)
    image_file_name = random_hex + file_extention.lower()
    image_path = os.path.join(current_app.root_path, 'static/images/user_images', image_file_name)

    output_size = (125, 125)
    i = Image.open(form_image)
    i.thumbnail(output_size)
    if file_extention.lower() in ('.jpg', '.jpeg') and i.mode not in ('RGB', 'L'):
        i = i.convert('RGB')
    i.save(image_path)

    return image_file_name


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request', sender=current_app.config['MAIL_USERNAME'], recipients=[user.email])
    msg.body = f'''To reset your password please visit:
{url_for('user_blueprint.reset_token', token=token, _external=True)}

This link works for 30 minutes.
If you did not make this request then simply ignore this email.
'''
    mail.send(msg)
