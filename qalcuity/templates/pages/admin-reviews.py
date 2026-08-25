# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Admin Reviews page context for Qalcuity ERP.
Provides page metadata for the superadmin payment review queue.
"""

import frappe

no_cache = True


def get_context(context):
    """Set page context for admin reviews page."""
    context.title = "Payment Review Queue - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-admin-reviews-page"

    # Check if user is logged in and is admin
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect=/admin-reviews"
        raise frappe.Redirect

    # Check admin role
    from qalcuity.qalcuity.isolation import is_admin_user

    if not is_admin_user():
        frappe.local.flags.redirect_location = "/dashboard"
        raise frappe.Redirect
