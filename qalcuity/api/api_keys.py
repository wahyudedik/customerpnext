# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
API Key Management endpoints for Qalcuity ERP.
Provides whitelisted methods for API key CRUD operations.
"""

import frappe
from frappe import _


@frappe.whitelist()
def generate_api_key(key_name, permissions="Read Only", expires_at=None, allowed_ips=None):
    """
    Customer generate API key baru.

    Args:
        key_name: Nama identifikasi API key (misal: "Production API")
        permissions: "Read Only" atau "Read & Write"
        expires_at: Optional expiry datetime
        allowed_ips: Optional comma-separated IP whitelist

    Returns:
        dict: Created API key document dengan api_secret (hanya ditampilkan sekali)
    """
    user = frappe.session.user

    # Get customer for current user
    customer = frappe.db.get_value("Portal User", {"user": user}, "parent")

    # Admin/superadmin can create for any customer (via customer param)
    if not customer:
        user_roles = frappe.get_roles(user)
        admin_roles = ["System Manager", "Qalcuity Superadmin", "Qalcuity Admin"]
        if not any(role in user_roles for role in admin_roles):
            frappe.throw(_("No customer account found for this user."))

    # Validate key_name
    if not key_name or not key_name.strip():
        frappe.throw(_("Key name is required."))

    # Validate permissions option
    if permissions not in ["Read Only", "Read & Write"]:
        frappe.throw(_("Invalid permissions level."))

    # Validate allowed_ips format if provided
    if allowed_ips and allowed_ips.strip():
        ip_list = [ip.strip() for ip in allowed_ips.split(",") if ip.strip()]
        for ip in ip_list:
            # Basic IP validation (IPv4 or CIDR)
            parts = ip.split("/")
            if len(parts) > 2:
                frappe.throw(_("Invalid IP format: {0}").format(ip))
            ip_parts = parts[0].split(".")
            if len(ip_parts) != 4:
                frappe.throw(_("Invalid IP format: {0}").format(ip))
            for part in ip_parts:
                if not part.isdigit() or int(part) > 255:
                    frappe.throw(_("Invalid IP format: {0}").format(ip))

    # Create API key
    doc = frappe.get_doc({
        "doctype": "Qalcuity Api Key",
        "customer": customer,
        "key_name": key_name.strip(),
        "permissions_level": permissions,
        "expires_at": expires_at if expires_at else None,
        "allowed_ips": allowed_ips if allowed_ips and allowed_ips.strip() else None,
    })
    doc.insert(ignore_permissions=True)

    # Get the raw secret (only available once)
    secret_raw = doc.get_password("api_secret", raise_exception=False)

    frappe.db.commit()

    return {
        "name": doc.name,
        "api_key": doc.api_key,
        "api_secret": secret_raw,
        "key_name": doc.key_name,
        "permissions": doc.permissions_level,
        "expires_at": doc.expires_at,
        "is_active": doc.is_active,
    }


@frappe.whitelist()
def get_my_api_keys():
    """
    Customer melihat semua API keys mereka.

    Returns:
        list: List of API key documents (tanpa secret)
    """
    user = frappe.session.user
    customer = frappe.db.get_value("Portal User", {"user": user}, "parent")

    if not customer:
        # Admin/superadmin — return all
        user_roles = frappe.get_roles(user)
        admin_roles = ["System Manager", "Qalcuity Superadmin", "Qalcuity Admin"]
        if any(role in user_roles for role in admin_roles):
            keys = frappe.get_all(
                "Qalcuity Api Key",
                fields=[
                    "name", "customer", "key_name", "api_key",
                    "is_active", "last_used", "expires_at",
                    "permissions_level", "allowed_ips", "creation"
                ],
                order_by="creation desc"
            )
            # Mask api_key for display
            for key in keys:
                key["api_key_masked"] = _mask_key(key["api_key"])
            return keys
        frappe.throw(_("No customer account found for this user."))

    keys = frappe.get_all(
        "Qalcuity Api Key",
        filters={"customer": customer},
        fields=[
            "name", "customer", "key_name", "api_key",
            "is_active", "last_used", "expires_at",
            "permissions_level", "allowed_ips", "creation"
        ],
        order_by="creation desc"
    )

    # Mask api_key for display
    for key in keys:
        key["api_key_masked"] = _mask_key(key["api_key"])

    return keys


@frappe.whitelist()
def revoke_api_key(api_key_name):
    """
    Customer revoke (deactivate) API key.

    Args:
        api_key_name: Name of the API key document

    Returns:
        dict: Updated API key info
    """
    if not frappe.db.exists("Qalcuity Api Key", api_key_name):
        frappe.throw(_("API key not found."))

    doc = frappe.get_doc("Qalcuity Api Key", api_key_name)

    # Permission check
    user = frappe.session.user
    if user != "Administrator":
        user_roles = frappe.get_roles(user)
        admin_roles = ["System Manager", "Qalcuity Superadmin", "Qalcuity Admin"]
        if not any(role in user_roles for role in admin_roles):
            customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
            if customer != doc.customer:
                frappe.throw(_("You can only revoke your own API keys."))

    if not doc.is_active:
        frappe.throw(_("This API key is already revoked."))

    doc.is_active = 0
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    frappe.get_doc({
        "doctype": "Qalcuity Audit Log",
        "user": frappe.session.user,
        "action": "API Key Revoked",
        "target_doctype": "Qalcuity Api Key",
        "target_name": doc.name,
        "details": "Revoked API key: {0}".format(doc.key_name),
    }).insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "name": doc.name,
        "key_name": doc.key_name,
        "is_active": doc.is_active,
    }


@frappe.whitelist()
def delete_api_key(api_key_name):
    """
    Customer hapus API key.

    Args:
        api_key_name: Name of the API key document

    Returns:
        dict: Status
    """
    if not frappe.db.exists("Qalcuity Api Key", api_key_name):
        frappe.throw(_("API key not found."))

    doc = frappe.get_doc("Qalcuity Api Key", api_key_name)

    # Permission check
    user = frappe.session.user
    if user != "Administrator":
        user_roles = frappe.get_roles(user)
        admin_roles = ["System Manager", "Qalcuity Superadmin", "Qalcuity Admin"]
        if not any(role in user_roles for role in admin_roles):
            customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
            if customer != doc.customer:
                frappe.throw(_("You can only delete your own API keys."))

    key_name = doc.key_name
    frappe.delete_doc("Qalcuity Api Key", api_key_name, ignore_permissions=True)
    frappe.db.commit()

    frappe.get_doc({
        "doctype": "Qalcuity Audit Log",
        "user": frappe.session.user,
        "action": "API Key Deleted",
        "target_doctype": "Qalcuity Api Key",
        "target_name": api_key_name,
        "details": "Deleted API key: {0}".format(key_name),
    }).insert(ignore_permissions=True)
    frappe.db.commit()

    return {"status": "deleted", "name": api_key_name}


@frappe.whitelist(allow_guest=False)
def validate_api_key(api_key, api_secret):
    """
    Validasi API key — dipanggil oleh external client.

    Args:
        api_key: The API key string
        api_secret: The API secret string

    Returns:
        dict: Customer info jika valid, None jika tidak
    """
    if not api_key or not api_secret:
        frappe.throw(_("API key and secret are required."), frappe.AuthenticationError)

    # Find key
    key_doc = frappe.db.get_value(
        "Qalcuity Api Key",
        {"api_key": api_key, "is_active": 1},
        ["name", "api_secret", "customer", "expires_at", "allowed_ips", "permissions_level"],
        as_dict=True
    )

    if not key_doc:
        frappe.throw(_("Invalid or inactive API key."), frappe.AuthenticationError)

    # Check expiry
    if key_doc.expires_at and key_doc.expires_at < frappe.utils.now_datetime():
        frappe.throw(_("API key has expired."), frappe.AuthenticationError)

    # Verify secret
    stored_secret = frappe.get_doc("Qalcuity Api Key", key_doc.name).get_password("api_secret", raise_exception=False)
    if stored_secret != api_secret:
        frappe.throw(_("Invalid API key or secret."), frappe.AuthenticationError)

    # Check IP whitelist
    if key_doc.allowed_ips:
        allowed = [ip.strip() for ip in key_doc.allowed_ips.split(",") if ip.strip()]
        client_ip = frappe.local.request_ip
        if client_ip and client_ip not in allowed:
            frappe.throw(_("IP address not allowed."), frappe.AuthenticationError)

    # Update last_used
    frappe.db.set_value("Qalcuity Api Key", key_doc.name, "last_used", frappe.utils.now_datetime())
    frappe.db.commit()

    # Get customer info
    customer_name = frappe.db.get_value("Customer", key_doc.customer, "customer_name")

    return {
        "customer": key_doc.customer,
        "customer_name": customer_name,
        "key_name": key_doc.name,
        "permissions": key_doc.permissions_level,
    }


def _mask_key(api_key):
    """Mask API key untuk display: qk_abc...xyz"""
    if not api_key or len(api_key) <= 12:
        return api_key
    return api_key[:9] + "..." + api_key[-6:]
