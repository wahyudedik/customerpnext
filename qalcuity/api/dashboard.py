# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Dashboard API endpoints for Qalcuity ERP.
Provides data for the customer dashboard page.
"""

import frappe
from frappe import _


@frappe.whitelisted()
def get_dashboard_data():
    """
    Get dashboard data for the current user (Customer).
    Returns subscription, tenant, and recent payment data.

    Returns:
        dict: Dashboard data with subscription, tenant, and payments
    """
    user = frappe.session.user

    if user == "Guest":
        frappe.throw(_("Please login to access the dashboard."))

    # Get customer linked to user
    customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
    if not customer:
        return {"subscription": None, "tenant": None, "payments": []}

    # Get latest subscription
    subscription = None
    subs = frappe.get_all(
        "Qalcuity Subscription",
        filters={"customer": customer},
        fields=[
            "name",
            "plan",
            "status",
            "start_date",
            "end_date",
            "is_trial",
            "tenant",
        ],
        order_by="creation desc",
        limit_page_length=1,
    )

    if subs:
        sub = subs[0]
        # Get plan name
        plan_name = frappe.db.get_value("Qalcuity Plan", sub.plan, "plan_name") if sub.plan else None
        subscription = {
            "name": sub.name,
            "plan": sub.plan,
            "plan_name": plan_name,
            "status": sub.status,
            "start_date": sub.start_date,
            "end_date": sub.end_date,
            "is_trial": sub.is_trial,
        }

    # Get tenant (with provisioning status)
    tenant = None
    tenant_doc = frappe.get_all(
        "Qalcuity Tenant",
        filters={"customer": customer},
        fields=[
            "name",
            "tenant_id",
            "status",
            "erp_provisioning_status",
            "erp_company",
            "provisioning_error",
        ],
        limit_page_length=1,
    )
    if tenant_doc:
        t = tenant_doc[0]
        tenant = {
            "name": t.name,
            "tenant_id": t.tenant_id,
            "status": t.status,
            "erp_provisioning_status": t.erp_provisioning_status or "Not Started",
            "erp_company": t.erp_company,
            "provisioning_error": t.provisioning_error,
        }

    # Get recent payments
    payments = []
    if subs:
        sub_names = [s.name for s in subs]
        payment_docs = frappe.get_all(
            "Qalcuity Payment",
            filters={"subscription": ["in", sub_names]},
            fields=[
                "name",
                "amount",
                "currency",
                "payment_method",
                "payment_date",
                "status",
            ],
            order_by="creation desc",
            limit_page_length=5,
        )
        for p in payment_docs:
            payments.append({
                "name": p.name,
                "amount": p.amount,
                "currency": p.currency,
                "payment_method": p.payment_method,
                "payment_date": p.payment_date,
                "status": p.status,
            })

    return {
        "subscription": subscription,
        "tenant": tenant,
        "payments": payments,
    }
