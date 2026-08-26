# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Plan Change page context for Qalcuity ERP.
Provides page metadata for the plan upgrade/downgrade page.
"""

import frappe

no_cache = True


def get_context(context):
    """Set page context for plan change page.

    Provides:
    - Page metadata
    - Active subscription info
    - Available plans
    - Recent plan changes
    """
    context.title = "Ganti Paket - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-plan-change-page"

    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect=/plan-change"
        raise frappe.Redirect

    # Get customer
    user = frappe.session.user
    customer = frappe.db.get_value("Portal User", {"user": user}, "parent")

    if not customer:
        context.redirect_to = "/login"
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect

    # Get active subscription
    subscription = frappe.db.get_value(
        "Qalcuity Subscription",
        {"customer": customer, "status": ["in", ["Active", "Grace Period"]]},
        ["name", "plan", "status", "start_date", "end_date", "customer"],
        as_dict=True,
    )

    context.subscription = subscription

    # Get current plan details
    context.current_plan = None
    if subscription and subscription.plan:
        context.current_plan = frappe.db.get_value(
            "Qalcuity Plan",
            subscription.plan,
            ["plan_name", "price", "billing_period", "description", "max_users", "max_storage_gb"],
            as_dict=True,
        )

    # Get available plans (excluding current plan and trial)
    all_plans = frappe.get_all(
        "Qalcuity Plan",
        filters={"is_active": 1, "is_trial": 0},
        fields=["plan_name", "price", "billing_period", "description", "max_users", "max_storage_gb", "name"],
        order_by="sort_order asc",
    )

    context.plans = all_plans

    # Get recent plan changes
    context.plan_changes = frappe.get_all(
        "Qalcuity Plan Change",
        filters={"customer": customer},
        fields=[
            "name",
            "current_plan",
            "new_plan",
            "change_type",
            "status",
            "effective_date",
            "amount_to_pay",
            "prorated_credit",
            "current_plan_price",
            "new_plan_price",
            "creation",
        ],
        order_by="creation desc",
        limit_page_length=10,
    )
