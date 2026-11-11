"""Small text clean-up helpers used by forms and templates. Pure functions."""

import re


def strip_or_none(value):
    """Trim whitespace; turn empty strings into None so blanks are stored as NULL."""
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def normalize_phone(value):
    """Store Sri Lankan numbers as 9 digits (no leading 0, no +94).

    That is the form the SMS gateway needs ("94" + number), and it lets
    staff type a number however they like:
        0771234567, 077 123 4567, +94 77 123 4567, 771234567  ->  771234567
    Anything that does not look like a local number is returned with the
    punctuation removed so the form validator can reject it.
    """
    if value is None:
        return None
    digits = re.sub(r'\D', '', str(value))
    if not digits:
        return None
    if digits.startswith('0094'):
        digits = digits[4:]
    elif digits.startswith('94') and len(digits) == 11:
        digits = digits[2:]
    elif digits.startswith('0') and len(digits) == 10:
        digits = digits[1:]
    return digits


def format_phone(value):
    """Show a stored 9-digit number the way people read it: 077 123 4567."""
    if not value:
        return ''
    digits = re.sub(r'\D', '', str(value))
    if len(digits) == 9:
        return f"0{digits[:2]} {digits[2:5]} {digits[5:]}"
    return str(value)


def normalize_plate(value):
    """Vehicle numbers are stored upper-case with single spaces: 'cab-1234 ' -> 'CAB-1234'."""
    if value is None:
        return None
    value = re.sub(r'\s+', ' ', str(value)).strip().upper()
    return value or None
