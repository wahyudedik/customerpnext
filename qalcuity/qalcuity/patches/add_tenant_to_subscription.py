# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Patch: Add tenant Link field to Qalcuity Subscription

This patch safely adds a 'tenant' link field to the Qalcuity Subscription
DocType for production environments where the field does not yet exist.

Created: 2026-08-24
Reason: Subscription needs a direct link to Tenant for easier querying
        and relationship management. Previously only a reverse link existed
        from Tenant to Subscription.
"""


def execute():
    """Add tenant Link field to Qalcuity Subscription via Custom Field."""
    import frappe

    frappe.reload_doctype("Qalcuity Subscription", force=True)

    # Check if the Custom Field already exists
    existing = frappe.db.exists(
        "Custom Field",
        {"dt": "Qalcuity Subscription", "fieldname": "tenant"},
    )

    if not existing:
        frappe.get_doc(
            {
                "doctype": "Custom Field",
                "dt": "Qalcuity Subscription",
                "fieldname": "tenant",
                "fieldtype": "Link",
                "label": "Tenant",
                "options": "Qalcuity Tenant",
                "insert_after": "customer",
                "module": "Qalcuity",
                "read_only": 0,
                "in_list_view": 1,
                "in_standard_filter": 1,
            }
        ).insert(ignore_permissions=True)

        frappe.db.commit()
