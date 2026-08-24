# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Customer API hooks for Qalcuity ERP.
Handles customer-related events.
"""

import frappe
from frappe import _


def after_customer_insert(doc, method):
    """
    Hook: After a new Customer is created in ERPNext.
    Automatically create a Qalcuity Tenant for the new customer.

    Args:
        doc: Customer document
        method: Event method name
    """
    try:
        # Check if Qalcuity Settings exists
        if not frappe.db.exists("Qalcuity Settings"):
            return

        settings = frappe.get_single("Qalcuity Settings")

        # Only auto-provision if enabled
        if not settings.enable_trial_period:
            return

        # Check if tenant already exists
        if frappe.db.exists("Qalcuity Tenant", {"customer": doc.name}):
            return

        # Create tenant
        tenant = frappe.get_doc(
            {
                "doctype": "Qalcuity Tenant",
                "customer": doc.name,
                "status": "Active",
            }
        )
        tenant.insert(ignore_permissions=True)

        frappe.msgprint(
            _("Tenant provisioned for customer {0}.").format(doc.customer_name),
            indicator="green",
            alert=True,
        )

    except Exception:
        frappe.log_error(
            title="Qalcuity: Failed to provision tenant for customer {0}".format(
                doc.name
            )
        )
