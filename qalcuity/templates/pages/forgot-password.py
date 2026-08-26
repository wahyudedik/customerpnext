# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Forgot Password page context for Qalcuity ERP.
Provides page metadata for the forgot password form.
"""

no_cache = True


def get_context(context):
    """Set page context for forgot password page."""
    context.title = "Lupa Password - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-auth-page"
