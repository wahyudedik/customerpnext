# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity Provisioning Log — DocType Controller
================================================
Minimal controller untuk provisioning audit trail.
"""

import frappe
from frappe.model.document import Document


class QalcuityProvisioningLog(Document):
    """Provisioning log entry untuk tracking ERP provisioning events."""

    def validate(self):
        """Validasi provisioning log entry."""
        pass
