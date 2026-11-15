"""Money arithmetic: the one place money is rounded.

Rules (used by billing, the ledger, payroll and the screens):

* Money is a Decimal in rupees with two places, never a float. The database
  columns are Numeric(10, 2); quantities are Numeric(10, 4).
* `money()` rounds to the cent, half up (2.345 -> 2.35), the way a cashier
  would. Every stored amount is rounded when it is worked out: each line's
  price, cost and discounts; each payroll component; each payment.
* Totals are sums of those rounded amounts and are never rounded again, so a
  bill always adds up to its lines on paper.
* A percentage discount is worked out on the rounded line price, then rounded.
  A bill discount comes off after the lines and can't exceed them.
* Floats appear only at the very edge: chart data sent to the browser
  (the JSON encoder turns Decimals into numbers there).

Everything here is a pure function on Decimals: no database, no Flask
(see tests/test_billing.py).
"""

from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal('0.01')
ZERO = Decimal('0')
HUNDRED = Decimal('100')


def to_decimal(value):
    """Turn None / '' / int / str / Decimal into a Decimal (None -> 0).

    A float is converted through its shortest text form (0.1 -> Decimal('0.1')),
    so the binary error of the float does not leak in.
    """
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


def invoice_totals(lines, bill_discount=0):
    """Add up invoice lines.

    lines         iterable of objects with total_cost, total_price,
                  discount_amount and gross_price attributes
    bill_discount a discount on the whole bill (an amount)

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
    return {
        'total_cost': money(total_cost),
        'total_price': money(total_price),
        'total_discount': money(line_discount + bill_discount),
        'discount_amount': bill_discount,
        'gross_price': gross,
    }


def purchase_totals(lines, discount_pct=0):
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
    return {
        'total_cost': money(total_cost),
        'total_price': money(total_price),
        'gross_price': gross,
    }
