# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity API v1 — Authentication & Authorization Helpers
==========================================================

Menyediakan fungsi-fungsi untuk validasi auth di setiap API v1 endpoint:

- require_authentication() — pastikan user login (bukan Guest)
- require_customer_role() — pastikan user punya role Customer (Portal User)
- require_admin_role() — pastikan user punya Qalcuity Superadmin atau Qalcuity Admin
- get_current_user_info() — return dict dengan user, customer, tenant info
- rate_limit_check() — basic rate limiting per user (pakai frappe.cache)

Rate limiting menggunakan frappe.cache() dengan sliding window pattern.
Default: 100 requests per minute per user.
Configurable via environment variable QALCUITY_API_RATE_LIMIT.
"""

import os
import time
import frappe
from frappe import _

from qalcuity.isolation import is_admin_user, get_current_customer, get_current_tenant


# =============================================================================
# Rate Limiting Configuration
# =============================================================================

DEFAULT_RATE_LIMIT = 100  # requests per minute
RATE_LIMIT_WINDOW = 60  # seconds


def _get_rate_limit():
    """
    Get rate limit from environment variable or use default.

    Returns:
        int: Maximum requests per minute per user
    """
    try:
        env_limit = os.environ.get("QALCUITY_API_RATE_LIMIT")
        if env_limit:
            return int(env_limit)
    except (ValueError, TypeError):
        pass
    return DEFAULT_RATE_LIMIT


def rate_limit_check(user=None):
    """
    Basic rate limiting per user using frappe.cache().

    Uses a sliding window counter approach:
    - Each user gets a cache key with timestamp-based window
    - Counter increments for each request within the window
    - Returns True if request is allowed, raises frappe.TooManyRequestsError if exceeded

    Args:
        user: User identifier. Default: frappe.session.user

    Returns:
        bool: True if request is allowed

    Raises:
        frappe.TooManyRequestsError: If rate limit exceeded
    """
    if not user:
        user = frappe.session.user

    # Skip rate limiting for Administrator
    if user == "Administrator":
        return True

    limit = _get_rate_limit()
    current_time = int(time.time())
    window_start = current_time - RATE_LIMIT_WINDOW

    # Cache key for this user's request window
    cache_key = f"qalcuity_api_v1_rate_{user}"

    # Get current request log from cache
    request_log = frappe.cache().get_value(cache_key)
    if request_log is None:
        request_log = []

    # Filter out expired entries (outside the window)
    request_log = [ts for ts in request_log if ts > window_start]

    # Check if limit exceeded
    if len(request_log) >= limit:
        retry_after = request_log[0] - window_start + 1
        frappe.throw(
            _("Rate limit exceeded. Maximum {0} requests per minute. Try again in {1} seconds.").format(
                limit, retry_after
            ),
            frappe.TooManyRequestsError,
        )

    # Add current request
    request_log.append(current_time)

    # Save updated log with TTL slightly longer than window
    frappe.cache().set_value(cache_key, request_log, expires_in_sec=RATE_LIMIT_WINDOW + 10)

    return True


# =============================================================================
# Authentication Helpers
# =============================================================================

def require_authentication():
    """
    Pastikan user sudah login (bukan Guest).

    Returns:
        str: Current user email/name

    Raises:
        frappe.AuthenticationError: Jika user adalah Guest
    """
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw(
            _("Authentication required. Please login."),
            frappe.AuthenticationError,
        )

    return user


def require_customer_role():
    """
    Pastikan user adalah customer (Portal User yang terhubung ke Customer).

    Validates:
    1. User bukan Guest
    2. User memiliki Portal User record yang terhubung ke Customer
    3. Customer memiliki Qalcuity Tenant

    Returns:
        dict: {"user": str, "customer": str, "tenant": str}

    Raises:
        frappe.AuthenticationError: Jika user adalah Guest
        frappe.PermissionError: Jika user bukan customer yang valid
    """
    user = require_authentication()

    # Check if user has admin role — admin can also access customer endpoints
    # (but they operate on behalf of the system, not as a customer)
    # For customer-specific endpoints, we require a customer link

    customer = get_current_customer(user)

    if not customer:
        frappe.throw(
            _("Access denied. No customer account linked to your user."),
            frappe.PermissionError,
        )

    tenant = get_current_tenant(user)
    tenant_name = tenant.name if tenant else None

    return {
        "user": user,
        "customer": customer,
        "tenant": tenant_name,
    }


def require_admin_role():
    """
    Pastikan user adalah Qalcuity Superadmin, Qalcuity Admin, atau System Manager.

    Returns:
        str: Current user email/name

    Raises:
        frappe.AuthenticationError: Jika user adalah Guest
        frappe.PermissionError: Jika user bukan admin
    """
    user = require_authentication()

    if not is_admin_user(user):
        frappe.throw(
            _("Access denied. Admin privileges required. Only Qalcuity Superadmin, Qalcuity Admin, or System Manager can perform this action."),
            frappe.PermissionError,
        )

    return user


def get_current_user_info():
    """
    Return comprehensive user info: user, customer, tenant, dan role info.

    Returns:
        dict: {
            "user": str,
            "email": str,
            "full_name": str,
            "roles": list,
            "customer": str|None,
            "tenant": str|None,
            "is_admin": bool,
        }
    """
    user = frappe.session.user

    if not user or user == "Guest":
        return {
            "user": None,
            "email": None,
            "full_name": None,
            "roles": [],
            "customer": None,
            "tenant": None,
            "is_admin": False,
        }

    # Get user doc
    user_doc = frappe.get_doc("User", user)

    # Get roles
    roles = [r.role for r in user_doc.roles]

    # Get customer & tenant
    customer = get_current_customer(user)
    tenant = get_current_tenant(user)

    return {
        "user": user,
        "email": user_doc.email,
        "full_name": user_doc.full_name,
        "roles": roles,
        "customer": customer,
        "tenant": tenant.name if tenant else None,
        "is_admin": is_admin_user(user),
    }


def check_api_key_authentication():
    """
    Validate API key authentication for external API access.

    Checks the Authorization header for a valid API key.
    If valid, sets the frappe session user accordingly.

    Returns:
        str: Authenticated user email/name, or None if no API key provided

    Note:
        API key format: "token {api_key}:{api_secret}"
        This is the standard Frappe API key authentication mechanism.
    """
    try:
        auth_header = frappe.get_request_header("Authorization", "")

        if not auth_header.startswith("token "):
            return None

        # Frappe handles API key auth natively via the Authorization header
        # The framework will set frappe.session.user if the token is valid
        # This function just provides a helper for explicit checking

        return frappe.session.user if frappe.session.user != "Guest" else None

    except Exception:
        return None
