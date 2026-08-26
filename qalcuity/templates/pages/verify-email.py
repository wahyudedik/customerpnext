# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Verify Email page context for Qalcuity ERP.
Handles email verification token validation on page load.
"""

no_cache = True


def get_context(context):
    """Set page context for verify-email page."""
    context.title = "Verifikasi Email - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-auth-page"
