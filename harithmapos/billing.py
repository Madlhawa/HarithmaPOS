"""Money and stock arithmetic for invoices and purchase orders.

Everything in here is a pure function on Decimals: no database, no Flask.
That keeps the rules in one place and makes them easy to unit test
(see tests/test_billing.py).
"""

from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal('0.01')
ZERO = Decimal('0')
HUNDRED = Decimal('100')


def to_decimal(value):
    """Turn None / '' / int / float / str / Decimal into a Decimal (None -> 0)."""
    if value is None or value == '':
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def money(value):
    """Round to cents the way a cashier would (half up)."""
    return to_decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def line_amounts(quantity, unit_cost, unit_price, discount_pct=0, additional_discount=0):
    """Work out the stored amounts for one invoice line.

    discount_pct        the item's automatic discount (percent of the line price)
    additional_discount a manual discount typed in at the counter (an amount)

    The combined discount can never be more than the line price.
    """
    quantity = to_decimal(quantity)
    total_cost = money(to_decimal(unit_cost) * quantity)
    total_price = money(to_decimal(unit_price) * quantity)

    auto_discount = money(total_price * to_decimal(discount_pct) / HUNDRED)
    auto_discount = min(max(auto_discount, ZERO), total_price)

    additional = max(money(additional_discount), ZERO)
    additional = min(additional, total_price - auto_discount)

    discount = auto_discount + additional
    return {
        'total_cost': total_cost,
        'total_price': total_price,
        'discount_amount': discount,
        'additional_discount': additional,
        'gross_price': total_price - discount,
    }


def invoice_totals(lines, bill_discount=0, paid=0):
    """Add up invoice lines.

    lines         iterable of objects with total_cost, total_price,
                  discount_amount and gross_price attributes
    bill_discount a discount on the whole bill (an amount)
    paid          what the customer has handed over so far

    Returns the values stored on the invoice head. Note the column names:
    total_price is the price before discounts, gross_price is what the
    customer actually owes.
    """
    total_cost = ZERO
    total_price = ZERO
    line_discount = ZERO
    line_gross = ZERO
    for line in lines:
        total_cost += to_decimal(line.total_cost)
        total_price += to_decimal(line.total_price)
        line_discount += to_decimal(line.discount_amount)
        line_gross += to_decimal(line.gross_price)

    bill_discount = min(max(money(bill_discount), ZERO), max(line_gross, ZERO))
    gross = money(line_gross - bill_discount)
    paid = money(paid)
    return {
        'total_cost': money(total_cost),
        'total_price': money(total_price),
        'total_discount': money(line_discount + bill_discount),
        'discount_amount': bill_discount,
        'gross_price': gross,
        'remaining_amount': gross - paid,
    }


def purchase_totals(lines, discount_pct=0, paid=0):
    """Add up purchase order lines.

    What we owe the supplier is based on cost, not on our selling price.
    total_price is kept as the retail value of the delivery, for reference.
    """
    total_cost = ZERO
    total_price = ZERO
    for line in lines:
        total_cost += to_decimal(line.total_cost)
        total_price += to_decimal(line.total_price)

    discount_pct = min(max(to_decimal(discount_pct), ZERO), HUNDRED)
    gross = money(total_cost - total_cost * discount_pct / HUNDRED)
    paid = money(paid)
    return {
        'total_cost': money(total_cost),
        'total_price': money(total_price),
        'gross_price': gross,
        'remaining_amount': gross - paid,
    }


def amount_to_record(paid, gross):
    """How much of the money handed over actually stays in the till.

    A customer may hand over Rs. 5,000 for a Rs. 4,300 bill. The payment
    ledger should show 4,300; the other 700 is change.
    """
    paid = max(money(paid), ZERO)
    gross = max(money(gross), ZERO)
    return min(paid, gross)
