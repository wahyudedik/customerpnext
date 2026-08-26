# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Sessions page context for Qalcuity ERP.
Provides page metadata for the session management page.
"""

import frappe

no_cache = True


def get_context(context):
    """Set page context for sessions page."""
    context.title = "Sesi Aktif - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-sessions-page"

    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect=/sessions"
        raise frappe.Redirect
