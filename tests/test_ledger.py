"""The money ledger: entries are only ever added; mistakes are reversed, never edited or deleted."""
from datetime import timedelta
from decimal import Decimal

import pytest

from harithmapos import db, ledger
from harithmapos.models import Customer, Payment
from harithmapos.timeutils import utcnow


def _entry(app, **kw):
    with app.app_context():
        entry = ledger.post(kw.pop('type', 'expense'), kw.pop('amount', 1000), kw.pop('method', 'cash'),
                            remarks=kw.pop('remarks', 'Electricity'), **kw)
        db.session.commit()
        return entry.id


def test_entries_cannot_be_changed_or_deleted(app):
    entry_id = _entry(app)
    with app.app_context():
        entry = db.session.get(Payment, entry_id)
        entry.payment_amount = 900
        with pytest.raises(ledger.LedgerError):
            db.session.flush()
        db.session.rollback()
        db.session.delete(db.session.get(Payment, entry_id))
        with pytest.raises(ledger.LedgerError):
            db.session.flush()
        db.session.rollback()
        assert db.session.get(Payment, entry_id).payment_amount == 1000


def test_type_fixes_the_direction_and_bad_entries_are_refused(app):
    with app.app_context():
        assert ledger.post('income', 50, 'qr', remarks='Scrap').payment_direction == 'in'
        assert ledger.post('withdrawal', 50, 'cash', remarks='Owner').payment_direction == 'out'
        for args in (('expense', 0, 'cash'), ('expense', -5, 'cash'), ('expense', 10, 'credit'), ('gift', 10, 'cash')):
            with pytest.raises(ledger.LedgerError):
                ledger.post(*args)
        db.session.rollback()


def test_reversal_cancels_once_and_cannot_itself_be_reversed(app, owner):
    entry_id = _entry(app)
    owner.post(f'/app/payment/{entry_id}/reverse', data={'reason': ''})                  # a reason is required
    with app.app_context():
        assert Payment.query.count() == 1
    owner.post(f'/app/payment/{entry_id}/reverse', data={'reason': 'Entered twice'})
    owner.post(f'/app/payment/{entry_id}/reverse', data={'reason': 'Again'})
    with app.app_context():
        original, reversal = Payment.query.order_by(Payment.id).all()
        assert (reversal.reverses_id, reversal.payment_direction, reversal.payment_type) == (original.id, 'in', 'expense')
        assert original.is_reversed and reversal.remarks == f'Reversal of #{original.id}: Entered twice'
        reversal_id = reversal.id
    owner.post(f'/app/payment/{reversal_id}/reverse', data={'reason': 'Undo the undo'})
    with app.app_context():
        assert Payment.query.count() == 2
    page = owner.get('/app/payment').get_data(as_text=True)
    assert f'Reversed by #{reversal_id}' in page and f'Reverses #{entry_id}' in page


def test_reversing_a_customer_payment_reopens_the_balance(app, owner):
    from tests_helpers_invoice import make_completed_invoice
    inv_id = make_completed_invoice(app, gross=4000)
    with app.app_context():
        from harithmapos.models import InvoiceHead
        inv = db.session.get(InvoiceHead, inv_id)
        entry = ledger.pay_document(inv, 4000, 'cash')
        db.session.commit()
        assert inv.balance == 0
        entry_id = entry.id
    owner.post(f'/app/payment/{entry_id}/reverse', data={'reason': 'Card declined'})
    with app.app_context():
        from harithmapos.models import InvoiceHead
        assert db.session.get(InvoiceHead, inv_id).balance == Decimal('4000')


def test_dashboard_totals_net_refunds_and_reversals(app):
    with app.app_context():
        now = utcnow()
        lo, hi = now - timedelta(hours=1), now + timedelta(hours=1)
        cust = Customer.query.first()
        sale = ledger.post('sale', 3000, 'cash', customer_id=cust.id)
        ledger.post('sale_refund', 500, 'cash', customer_id=cust.id)
        ledger.reverse(sale, 'Wrong invoice')
        ledger.post('sale', 1200, 'card', customer_id=cust.id)
        ledger.post('expense', 800, 'cash', remarks='Water bill')
        ledger.post('income', 100, 'cash', remarks='Scrap')          # neither collected nor paid out
        db.session.commit()
        assert ledger.collected(lo, hi) == Decimal('700.00')        # 3000 - 500 - 3000 + 1200
        assert ledger.paid_out(lo, hi) == Decimal('800.00')


def test_manual_entries_staff_and_owner(app, staff, owner):
    form = {'payment_type': 'expense', 'payment_amount': '250', 'payment_method': 'cash', 'remarks': 'Tea'}
    staff.post('/app/payment/create', data=form)
    staff.post('/app/payment/create', data={**form, 'payment_type': 'income', 'remarks': 'Scrap metal'})
    owner.post('/app/payment/create', data=form)
    owner.post('/app/payment/create', data={**form, 'payment_type': 'sale'})      # only via an invoice
    owner.post('/app/payment/create', data={**form, 'remarks': ''})               # must say what it was for
    with app.app_context():
        rows = [(p.payment_type, p.created_by.name) for p in Payment.query.order_by(Payment.id)]
    assert rows == [('income', 'Sam Staff'), ('expense', 'Olivia Owner')]
    staff_page = staff.get('/app/payment').get_data(as_text=True)
    assert 'Scrap metal' in staff_page and 'Tea' not in staff_page and 'Reverse' not in staff_page
