import json
import logging
import os
import secrets
import smtplib
import ssl
from email.message import EmailMessage
from decimal import Decimal

import pika
import requests
from PIL import Image
from flask import url_for, current_app, flash, request, redirect
from sqlalchemy.exc import IntegrityError

import harithmapos.config as config
from harithmapos import db
from harithmapos import settings as app_settings
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

class ServiceError(Exception):
    """An outside service (printer queue, SMS, e-mail) failed. The message is safe to show to the user."""


def printer_enabled():
    return bool(app_settings.get('printer_enabled') and app_settings.get('rabbitmq_host'))


def _rabbitmq_connection():
    credentials = pika.PlainCredentials(
        app_settings.get('rabbitmq_username'), app_settings.get('rabbitmq_password'))
    parameters = pika.ConnectionParameters(
        host=app_settings.get('rabbitmq_host'),
        port=app_settings.get('rabbitmq_port'),
        credentials=credentials,
        connection_attempts=1,
        socket_timeout=5,
        blocked_connection_timeout=5,
    )
    return pika.BlockingConnection(parameters)


def send_print_invoice(message, queue=None):
    """Queue a receipt for the print agent. Returns True if it was queued.

    Never raises: a printer or RabbitMQ outage must not stop a sale from
    being saved.
    """
    if not printer_enabled():
        logger.info("Receipt printer is switched off or has no host; skipping")
        return False
    queue = queue or app_settings.get('print_queue')
    try:
        connection = _rabbitmq_connection()
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


def check_printer_connection():
    """Connect to RabbitMQ and make sure the queue exists. Raises ServiceError on failure."""
    if not app_settings.get('rabbitmq_host'):
        raise ServiceError("Enter the RabbitMQ host first.")
    try:
        connection = _rabbitmq_connection()
    except pika.exceptions.ProbableAuthenticationError:
        raise ServiceError("RabbitMQ refused the username or password.")
    except Exception as exc:
        logger.warning("RabbitMQ test connection failed: %s", type(exc).__name__)
        raise ServiceError("Could not connect to RabbitMQ. Check the host and port, and that it is running.")
    try:
        connection.channel().queue_declare(queue=app_settings.get('print_queue'))
    except Exception:
        raise ServiceError("Connected, but the print queue could not be opened. Check the user's permissions.")
    finally:
        try:
            connection.close()
        except Exception:
            pass


def sms_ready():
    return bool(app_settings.get('sms_enabled')
                and app_settings.get('notifylk_user_id') and app_settings.get('notifylk_api_key'))


def send_sms(recipient, message, raise_errors=False):
    """Send a text through notify.lk. Returns True if the gateway accepted it.

    With raise_errors=True a failure raises ServiceError with the reason instead.
    """
    def fail(reason):
        if raise_errors:
            raise ServiceError(reason)
        logger.warning("SMS not sent: %s", reason)
        return False

    number = normalize_phone(recipient)
    if not number or len(number) != 9 or set(number) == {'0'}:
        return fail("That is not a usable phone number.")
    if not app_settings.get('sms_enabled'):
        return fail("SMS is switched off in Settings.")
    if not (app_settings.get('notifylk_user_id') and app_settings.get('notifylk_api_key')):
        return fail("The notify.lk user ID and API key are not set.")

    payload = {
        "user_id": app_settings.get('notifylk_user_id'),
        "api_key": app_settings.get('notifylk_api_key'),
        "sender_id": app_settings.get('sms_sender_id'),
        "to": f"94{number}",
        "message": message
    }
    try:
        response = requests.get(config.NOTIFYLK_API_URL, params=payload, timeout=10)
    except requests.RequestException as exc:
        # Log the error type only: the request URL contains the API key.
        logger.error("SMS request failed: %s", type(exc).__name__)
        return fail("Could not reach notify.lk. Check the server's internet connection.")

    if response.status_code != 200:
        logger.error("SMS gateway answered HTTP %s", response.status_code)
        return fail(f"notify.lk answered with an error (HTTP {response.status_code}). Check the user ID and API key.")
    try:
        body = response.json()
    except ValueError:
        body = {}
    if isinstance(body, dict) and str(body.get('status', '')).lower() == 'error':
        logger.error("SMS gateway rejected the message")
        detail = body.get('message') or body.get('errors') or ''
        return fail(f"notify.lk rejected the message{': ' + str(detail) if detail else '.'}")
    return True


def send_email(to, subject, body):
    """Send a plain-text e-mail with the SMTP settings. Raises ServiceError on failure."""
    server = app_settings.get('mail_server')
    username = app_settings.get('mail_username')
    sender = app_settings.get('mail_sender') or username
    if not server or not sender:
        raise ServiceError("Email is not set up: enter the SMTP server and a username or From address.")

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = to
    message.set_content(body)

    security = app_settings.get('mail_security')
    port = app_settings.get('mail_port')
    try:
        if security == 'ssl':
            smtp = smtplib.SMTP_SSL(server, port, timeout=15, context=ssl.create_default_context())
        else:
            smtp = smtplib.SMTP(server, port, timeout=15)
        with smtp:
            if security == 'starttls':
                smtp.starttls(context=ssl.create_default_context())
            if username:
                smtp.login(username, app_settings.get('mail_password'))
            smtp.send_message(message)
    except smtplib.SMTPAuthenticationError:
        raise ServiceError("The email server refused the username or password.")
    except smtplib.SMTPSenderRefused:
        raise ServiceError(f"The email server will not send from {sender}. Check the From address.")
    except smtplib.SMTPRecipientsRefused:
        raise ServiceError(f"The email server will not send to {to}.")
    except (OSError, smtplib.SMTPException) as exc:
        logger.warning("SMTP failed: %s", type(exc).__name__)
        raise ServiceError("Could not send through the email server. Check the server, port and security.")


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
    body = f'''To reset your password please visit:
{url_for('user_blueprint.reset_token', token=token, _external=True)}

This link works for 30 minutes.
If you did not make this request then simply ignore this email.
'''
    send_email(user.email, 'Password Reset Request', body)
