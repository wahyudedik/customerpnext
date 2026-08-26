# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Admin Health page context for Qalcuity ERP.
Provides page metadata for the system health monitoring page.
"""

import frappe

no_cache = True


def get_context(context):
    """Set page context for admin health page."""
    context.title = "System Health - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-admin-health-page"

    # Check if user is logged in and is admin
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect=/admin-health"
        raise frappe.Redirect

    # Check admin role
    from qalcuity.isolation import is_admin_user

    if not is_admin_user():
        frappe.local.flags.redirect_location = "/dashboard"
        raise frappe.Redirect
