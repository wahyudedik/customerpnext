# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Admin Login Logs page context for Qalcuity ERP.
Provides page metadata for the login audit trail page.
"""

import frappe
from frappe import _

no_cache = True


def get_context(context):
    """Set page context for admin login logs page."""
    context.title = "Login Logs - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-admin-login-logs-page"

    # Check if user is logged in and has admin access
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect=/admin-login-logs"
        raise frappe.Redirect

    user = frappe.session.user
    roles = frappe.get_roles(user)
    is_admin = (
        user == "Administrator"
        or "System Manager" in roles
        or "Qalcuity Superadmin" in roles
        or "Qalcuity Admin" in roles
    )

    if not is_admin:
        frappe.throw(_("You do not have permission to access this page."), frappe.PermissionError)
