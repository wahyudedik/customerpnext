# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
API Keys page context for Qalcuity ERP.
Provides page metadata for the API key management page.
"""

import frappe

no_cache = True


def get_context(context):
    """Set page context for API keys page.

    Provides:
    - Page metadata
    - Auth check (redirect to login if guest)
    """
    context.title = "API Keys - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-api-keys-page"

    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect=/api-keys"
        raise frappe.Redirect
