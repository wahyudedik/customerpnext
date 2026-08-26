# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class QalcuityLoginLog(Document):
    """Log setiap percobaan login (success/fail/blocked) untuk security audit."""

    def has_permission(self, doc, ptype):
        """Permission check — customer hanya bisa lihat log milik sendiri."""
        user = frappe.session.user
        if user == "Administrator":
            return True
        roles = frappe.get_roles(user)
        if "System Manager" in roles or "Qalcuity Superadmin" in roles or "Qalcuity Admin" in roles:
            return True
        # Customer — hanya bisa lihat log milik sendiri
        if doc.user == user and ptype == "read":
            return True
        return False


def has_permission(doc, ptype):
    """Standalone permission check for hooks."""
    user = frappe.session.user
    if user == "Administrator":
        return True
    roles = frappe.get_roles(user)
    if "System Manager" in roles or "Qalcuity Superadmin" in roles or "Qalcuity Admin" in roles:
        return True
    # Customer — hanya bisa lihat log milik sendiri
    if doc.user == user and ptype == "read":
        return True
    return False
