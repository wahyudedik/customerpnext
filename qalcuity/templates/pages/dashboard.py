# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Dashboard page context for Qalcuity ERP.
Provides page metadata for the customer dashboard.
"""

import frappe

no_cache = True


def get_context(context):
    """Set page context for dashboard page.

    Provides:
    - Page metadata
    - Provisioning status for ERP access banner
    - Subscription status for conditional rendering
    """
    context.title = "Dashboard - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-dashboard-page"

    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect=/dashboard"
        raise frappe.Redirect

    # Get customer and tenant info for provisioning status
    user = frappe.session.user
    customer = frappe.db.get_value("Portal User", {"user": user}, "parent")

    context.provisioning_status = "Not Started"
    context.erp_company = None
    context.can_access_erp = False
    context.subscription_status = None

    if customer:
        # Get latest subscription
        sub = frappe.get_all(
            "Qalcuity Subscription",
            filters={"customer": customer},
            fields=["name", "status"],
            order_by="creation desc",
            limit_page_length=1,
        )
        if sub:
            context.subscription_status = sub[0].status

        # Get tenant provisioning info
        tenant = frappe.get_all(
            "Qalcuity Tenant",
            filters={"customer": customer},
            fields=[
                "name",
                "erp_provisioning_status",
                "erp_company",
            ],
            limit_page_length=1,
        )
        if tenant:
            context.provisioning_status = tenant[0].erp_provisioning_status or "Not Started"
            context.erp_company = tenant[0].erp_company
            context.can_access_erp = (
                tenant[0].erp_provisioning_status == "Completed"
                and context.subscription_status == "Active"
            )
