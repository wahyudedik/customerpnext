# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity API Key DocType Controller
=====================================
Manages API keys for external integration with Qalcuity ERP.
Each key is tied to a customer and can be revoked.
"""

import frappe
import secrets
from frappe import _
from frappe.model.document import Document


class QalcuityApiKey(Document):
    """Controller untuk Qalcuity API Key DocType."""

    def before_insert(self):
        """Generate keys dan validasi customer sebelum insert."""
        self.generate_keys()
        self.validate_customer()

    def generate_keys(self):
        """Generate API key dan secret."""
        self.api_key = "qk_" + secrets.token_hex(16)
        self.api_secret = secrets.token_hex(32)

    def validate_customer(self):
        """Pastikan customer valid dan milik user yang sedang login."""
        if not self.customer:
            return

        user = frappe.session.user
        if user == "Administrator":
            return

        # Check if user is admin/superadmin — they can create for any customer
        user_roles = frappe.get_roles(user)
        admin_roles = ["System Manager", "Qalcuity Superadmin", "Qalcuity Admin"]
        if any(role in user_roles for role in admin_roles):
            return

        # Portal user —只能 create for own customer
        portal_customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
        if portal_customer and portal_customer != self.customer:
            frappe.throw(_("You can only create API keys for your own account."))

    def validate(self):
        """Validasi field wajib dan business rules."""
        if self.expires_at and self.expires_at < frappe.utils.now_datetime():
            frappe.throw(_("Expiry date cannot be in the past."))

    def has_permission(self, ptype):
        """
        Permission check — customer hanya bisa akses key milik sendiri.
        Admin/superadmin bisa akses semua.
        """
        user = frappe.session.user

        if user == "Administrator":
            return True

        # Admin roles have full access
        user_roles = frappe.get_roles(user)
        admin_roles = ["System Manager", "Qalcuity Superadmin", "Qalcuity Admin"]
        if any(role in user_roles for role in admin_roles):
            return True

        # Portal user — check ownership
        customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
        if customer and self.customer == customer:
            if ptype in ("read", "create"):
                return True

        return False


def has_permission(doc, ptype):
    """Module-level permission check for hooks integration."""
    return doc.has_permission(ptype)
