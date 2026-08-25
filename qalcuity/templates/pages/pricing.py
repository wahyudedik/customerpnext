# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Pricing page context for Qalcuity ERP.
Provides page metadata for the public pricing page.
"""

no_cache = True


def get_context(context):
    """Set page context for pricing page."""
    context.title = "Harga & Paket - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-pricing-page"
