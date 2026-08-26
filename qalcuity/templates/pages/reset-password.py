# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Reset Password page context for Qalcuity ERP.
Handles password reset token validation via URL params.
"""

no_cache = True


def get_context(context):
    """Set page context for reset password page."""
    context.title = "Reset Password - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-auth-page"
