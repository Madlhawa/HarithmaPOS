"""Live updates for the dashboard and floor board (server-sent events).

The page opens GET /app/live and keeps it open. Every few seconds the server
works out a small fingerprint of everything those boards show (invoices and
their stages, customer requests, payments, item sales, items, bays, staff,
and the audit log). When it changes, it sends an event called "change" and
the page fetches its board again (see startLive in app.js).

Each open board holds one gunicorn thread (gunicorn_config.py uses threads
for this). The database connection is handed back between checks, and the
stream ends after a few minutes; the browser reconnects by itself.
"""
import time

from flask import Blueprint, Response, current_app, stream_with_context
from flask_login import login_required
from sqlalchemy import func, select

from harithmapos import db
from harithmapos.models import (
    AuditLog, Employee, InvoiceHead, InvoiceRequest, InvoiceStatusLog, Item, ItemInvoiceHead, Payment, WashBay,
)

live_blueprint = Blueprint('live_blueprint', __name__)


def fingerprint():
    """One cheap query whose answer changes whenever the dashboard or floor board would."""
    parts = [
        select(func.max(InvoiceHead.update_dttm)), select(func.count(InvoiceHead.id)),
        select(func.max(InvoiceStatusLog.id)),
        select(func.max(InvoiceRequest.id)), select(func.count(InvoiceRequest.id)),
        select(func.max(InvoiceRequest.done_dttm)),
        select(func.count(InvoiceRequest.id)).where(InvoiceRequest.done.is_(True)),
        select(func.max(Payment.id)), select(func.count(Payment.id)),
        select(func.max(ItemInvoiceHead.update_dttm)), select(func.count(ItemInvoiceHead.id)),
        select(func.max(Item.update_dttm)),
        select(func.count(WashBay.id)), select(func.max(Employee.update_dttm)), select(func.count(Employee.id)),
        select(func.max(AuditLog.id)),
    ]
    row = db.session.execute(select(*[p.scalar_subquery() for p in parts])).one()
    return tuple(str(value) for value in row)


def _events(max_seconds, every):
    yield 'retry: 3000\n\n'                      # reconnect after 3 s when the stream ends
    started = time.monotonic()
    last = None
    quiet_since = started
    while True:
        try:
            current = fingerprint()
        finally:
            db.session.remove()                  # give the connection back while we wait
        if last is not None and current != last:
            yield 'event: change\ndata: 1\n\n'
            quiet_since = time.monotonic()
        last = current
        now = time.monotonic()
        if now - started >= max_seconds:
            return
        if now - quiet_since >= 15:              # keep proxies from closing an idle connection
            yield ': ping\n\n'
            quiet_since = now
        time.sleep(every)


@live_blueprint.route('/app/live')
@login_required
def stream():
    max_seconds = current_app.config.get('LIVE_STREAM_SECONDS', 300)
    every = current_app.config.get('LIVE_CHECK_SECONDS', 3)
    response = Response(stream_with_context(_events(max_seconds, every)), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'     # nginx: send each event straight away
    return response
