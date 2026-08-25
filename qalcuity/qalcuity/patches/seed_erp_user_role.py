# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Patch: Seed Qalcuity ERP User role
====================================
Ensures the "Qalcuity ERP User" custom role exists in the system.
This role is assigned to customers during ERP provisioning.
"""

import frappe


def execute():
    """Create Qalcuity ERP User role if it doesn't exist."""
    role_name = "Qalcuity ERP User"

    if not frappe.db.exists("Role", role_name):
        role = frappe.get_doc(
            {
                "doctype": "Role",
                "role_name": role_name,
                "desk_access": 1,
                "is_custom": 1,
                "description": "Standard ERP access for Qalcuity customers",
            }
        )
        role.insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.logger().info(
            "Qalcuity Patch: Role '{0}' created".format(role_name)
        )
    else:
        frappe.logger().info(
            "Qalcuity Patch: Role '{0}' already exists".format(role_name)
        )
