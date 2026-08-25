# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity Backup DocType Controller
===================================
Tracks backup operations (database, files, full) with status, size, and timing.
"""

import frappe
from frappe import _


class QalcuityBackup(Document):
    """Controller untuk Qalcuity Backup DocType."""

    def before_insert(self):
        """Set default values sebelum insert."""
        self.status = "Pending"
        self.site_name = frappe.local.site
        if not self.performed_by:
            self.performed_by = frappe.session.user

    def validate(self):
        """Validasi field wajib."""
        if self.backup_type not in ["Database", "Files", "Full"]:
            frappe.throw(_("Invalid backup type: {0}").format(self.backup_type))

    def has_permission(self, perm_type):
        """
        Permission check — hanya admin/superadmin bisa akses backup.
        Semua user bisa read (untuk melihat status backup).
        """
        if perm_type == "read":
            return True

        # Write, create, delete — admin only
        user_roles = frappe.get_roles(frappe.session.user)
        admin_roles = ["System Manager", "Qalcuity Superadmin", "Qalcuity Admin"]
        if any(role in user_roles for role in admin_roles):
            return True

        return False
