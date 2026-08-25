# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class QalcuityNotification(Document):
    """In-app notification untuk Qalcuity ERP."""

    def validate(self):
        """Set timestamp jika kosong."""
        if not self.timestamp:
            self.timestamp = now_datetime()


def has_permission(doc, ptype):
    """Permission check — hanya recipient yang bisa akses (kecuali admin)."""
    user = frappe.session.user

    # System Manager and Qalcuity Superadmin have full access
    if frappe.db.exists(
        "Has Role",
        {"parent": user, "role": ["in", ["System Manager", "Qalcuity Superadmin"]]},
    ):
        return True

    # Qalcuity Admin can read/write
    if frappe.db.exists(
        "Has Role",
        {"parent": user, "role": "Qalcuity Admin"},
    ):
        return True

    # Recipient can only read their own notifications
    if ptype in ("read",) and doc.recipient == user:
        return True

    return False
