# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Register page context for Qalcuity ERP.
Provides page metadata for the customer registration form.
"""

no_cache = True


def get_context(context):
    """Set page context for registration page."""
    context.title = "Daftar Akun - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-register-page"
