"""What the customer asked for on a service invoice: a short checklist.

The floor supervisor types the requests when the vehicle comes in (one per
line). Staff tick each off when it is done, and the counter is warned about
anything still open before the invoice is completed.
"""
from harithmapos import db
from harithmapos.models import InvoiceRequest
from harithmapos.timeutils import utcnow

MAX_LENGTH = 200
MAX_PER_INVOICE = 30


def parse(text):
    """One request per line; blank lines and bullets are dropped, duplicates kept once."""
    seen, out = set(), []
    for line in (text or '').splitlines():
        line = line.strip().lstrip('-*•').strip()
        if not line or line.lower() in seen:
            continue
        seen.add(line.lower())
        out.append(line[:MAX_LENGTH])
    return out


def add(invoice, text, user=None):
    """Add the requests in `text` to the invoice. Returns how many were added. Does not commit."""
    room = MAX_PER_INVOICE - len(invoice.requests)
    existing = {r.description.lower() for r in invoice.requests}
    added = 0
    for description in parse(text):
        if added >= room:
            break
        if description.lower() in existing:
            continue
        invoice.requests.append(InvoiceRequest(
            description=description, created_dttm=utcnow(),
            created_by_id=user.id if user is not None else None))
        added += 1
    return added


def set_done(item, done, user=None):
    """Tick or untick one request. Does not commit."""
    done = bool(done)
    if item.done == done:
        return False
    item.done = done
    item.done_dttm = utcnow() if done else None
    item.done_by_id = user.id if (done and user is not None) else None
    return True


def confirm_message(invoice):
    """The question to ask before finishing while requests are still open, or None."""
    open_items = invoice.open_requests
    if not open_items:
        return None
    names = '\n'.join(f'- {r.description}' for r in open_items[:8])
    more = f'\n…and {len(open_items) - 8} more' if len(open_items) > 8 else ''
    return (f"{len(open_items)} of the customer's requests not ticked off yet:\n{names}{more}\n\n"
            "Finish anyway?")
