# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
2FA Verify page context for Qalcuity ERP.
Provides page metadata for the two-factor authentication verification page.
"""

import frappe

no_cache = True


def get_context(context):
    """Set page context for 2fa-verify page."""
    context.title = "Verifikasi 2FA - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-2fa-verify-page"

    # This page can be accessed by guests (during login flow)
    # The token parameter is validated server-side
