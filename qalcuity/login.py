"""
Qalcuity ERP — Login Page Override

Customizes the login page to show Qalcuity branding
instead of the default Frappe/ERPNext branding.
"""

import frappe
from frappe import _


def login(context):
    """Custom login page context for Qalcuity branding."""
    context.brand_html = (
        '<img src="/assets/qalcuity/images/logo-dark.png" '
        'alt="Qalcuity ERP" '
        'style="height: 40px;">'
    )
    context.title = "Qalcuity ERP - Login"
    context.no_header = True
    context.no_breadcrumbs = True
