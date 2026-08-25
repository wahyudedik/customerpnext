# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Account Status API endpoints for Qalcuity ERP.
Provides whitelisted methods for account status overview.
"""

import frappe
from frappe import _
from datetime import datetime, timedelta


@frappe.whitelisted()
def get_account_status():
    """
    Get comprehensive account status for the currently logged-in user.
    Returns subscription, tenant, payment summary, and usage data.

    Returns:
        dict: Account status with subscription, tenant, payments, and usage
    """
    user = frappe.session.user

    if user == "Guest":
        frappe.throw(_("Silakan login untuk mengakses status akun."))

    # Get customer linked to user
    customer_name = frappe.db.get_value(
        "Portal User", {"user": user, "parenttype": "Customer"}, "parent"
    )

    if not customer_name:
        return {
            "subscription": None,
            "tenant": None,
            "payments": {"total": 0, "pending": 0, "approved": 0, "rejected": 0},
            "usage": {"storage_used": 0, "storage_limit": 0, "users_count": 0, "users_limit": 0},
        }

    # --- Subscription ---
    subscription = _get_subscription_status(customer_name)

    # --- Tenant ---
    tenant = _get_tenant_status(customer_name)

    # --- Payment Summary ---
    payments = _get_payment_summary(customer_name)

    # --- Usage ---
    usage = _get_usage_data(customer_name, tenant)

    return {
        "subscription": subscription,
        "tenant": tenant,
        "payments": payments,
        "usage": usage,
    }


def _get_subscription_status(customer_name):
    """
    Get subscription status with days remaining calculation.

    Args:
        customer_name: Customer name

    Returns:
        dict or None: Subscription information
    """
    sub = frappe.get_all(
        "Qalcuity Subscription",
        filters={"customer": customer_name},
        fields=[
            "name", "plan", "status", "start_date", "end_date",
            "is_trial", "auto_renew",
        ],
        order_by="creation desc",
        limit_page_length=1,
    )

    if not sub:
        return None

    s = sub[0]
    plan_name = frappe.db.get_value("Qalcuity Plan", s.plan, "plan_name") if s.plan else None

    # Calculate days remaining
    days_remaining = None
    is_grace_period = False
    if s.end_date:
        end = frappe.utils.getdate(s.end_date)
        today = frappe.utils.getdate()
        diff = (end - today).days
        days_remaining = diff
        if diff < 0 and diff >= -7:
            is_grace_period = True

    return {
        "name": s.name,
        "plan": s.plan,
        "plan_name": plan_name,
        "status": s.status,
        "start_date": str(s.start_date) if s.start_date else None,
        "end_date": str(s.end_date) if s.end_date else None,
        "is_trial": s.is_trial,
        "auto_renew": s.auto_renew,
        "days_remaining": days_remaining,
        "is_grace_period": is_grace_period,
    }


def _get_tenant_status(customer_name):
    """
    Get tenant status information.

    Args:
        customer_name: Customer name

    Returns:
        dict or None: Tenant information
    """
    tenant = frappe.get_all(
        "Qalcuity Tenant",
        filters={"customer": customer_name},
        fields=["name", "tenant_id", "status", "creation"],
        limit_page_length=1,
    )

    if not tenant:
        return None

    t = tenant[0]
    return {
        "name": t.name,
        "tenant_id": t.tenant_id,
        "status": t.status,
        "provisioned_at": str(t.creation) if t.creation else None,
    }


def _get_payment_summary(customer_name):
    """
    Get payment summary counts by status.

    Args:
        customer_name: Customer name

    Returns:
        dict: Payment counts
    """
    # Get all subscriptions for this customer
    sub_names = frappe.get_all(
        "Qalcuity Subscription",
        filters={"customer": customer_name},
        pluck="name",
    )

    if not sub_names:
        return {"total": 0, "pending": 0, "approved": 0, "rejected": 0}

    # Count payments by status
    total = frappe.db.count("Qalcuity Payment", {"subscription": ["in", sub_names]})
    pending = frappe.db.count("Qalcuity Payment", {"subscription": ["in", sub_names], "status": "Pending"})
    approved = frappe.db.count("Qalcuity Payment", {"subscription": ["in", sub_names], "status": "Approved"})
    rejected = frappe.db.count("Qalcuity Payment", {"subscription": ["in", sub_names], "status": "Rejected"})

    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
    }


def _get_usage_data(customer_name, tenant):
    """
    Get usage data (storage, users) for the customer's tenant.

    Args:
        customer_name: Customer name
        tenant: Tenant dict from _get_tenant_status

    Returns:
        dict: Usage information
    """
    usage = {
        "storage_used": 0,
        "storage_limit": 0,
        "users_count": 0,
        "users_limit": 0,
    }

    if not tenant:
        return usage

    # Count users linked to this customer
    user_count = frappe.db.count(
        "Portal User",
        {"parent": customer_name, "parenttype": "Customer"},
    )
    usage["users_count"] = user_count

    # Get plan limits
    sub = frappe.get_all(
        "Qalcuity Subscription",
        filters={"customer": customer_name, "status": "Active"},
        fields=["plan"],
        limit_page_length=1,
    )

    if sub and sub[0].plan:
        plan_doc = frappe.get_doc("Qalcuity Plan", sub[0].plan)
        # Check for user limit in plan features
        for feature in plan_doc.features:
            if "user" in (feature.feature_name or "").lower():
                try:
                    usage["users_limit"] = int(feature.feature_value)
                except (ValueError, TypeError):
                    pass

    # Storage is not yet tracked in MVP — return 0
    usage["storage_used"] = 0
    usage["storage_limit"] = 0

    return usage
