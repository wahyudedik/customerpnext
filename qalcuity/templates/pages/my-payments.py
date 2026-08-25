# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
My Payments page context for Qalcuity ERP.
Provides page metadata for the payment history page.
"""

import frappe

no_cache = True


def get_context(context):
    """Set page context for my-payments page."""
    context.title = "Pembayaran Saya - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-my-payments-page"

    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect
