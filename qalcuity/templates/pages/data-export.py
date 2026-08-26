# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Data Export page context for Qalcuity ERP.
Provides page metadata for the data export page.
"""

import frappe

no_cache = True


def get_context(context):
    """Set page context for data export page."""
    context.title = "Data Export - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-data-export-page"

    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect=/data-export"
        raise frappe.Redirect

    # Check if user is admin
    user = frappe.session.user
    roles = frappe.get_roles(user)
    context.is_admin = any(r in roles for r in ["System Manager", "Qalcuity Superadmin", "Qalcuity Admin"])

    # Get customer info
    customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
    context.customer = customer
