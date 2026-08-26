# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
2FA Setup page context for Qalcuity ERP.
Provides page metadata for the two-factor authentication setup page.
"""

import frappe

no_cache = True


def get_context(context):
    """Set page context for 2fa-setup page."""
    context.title = "atur 2FA - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-2fa-setup-page"

    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect=/2fa-setup"
        raise frappe.Redirect
