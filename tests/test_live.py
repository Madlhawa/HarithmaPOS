"""In-page updates (htmx) and live updates (server-sent events) for the dashboard and floor board."""
import pytest

from harithmapos import config, db
from harithmapos.models import Customer, Employee, InvoiceHead, InvoiceRequest, Item, Payment, Vehicle, WashBay
from harithmapos.views.live import routes as live


@pytest.fixture
def job(app):
    with app.app_context():
        cust = Customer.query.first()
        bay, emp = WashBay(name='Bay 1'), Employee(name='Ajith', wage=1, active=True)
        car = Vehicle(number='CAB-1234', owner_id=cust.id)
        db.session.add_all([bay, emp, car]); db.session.flush()
        inv = InvoiceHead(customer_id=cust.id, vehicle_id=car.id, washbay_id=bay.id, employee_id=emp.id,
                          service_status=config.SERVICE_STATUS_WAITING, total_cost=0, gross_price=0)
        db.session.add(inv); db.session.flush()
        req = InvoiceRequest(invoice_id=inv.id, description='Full wash')
        db.session.add(req); db.session.commit()
        return {'inv': inv.id, 'req': req.id, 'bay': bay.id, 'emp': emp.id, 'item': Item.query.first().id}


def _print(app):
    with app.app_context():
        return live.fingerprint()


def test_fingerprint_changes_with_what_the_boards_show(app, staff, job):
    before = _print(app)
    assert _print(app) == before                                     # nothing changed, nothing to send
    staff.post(f"/app/floor/{job['inv']}/move", data={'status': config.SERVICE_STATUS_VACUUMING})
    after_move = _print(app)
    assert after_move != before
    staff.post(f"/app/invoice/request/{job['req']}/done", data={'done': '1'})
    after_tick = _print(app)
    assert after_tick != after_move
    with app.app_context():
        db.session.add(Payment(payment_amount=100, payment_direction='in', payment_method='cash', payment_type='general'))
        db.session.commit()
    assert _print(app) != after_tick


def test_stream_needs_sign_in(app):
    assert app.test_client().get('/app/live').status_code == 302


def test_stream_headers_and_end(app, staff):
    app.config['LIVE_STREAM_SECONDS'] = 0          # one check, then the stream ends
    response = staff.get('/app/live?board=floor')
    assert response.status_code == 200
    assert response.mimetype == 'text/event-stream'
    assert response.headers['X-Accel-Buffering'] == 'no' and response.headers['Cache-Control'] == 'no-cache'
    body = response.get_data(as_text=True)
    assert body.startswith('retry: 3000') and 'event: change' not in body


def test_stream_sends_change_only_when_something_changed(app, monkeypatch):
    prints = [('a',), ('a',), ('b',), ('b',), ('c',)]
    calls = []

    def fake():
        calls.append(1)
        return prints[min(len(calls), len(prints)) - 1]
    monkeypatch.setattr(live, 'fingerprint', fake)
    monkeypatch.setattr(live.time, 'sleep', lambda s: None)
    with app.app_context():
        stream = live._events(max_seconds=3600, every=0)
        events = [next(stream) for _ in range(1 + 2)]          # retry line, then the two changes
    assert events[1:] == ['event: change\ndata: 1\n\n'] * 2
    assert len(calls) == 5                                     # a -> a (nothing), a -> b, b -> b (nothing), b -> c


def test_pages_carry_the_live_and_in_page_markers(app, staff, job):
    dash = staff.get('/app/dashboard').get_data(as_text=True)
    assert 'data-live="dashboard"' in dash and 'id="dash-live" data-region data-live-region' in dash
    assert 'htmx.org@2.0.4' in dash and 'id="flash-area"' in dash
    floor = staff.get('/app/floor').get_data(as_text=True)
    assert 'data-live="floor"' in floor and 'id="fl-live" data-region data-live-region' in floor
    assert 'data-region-target="fl-live"' in floor
    inv = staff.get(f"/app/invoice/head/{job['inv']}").get_data(as_text=True)
    assert 'id="lines" data-region' in inv and 'id="requests" data-region' in inv
    assert 'id="bill-totals" data-sync' in inv and 'id="complete-slot"' in inv


def test_background_post_gets_the_same_page_back(staff, job):
    """htmx follows the usual redirect: the page that comes back holds the updated region."""
    response = staff.post(f"/app/invoice/detail/add/{job['inv']}", data={'item_id': job['item'], 'quantity': '1'},
                          headers={'HX-Request': 'true'}, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200 and 'id="lines" data-region' in html and 'Engine oil' in html
