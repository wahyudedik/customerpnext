# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity Audit Log — DocType Controller
========================================
Minimal controller untuk audit trail system.
"""

import frappe
from frappe.model.document import Document


class QalcuityAuditLog(Document):
    """Audit log entry untuk tracking aktivitas SaaS."""

    def validate(self):
        """Validasi audit log entry."""
        if not self.timestamp:
            self.timestamp = frappe.utils.now_datetime()
