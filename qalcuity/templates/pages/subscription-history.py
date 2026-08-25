# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Subscription History page context for Qalcuity ERP.
Provides page metadata for the subscription history page.
"""

import frappe

no_cache = True


def get_context(context):
    """Set page context for subscription-history page."""
    context.title = "Riwayat Subscription - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-subscription-history-page"

    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect
