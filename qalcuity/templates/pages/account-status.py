# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Account Status page context for Qalcuity ERP.
Provides page metadata for the account status page.
"""

import frappe

no_cache = True


def get_context(context):
    """Set page context for account-status page."""
    context.title = "Status Akun - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-account-status-page"

    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect=/account-status"
        raise frappe.Redirect
