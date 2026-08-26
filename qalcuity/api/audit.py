# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity Audit Log API
========================
API endpoints untuk audit trail system.

Endpoints:
- log_action() — create audit log entry (internal use)
- get_audit_logs() — get audit logs (admin only)
- get_my_audit_logs() — get user's own audit logs
- on_payment_update() — doc_event hook for Qalcuity Payment
- on_subscription_update() — doc_event hook for Qalcuity Subscription
"""

import frappe
from frappe import _
import json


def log_action(action, doc_type=None, doc_name=None, details=None):
    """
    Buat audit log entry.

    Fungsi ini dipanggil internal oleh sistem (hooks, doc_events, dll).
    Tidak perlu @frappe.whitelisted karena dipanggil dari server-side.

    Args:
        action: Jenis aksi (Login, Logout, Payment Submit, dll)
        doc_type: Nama DocType yang terkait (optional)
        doc_name: Nama dokumen yang terkait (optional)
        details: Detail tambahan sebagai string/JSON (optional)

    Returns:
        str: Name dari audit log entry yang dibuat
    """
    try:
        user = frappe.session.user
        ip_address = frappe.local.request_ip if hasattr(frappe.local, 'request_ip') else None

        # Get IP from request headers if not available
        if not ip_address:
            try:
                ip_address = frappe.local.request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            except (AttributeError, IndexError):
                ip_address = None

        # Convert details dict to JSON string if needed
        if details and isinstance(details, dict):
            details = json.dumps(details, default=str)

        log = frappe.get_doc({
            "doctype": "Qalcuity Audit Log",
            "user": user,
            "action": action,
            "doc_type": doc_type,
            "doc_name": doc_name,
            "details": details,
            "ip_address": ip_address,
            "timestamp": frappe.utils.now_datetime(),
        })
        log.insert(ignore_permissions=True)
        frappe.db.commit()

        return log.name

    except Exception as e:
        frappe.log_error(
            message=f"Failed to create audit log: {str(e)}",
            title="Qalcuity Audit Log Error",
        )
        return None


@frappe.whitelist()
def get_audit_logs(filters=None, limit_page_length=20, start=0, order_by="timestamp desc"):
    """
    Mendapatkan daftar audit logs (admin only).

    Args:
        filters: JSON string filters (optional)
        limit_page_length: Jumlah baris per halaman (default: 20)
        start: Offset untuk pagination (default: 0)
        order_by: Ordering (default: timestamp desc)

    Returns:
        dict: {data: [...], total: int}
    """
    # Permission check — hanya admin
    _require_admin()

    conditions = []
    values = {}

    if filters:
        if isinstance(filters, str):
            try:
                filters = json.loads(filters)
            except json.JSONDecodeError:
                filters = {}

        if filters.get("user"):
            conditions.append("user = @user")
            values["user"] = filters["user"]

        if filters.get("action"):
            conditions.append("action = @action")
            values["action"] = filters["action"]

        if filters.get("doc_type"):
            conditions.append("doc_type = @doc_type")
            values["doc_type"] = filters["doc_type"]

        if filters.get("from_date"):
            conditions.append("timestamp >= @from_date")
            values["from_date"] = filters["from_date"]

        if filters.get("to_date"):
            conditions.append("timestamp <= @to_date")
            values["to_date"] = filters["to_date"] + " 23:59:59"

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Get total count
    total = frappe.db.sql(
        f"SELECT COUNT(*) FROM `tabQalcuity Audit Log` WHERE {where_clause}",
        values,
        as_dict=True,
    )[0].get("count", 0)

    # Get data
    data = frappe.db.sql(
        f"""
        SELECT name, user, action, doc_type, doc_name, ip_address, timestamp, details
        FROM `tabQalcuity Audit Log`
        WHERE {where_clause}
        ORDER BY {order_by}
        LIMIT %s OFFSET %s
        """,
        values.values() + (limit_page_length, int(start)),
        as_dict=True,
    )

    return {
        "data": data,
        "total": total,
    }


@frappe.whitelisted()
def get_my_audit_logs(limit_page_length=20, start=0):
    """
    Mendapatkan audit logs untuk user yang sedang login.

    Args:
        limit_page_length: Jumlah baris per halaman (default: 20)
        start: Offset untuk pagination (default: 0)

    Returns:
        dict: {data: [...], total: int}
    """
    user = frappe.session.user

    if user in ("Guest", "Administrator"):
        frappe.throw(_("Access denied."))

    conditions = "user = %s"
    values = (user,)

    # Get total count
    total = frappe.db.sql(
        f"SELECT COUNT(*) FROM `tabQalcuity Audit Log` WHERE {conditions}",
        values,
        as_dict=True,
    )[0].get("count", 0)

    # Get data
    data = frappe.db.sql(
        f"""
        SELECT name, action, doc_type, doc_name, timestamp, details
        FROM `tabQalcuity Audit Log`
        WHERE {conditions}
        ORDER BY timestamp DESC
        LIMIT %s OFFSET %s
        """,
        values + (limit_page_length, int(start)),
        as_dict=True,
    )

    return {
        "data": data,
        "total": total,
    }


# =============================================================================
# Doc Event Hooks — Auto-logging untuk Payment & Subscription
# =============================================================================

def on_payment_update(doc, method):
    """
    Hook: Qalcuity Payment on_update.
    Auto-log payment approve/reject/submit actions.
    """
    if not doc.is_new():
        # Check status change
        old_status = doc.get_doc_before_save()
        if old_status:
            old_status_val = old_status.get("status")
        else:
            old_status_val = None

        new_status = doc.status

        if old_status_val != new_status:
            if new_status == "Approved":
                log_action(
                    action="Payment Approve",
                    doc_type="Qalcuity Payment",
                    doc_name=doc.name,
                    details=json.dumps({
                        "subscription": doc.subscription,
                        "amount": doc.amount,
                        "reviewed_by": doc.reviewed_by,
                    }, default=str),
                )
            elif new_status == "Rejected":
                log_action(
                    action="Payment Reject",
                    doc_type="Qalcuity Payment",
                    doc_name=doc.name,
                    details=json.dumps({
                        "subscription": doc.subscription,
                        "amount": doc.amount,
                        "rejection_reason": doc.rejection_reason,
                        "reviewed_by": doc.reviewed_by,
                    }, default=str),
                )
    else:
        # New payment submitted
        log_action(
            action="Payment Submit",
            doc_type="Qalcuity Payment",
            doc_name=doc.name,
            details=json.dumps({
                "subscription": doc.subscription,
                "amount": doc.amount,
            }, default=str),
        )


def on_subscription_update(doc, method):
    """
    Hook: Qalcuity Subscription on_update.
    Auto-log subscription status changes.
    """
    if doc.is_new():
        return

    old_doc = doc.get_doc_before_save()
    if not old_doc:
        return

    old_status = old_doc.get("status")
    new_status = doc.status

    if old_status == new_status:
        return

    # Map status to action
    action_map = {
        "Active": "Subscription Activate",
        "Suspended": "Subscription Suspend",
        "Cancelled": "Subscription Cancel",
    }

    action = action_map.get(new_status)
    if action:
        log_action(
            action=action,
            doc_type="Qalcuity Subscription",
            doc_name=doc.name,
            details=json.dumps({
                "old_status": old_status,
                "new_status": new_status,
                "customer": doc.customer,
                "plan": doc.plan,
            }, default=str),
        )


def _require_admin():
    """Cek apakah user adalah admin/superadmin."""
    from qalcuity.isolation import is_admin_user

    if not is_admin_user():
        frappe.throw(_("Access denied. Admin privileges required."))
