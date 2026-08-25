# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity ERP — In-App Notification API

Provides functions for creating, reading, and managing
in-app notifications for Qalcuity users.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime


@frappe.whitelist()
def get_my_notifications(limit_page_length=20, start=0):
    """Get notifications untuk current user.

    Returns:
        dict: {"notifications": [...], "unread_count": int}
    """
    user = frappe.session.user

    notifications = frappe.get_all(
        "Qalcuity Notification",
        filters={"recipient": user},
        fields=[
            "name",
            "notification_type",
            "title",
            "message",
            "is_read",
            "link",
            "reference_doctype",
            "reference_name",
            "timestamp",
        ],
        order_by="timestamp desc",
        limit_page_length=int(limit_page_length),
        start=int(start),
    )

    unread_count = frappe.db.count(
        "Qalcuity Notification",
        filters={"recipient": user, "is_read": 0},
    )

    return {
        "notifications": notifications,
        "unread_count": unread_count,
    }


@frappe.whitelist()
def get_unread_count():
    """Get count unread notifications untuk current user.

    Returns:
        dict: {"count": int}
    """
    user = frappe.session.user

    count = frappe.db.count(
        "Qalcuity Notification",
        filters={"recipient": user, "is_read": 0},
    )

    return {"count": count}


@frappe.whitelist()
def mark_as_read(notification_name):
    """Mark notification sebagai sudah dibaca.

    Args:
        notification_name: Nama/ID notification

    Returns:
        dict: {"success": True}
    """
    user = frappe.session.user

    # Pastikan notification milik current user
    doc = frappe.get_doc("Qalcuity Notification", notification_name)
    if doc.recipient != user and not _is_admin_user(user):
        frappe.throw(
            _("You do not have permission to modify this notification."),
            frappe.PermissionError,
        )

    frappe.db.set_value(
        "Qalcuity Notification", notification_name, "is_read", 1
    )
    frappe.db.commit()

    return {"success": True}


@frappe.whitelist()
def mark_all_as_read():
    """Mark semua notifikasi current user sebagai sudah dibaca.

    Returns:
        dict: {"success": True, "count": int}
    """
    user = frappe.session.user

    count = frappe.db.count(
        "Qalcuity Notification",
        filters={"recipient": user, "is_read": 0},
    )

    frappe.db.sql(
        """UPDATE `tabQalcuity Notification`
        SET is_read = 1
        WHERE recipient = %s AND is_read = 0""",
        user,
    )
    frappe.db.commit()

    return {"success": True, "count": count}


def create_notification(
    recipient,
    notification_type,
    title,
    message,
    link=None,
    reference_doctype=None,
    reference_name=None,
):
    """Create notification entry (internal use).

    Fungsi ini dipanggil dari sistem (bukan dari API langsung).
    Gagal membuat notification TIDAK akan block operasi utama.

    Args:
        recipient: User email atau name
        notification_type: Payment|Subscription|System|Info
        title: Judul notifikasi
        message: Isi notifikasi
        link: URL redirect (opsional)
        reference_doctype: DocType reference (opsional)
        reference_name: Doc name reference (opsional)
    """
    try:
        # Resolve user email jika bukan user name
        if "@" in str(recipient):
            user = frappe.db.get_value("User", {"email": recipient}, "name")
            if not user:
                frappe.log_error(
                    message=f"Cannot create notification: user not found for {recipient}",
                    title="Qalcuity Notification - User Not Found",
                )
                return
        else:
            user = recipient

        notification = frappe.get_doc(
            {
                "doctype": "Qalcuity Notification",
                "recipient": user,
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "link": link,
                "reference_doctype": reference_doctype,
                "reference_name": reference_name,
                "timestamp": now_datetime(),
            }
        )
        notification.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            message=f"Gagal membuat notifikasi: {str(e)}\nRecipient: {recipient}\nTitle: {title}",
            title="Qalcuity Notification - Create Error",
        )


def _is_admin_user(user):
    """Check apakah user adalah admin/superadmin."""
    return frappe.db.exists(
        "Has Role",
        {
            "parent": user,
            "role": [
                "in",
                ["System Manager", "Qalcuity Superadmin", "Qalcuity Admin"],
            ],
        },
    )
