# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity Subscription Log — DocType Controller
================================================
Minimal controller untuk subscription history tracking.
"""

import frappe
from frappe.model.document import Document


class QalcuitySubscriptionLog(Document):
    """Subscription history log entry."""

    def validate(self):
        """Validasi subscription log entry."""
        if not self.timestamp:
            self.timestamp = frappe.utils.now_datetime()
