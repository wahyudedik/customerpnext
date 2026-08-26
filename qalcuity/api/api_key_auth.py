# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
API Key Authentication Middleware for Qalcuity ERP.
Provides authentication via API key/secret headers for external integrations.

Usage in endpoint:
    from qalcuity.api.api_key_auth import authenticate_api_key
    customer = authenticate_api_key()
    if not customer:
        frappe.throw("Invalid API key", frappe.AuthenticationError)
"""

import frappe


def authenticate_api_key():
    """
    Middleware untuk validasi API key dari request headers.

    Headers:
        X-Qalcuity-Key: API key
        X-Qalcuity-Secret: API secret

    Returns:
        dict: Customer info jika valid, None jika tidak
            {
                "customer": "CUST-001",
                "key_name": "QKEY-20260826-0001",
                "permissions": "Read Only"
            }
    """
    api_key = frappe.get_request_header("X-Qalcuity-Key")
    api_secret = frappe.get_request_header("X-Qalcuity-Secret")

    if not api_key or not api_secret:
        return None

    # Find key
    key_doc = frappe.db.get_value(
        "Qalcuity Api Key",
        {"api_key": api_key, "is_active": 1},
        ["name", "api_secret", "customer", "expires_at", "allowed_ips", "permissions_level"],
        as_dict=True
    )

    if not key_doc:
        return None

    # Check expiry
    if key_doc.expires_at and key_doc.expires_at < frappe.utils.now_datetime():
        return None

    # Verify secret
    stored_secret = frappe.get_doc("Qalcuity Api Key", key_doc.name).get_password(
        "api_secret", raise_exception=False
    )
    if stored_secret != api_secret:
        return None

    # Check IP whitelist
    if key_doc.allowed_ips:
        allowed = [ip.strip() for ip in key_doc.allowed_ips.split(",") if ip.strip()]
        client_ip = frappe.local.request_ip
        if client_ip and client_ip not in allowed:
            return None

    # Update last_used
    frappe.db.set_value("Qalcuity Api Key", key_doc.name, "last_used", frappe.utils.now_datetime())
    frappe.db.commit()

    return {
        "customer": key_doc.customer,
        "key_name": key_doc.name,
        "permissions": key_doc.permissions_level,
    }


def require_api_key():
    """
    Stricter version — throws error if API key is invalid.

    Returns:
        dict: Customer info

    Raises:
        frappe.AuthenticationError: If API key is invalid
    """
    result = authenticate_api_key()
    if not result:
        frappe.throw(
            frappe._("Invalid or missing API key. Provide X-Qalcuity-Key and X-Qalcuity-Secret headers."),
            frappe.AuthenticationError
        )
    return result


def check_write_permission(auth_info):
    """
    Check if the authenticated API key has write permission.

    Args:
        auth_info: Return value from authenticate_api_key()

    Returns:
        bool: True if write is allowed

    Raises:
        frappe.PermissionError: If write is not allowed
    """
    if not auth_info or auth_info.get("permissions") == "Read Only":
        frappe.throw(
            frappe._("This API key does not have write permission."),
            frappe.PermissionError
        )
    return True
