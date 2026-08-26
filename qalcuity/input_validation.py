# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Input Validation utilities for Qalcuity ERP.
Sanitizes and validates user inputs across all API endpoints.
"""

import re
import html


# =============================================================================
# Text Sanitization
# =============================================================================

def sanitize_text(value, max_length=500):
    """
    Sanitize text input — strip whitespace, limit length.

    Args:
        value: Input value
        max_length: Maximum allowed length

    Returns:
        str: Sanitized text
    """
    if not value:
        return value
    value = str(value).strip()
    if len(value) > max_length:
        value = value[:max_length]
    return value


def sanitize_html(value):
    """
    Strip HTML tags from input.

    Args:
        value: Input value

    Returns:
        str: Text without HTML tags
    """
    if not value:
        return value
    value = html.unescape(str(value))
    # Strip all HTML tags
    value = re.sub(r'<[^>]+>', '', value)
    return value.strip()


# =============================================================================
# Field Validation
# =============================================================================

def validate_email(email):
    """
    Validate email format.

    Args:
        email: Email address

    Returns:
        bool: True if valid format
    """
    if not email:
        return False
    email = str(email).strip().lower()
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone):
    """
    Validate phone number format (Indonesia).

    Args:
        phone: Phone number

    Returns:
        bool: True if valid format
    """
    if not phone:
        return False
    # Remove spaces, dashes, parentheses
    phone = re.sub(r'[\s\-\(\)]', '', str(phone))
    # Indonesia: 08xx, +628xx, 628xx
    pattern = r'^(\+62|62|0)8[1-9][0-9]{7,11}$'
    return bool(re.match(pattern, phone))


def validate_password(password):
    """
    Validate password strength — min 8 chars + letter + number.

    Args:
        password: Password string

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if not password:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r'[a-zA-Z]', password):
        return False, "Password must contain at least one letter."
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number."
    return True, None


def validate_amount(amount):
    """
    Validate monetary amount.

    Args:
        amount: Amount value

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    try:
        amount = float(amount)
        if amount < 0:
            return False, "Amount cannot be negative."
        if amount > 999999999999:
            return False, "Amount is too large."
        return True, None
    except (ValueError, TypeError):
        return False, "Invalid amount."


def validate_name(name, max_length=100):
    """
    Validate name field — check not empty, reasonable length, no dangerous chars.

    Args:
        name: Name string
        max_length: Maximum allowed length

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if not name or not str(name).strip():
        return False, "Name is required."
    name = str(name).strip()
    if len(name) > max_length:
        return False, "Name is too long (maximum {0} characters).".format(max_length)
    if len(name) < 2:
        return False, "Name must be at least 2 characters."
    return True, None


def validate_reference_number(ref_number):
    """
    Validate payment reference number — alphanumeric + common separators only.

    Args:
        ref_number: Reference number string

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if not ref_number:
        return True, None  # Optional field

    ref_number = str(ref_number).strip()

    # Only allow alphanumeric, dash, dot, slash
    if not re.match(r'^[a-zA-Z0-9\-\.\/]+$', ref_number):
        return False, "Reference number contains invalid characters."

    if len(ref_number) > 50:
        return False, "Reference number is too long (maximum 50 characters)."

    return True, None


def validate_reason(reason, max_length=500):
    """
    Validate reason/notes field.

    Args:
        reason: Reason string
        max_length: Maximum allowed length

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if not reason:
        return True, None  # Optional field

    reason = str(reason).strip()
    if len(reason) > max_length:
        return False, "Reason is too long (maximum {0} characters).".format(max_length)

    return True, None


# =============================================================================
# Search & Query Sanitization
# =============================================================================

def sanitize_search_query(query):
    """
    Sanitize search query — prevent SQL injection in LIKE.

    Args:
        query: Search query string

    Returns:
        str: Sanitized query
    """
    if not query:
        return ""
    query = str(query).strip()
    # Remove SQL wildcards that user shouldn't use
    query = query.replace('%', '').replace('_', '')
    if len(query) > 100:
        query = query[:100]
    return query


def validate_date_range(from_date, to_date):
    """
    Validate date range — start date not after end date.

    Args:
        from_date: Start date
        to_date: End date

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    from frappe.utils import getdate, date_diff
    try:
        f = getdate(from_date) if from_date else None
        t = getdate(to_date) if to_date else None
        if f and t and f > t:
            return False, "Start date cannot be after end date."
        return True, None
    except Exception:
        return False, "Invalid date format."
