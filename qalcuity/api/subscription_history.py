# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity Subscription History API
====================================
API endpoints untuk subscription history tracking.

Endpoints:
- get_subscription_history() — get history untuk subscription tertentu
- get_my_subscription_history() — get history untuk customer yang sedang login
"""

import frappe
from frappe import _
import json


def create_subscription_log(subscription_name, action, old_status=None, new_status=None,
                            old_plan=None, new_plan=None, notes=None):
    """
    Buat subscription log entry.

    Fungsi ini dipanggil internal oleh sistem (subscription methods).
    Tidak perlu @frappe.whitelisted karena dipanggil dari server-side.

    Args:
        subscription_name: Nama/ID subscription
        action: Jenis aksi (Created, Activated, Suspended, dll)
        old_status: Status sebelum perubahan (optional)
        new_status: Status sesudah perubahan (optional)
        old_plan: Plan sebelum perubahan (optional)
        new_plan: Plan sesudah perubahan (optional)
        notes: Catatan tambahan (optional)

    Returns:
        str: Name dari subscription log entry yang dibuat
    """
    try:
        user = frappe.session.user

        log = frappe.get_doc({
            "doctype": "Qalcuity Subscription Log",
            "subscription": subscription_name,
            "action": action,
            "old_status": old_status,
            "new_status": new_status,
            "old_plan": old_plan,
            "new_plan": new_plan,
            "performed_by": user,
            "notes": notes,
            "timestamp": frappe.utils.now_datetime(),
        })
        log.insert(ignore_permissions=True)
        frappe.db.commit()

        return log.name

    except Exception as e:
        frappe.log_error(
            message=f"Failed to create subscription log: {str(e)}",
            title="Qalcuity Subscription Log Error",
        )
        return None


@frappe.whitelisted()
def get_subscription_history(subscription_name):
    """
    Mendapatkan riwayat untuk subscription tertentu.

    Args:
        subscription_name: Nama/ID subscription

    Returns:
        list: Daftar subscription log entries
    """
    if not subscription_name:
        frappe.throw(_("Subscription name is required."))

    # Permission check — admin bisa lihat semua, customer hanya yang punya
    _check_subscription_access(subscription_name)

    data = frappe.db.sql(
        """
        SELECT name, subscription, action, old_status, new_status,
               old_plan, new_plan, performed_by, notes, timestamp
        FROM `tabQalcuity Subscription Log`
        WHERE subscription = %s
        ORDER BY timestamp DESC
        """,
        (subscription_name,),
        as_dict=True,
    )

    return data


@frappe.whitelisted()
def get_my_subscription_history(limit_page_length=20, start=0):
    """
    Mendapatkan riwayat subscription untuk customer yang sedang login.

    Args:
        limit_page_length: Jumlah baris per halaman (default: 20)
        start: Offset untuk pagination (default: 0)

    Returns:
        dict: {data: [...], total: int}
    """
    from qalcuity.qalcuity.isolation import get_current_customer

    user = frappe.session.user
    if user in ("Guest", "Administrator"):
        frappe.throw(_("Access denied."))

    # Check if admin — they can see all
    from qalcuity.qalcuity.isolation import is_admin_user
    if is_admin_user():
        # Admin sees all subscription logs
        total = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabQalcuity Subscription Log`",
            as_dict=True,
        )[0].get("count", 0)

        data = frappe.db.sql(
            """
            SELECT sl.name, sl.subscription, sl.action, sl.old_status, sl.new_status,
                   sl.old_plan, sl.new_plan, sl.performed_by, sl.notes, sl.timestamp,
                   sub.customer
            FROM `tabQalcuity Subscription Log` sl
            LEFT JOIN `tabQalcuity Subscription` sub ON sl.subscription = sub.name
            ORDER BY sl.timestamp DESC
            LIMIT %s OFFSET %s
            """,
            (limit_page_length, int(start)),
            as_dict=True,
        )
    else:
        # Customer — only their subscriptions
        customer = get_current_customer()
        if not customer:
            frappe.throw(_("No customer account found."))

        total = frappe.db.sql(
            """
            SELECT COUNT(*)
            FROM `tabQalcuity Subscription Log` sl
            INNER JOIN `tabQalcuity Subscription` sub ON sl.subscription = sub.name
            WHERE sub.customer = %s
            """,
            (customer,),
            as_dict=True,
        )[0].get("count", 0)

        data = frappe.db.sql(
            """
            SELECT sl.name, sl.subscription, sl.action, sl.old_status, sl.new_status,
                   sl.old_plan, sl.new_plan, sl.performed_by, sl.notes, sl.timestamp
            FROM `tabQalcuity Subscription Log` sl
            INNER JOIN `tabQalcuity Subscription` sub ON sl.subscription = sub.name
            WHERE sub.customer = %s
            ORDER BY sl.timestamp DESC
            LIMIT %s OFFSET %s
            """,
            (customer, limit_page_length, int(start)),
            as_dict=True,
        )

    return {
        "data": data,
        "total": total,
    }


def _check_subscription_access(subscription_name):
    """Cek apakah user memiliki akses ke subscription tertentu."""
    from qalcuity.qalcuity.isolation import is_admin_user, get_current_customer

    if is_admin_user():
        return True

    customer = get_current_customer()
    if not customer:
        frappe.throw(_("Access denied."))

    sub_customer = frappe.db.get_value(
        "Qalcuity Subscription", subscription_name, "customer"
    )
    if sub_customer != customer:
        frappe.throw(_("Access denied. You can only view your own subscription history."))

    return True
