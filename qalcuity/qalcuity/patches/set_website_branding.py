# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Patch: Set Website Settings branding to Qalcuity
=================================================
Overrides the default Frappe/ERPNext website settings to show
Qalcuity branding on the login page, favicon, and splash screen.

This sets:
  - Website Settings-app_name = "Qalcuity ERP"
  - Website Settings-app_logo = "/assets/qalcuity/images/logo-dark.png"
  - Website Settings-favicon = "/assets/qalcuity/images/logo-dark.png"
  - Website Settings-splash_image = "/assets/qalcuity/images/logo-dark.png"
"""

import frappe


def execute():
    """Set Website Settings to show Qalcuity branding."""
    properties = {
        "app_name": "Qalcuity ERP",
        "app_logo": "/assets/qalcuity/images/logo-dark.png",
        "favicon": "/assets/qalcuity/images/logo-dark.png",
        "splash_image": "/assets/qalcuity/images/logo-dark.png",
    }

    for prop, value in properties.items():
        setter_name = "Website Settings-{0}".format(prop)
        try:
            if frappe.db.exists("Property Setter", setter_name):
                frappe.db.set_value("Property Setter", setter_name, "value", value)
                frappe.logger().info(
                    "Qalcuity Patch: Property Setter '{0}' updated to '{1}'".format(
                        setter_name, value
                    )
                )
            else:
                doc = frappe.get_doc(
                    {
                        "doctype": "Property Setter",
                        "name": setter_name,
                        "doc_type": "Website Settings",
                        "field_name": prop,
                        "property": "value",
                        "value": value,
                        "property_type": "Data",
                        "doctype_or_field": "Field",
                    }
                )
                doc.insert(ignore_permissions=True)
                frappe.logger().info(
                    "Qalcuity Patch: Property Setter '{0}' created with value '{1}'".format(
                        setter_name, value
                    )
                )
        except Exception as e:
            frappe.logger().error(
                "Qalcuity Patch: Failed to set '{0}': {1}".format(setter_name, str(e))
            )

    frappe.db.commit()
    frappe.logger().info("Qalcuity Patch: Website Settings branding applied successfully")
