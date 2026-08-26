# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Admin Dashboard API endpoints for Qalcuity ERP.
Provides analytics data for the superadmin dashboard.
"""

import frappe
from frappe import _
from frappe.utils import getdate, add_months, nowdate, cint, flt


@frappe.whitelist()
def get_admin_dashboard_data(date_from=None, date_to=None):
    """
    Get comprehensive admin dashboard data for superadmin overview.

    Args:
        date_from: Start date for filtering (default: first day of current month)
        date_to: End date for filtering (default: today)

    Returns:
        dict: Dashboard data with revenue, customer, subscription, payment,
              tenant stats, revenue trend, and recent activity
    """
    user = frappe.session.user

    if user == "Guest":
        frappe.throw(_("Please login to access the admin dashboard."))

    # Check admin role
    from qalcuity.isolation import is_admin_user

    if not is_admin_user():
        frappe.throw(_("You do not have permission to access the admin dashboard."))

    # Default date range: current month
    today = getdate(nowdate())
    if not date_to:
        date_to = today
    else:
        date_to = getdate(date_to)

    if not date_from:
        date_from = add_months(today, 0).replace(day=1)
    else:
        date_from = getdate(date_from)

    # Previous month range for comparison
    prev_month_end = add_months(date_from, -1)
    prev_month_start = prev_month_end.replace(day=1)

    data = {
        "revenue": _get_revenue_stats(date_from, date_to, prev_month_start, prev_month_end),
        "customers": _get_customer_stats(date_from, date_to),
        "subscriptions": _get_subscription_stats(),
        "payments": _get_payment_stats(date_from, date_to, prev_month_start, prev_month_end),
        "tenants": _get_tenant_stats(),
        "revenue_trend": _get_revenue_trend(date_from, date_to),
        "recent_activity": _get_recent_activity(),
        "date_range": {
            "from": str(date_from),
            "to": str(date_to),
        },
    }

    return data


def _get_revenue_stats(date_from, date_to, prev_month_start, prev_month_end):
    """Get revenue statistics for current and previous month."""
    # Revenue this month (approved payments)
    current_revenue = frappe.db.sql(
        """
        SELECT COALESCE(SUM(amount), 0) as total
        FROM `tabQalcuity Payment`
        WHERE status = 'Approved'
        AND payment_date BETWEEN %s AND %s
        """,
        (date_from, date_to),
        as_dict=True,
    )

    # Revenue last month (approved payments)
    prev_revenue = frappe.db.sql(
        """
        SELECT COALESCE(SUM(amount), 0) as total
        FROM `tabQalcuity Payment`
        WHERE status = 'Approved'
        AND payment_date BETWEEN %s AND %s
        """,
        (prev_month_start, prev_month_end),
        as_dict=True,
    )

    # Total all-time revenue
    total_revenue = frappe.db.sql(
        """
        SELECT COALESCE(SUM(amount), 0) as total
        FROM `tabQalcuity Payment`
        WHERE status = 'Approved'
        """,
        as_dict=True,
    )

    current = flt(current_revenue[0].total) if current_revenue else 0
    prev = flt(prev_revenue[0].total) if prev_revenue else 0
    total = flt(total_revenue[0].total) if total_revenue else 0

    # Calculate growth percentage
    growth_pct = 0
    if prev > 0:
        growth_pct = round(((current - prev) / prev) * 100, 1)

    return {
        "total": total,
        "this_month": current,
        "last_month": prev,
        "growth_pct": growth_pct,
    }


def _get_customer_stats(date_from, date_to):
    """Get customer statistics."""
    total = frappe.db.count("Customer") or 0

    # New this month (customers created in date range)
    new_this_month = frappe.db.sql(
        """
        SELECT COUNT(*) as cnt
        FROM `tabCustomer`
        WHERE creation BETWEEN %s AND %s
        """,
        (date_from, add_months(date_from, 1).replace(day=1) if date_from.day == 1 else date_to),
        as_dict=True,
    )

    # Active customers (have active subscription)
    active = frappe.db.sql(
        """
        SELECT COUNT(DISTINCT s.customer) as cnt
        FROM `tabQalcuity Subscription` s
        WHERE s.status IN ('Active', 'Grace Period')
        """,
        as_dict=True,
    )

    # Inactive customers (no active subscription or expired)
    inactive = total - (active[0].cnt if active else 0)

    return {
        "total": total,
        "new_this_month": new_this_month[0].cnt if new_this_month else 0,
        "active": active[0].cnt if active else 0,
        "inactive": max(inactive, 0),
    }


def _get_subscription_stats():
    """Get subscription statistics by status."""
    stats = frappe.db.sql(
        """
        SELECT status, COUNT(*) as cnt
        FROM `tabQalcuity Subscription`
        GROUP BY status
        """,
        as_dict=True,
    )

    result = {
        "Active": 0,
        "Grace Period": 0,
        "Expired": 0,
        "Suspended": 0,
        "Pending Payment": 0,
        "Draft": 0,
        "Cancelled": 0,
        "total": 0,
    }

    for row in stats:
        result[row.status] = cint(row.cnt)
        result["total"] += cint(row.cnt)

    return result


def _get_payment_stats(date_from, date_to, prev_month_start, prev_month_end):
    """Get payment statistics."""
    # Pending reviews
    pending = frappe.db.count("Qalcuity Payment", {"status": "Pending"}) or 0

    # Approved this month
    approved_this_month = frappe.db.sql(
        """
        SELECT COUNT(*) as cnt
        FROM `tabQalcuity Payment`
        WHERE status = 'Approved'
        AND modified BETWEEN %s AND %s
        """,
        (date_from, add_months(date_from, 1).replace(day=1) if date_from.day == 1 else date_to),
        as_dict=True,
    )

    # Rejected this month
    rejected_this_month = frappe.db.sql(
        """
        SELECT COUNT(*) as cnt
        FROM `tabQalcuity Payment`
        WHERE status = 'Rejected'
        AND modified BETWEEN %s AND %s
        """,
        (date_from, add_months(date_from, 1).replace(day=1) if date_from.day == 1 else date_to),
        as_dict=True,
    )

    # Approved last month (for comparison)
    approved_last_month = frappe.db.sql(
        """
        SELECT COUNT(*) as cnt
        FROM `tabQalcuity Payment`
        WHERE status = 'Approved'
        AND modified BETWEEN %s AND %s
        """,
        (prev_month_start, prev_month_end),
        as_dict=True,
    )

    # Total payments
    total = frappe.db.count("Qalcuity Payment") or 0

    return {
        "pending": pending,
        "approved_this_month": approved_this_month[0].cnt if approved_this_month else 0,
        "rejected_this_month": rejected_this_month[0].cnt if rejected_this_month else 0,
        "approved_last_month": approved_last_month[0].cnt if approved_last_month else 0,
        "total": total,
    }


def _get_tenant_stats():
    """Get tenant statistics."""
    stats = frappe.db.sql(
        """
        SELECT status, COUNT(*) as cnt
        FROM `tabQalcuity Tenant`
        GROUP BY status
        """,
        as_dict=True,
    )

    result = {
        "Active": 0,
        "Provisioned": 0,
        "Suspended": 0,
        "Pending": 0,
        "total": 0,
    }

    for row in stats:
        result[row.status] = cint(row.cnt)
        result["total"] += cint(row.cnt)

    # Provisioned count (has ERP provisioning completed)
    provisioned = frappe.db.sql(
        """
        SELECT COUNT(*) as cnt
        FROM `tabQalcuity Tenant`
        WHERE erp_provisioning_status = 'Completed'
        """,
        as_dict=True,
    )

    result["Provisioned"] = provisioned[0].cnt if provisioned else 0

    return result


def _get_revenue_trend(date_from, date_to):
    """Get monthly revenue trend for chart (last 6 months)."""
    months = []
    for i in range(5, -1, -1):
        month_date = add_months(date_from, -i)
        month_start = month_date.replace(day=1)
        if i > 0:
            month_end = add_months(month_date, 1).replace(day=1)
        else:
            month_end = date_to

        revenue = frappe.db.sql(
            """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM `tabQalcuity Payment`
            WHERE status = 'Approved'
            AND payment_date BETWEEN %s AND %s
            """,
            (month_start, month_end),
            as_dict=True,
        )

        months.append(
            {
                "month": month_start.strftime("%b %Y"),
                "revenue": flt(revenue[0].total) if revenue else 0,
            }
        )

    return months


def _get_recent_activity():
    """Get 10 most recent activities (payments, subscriptions, tenants)."""
    activities = []

    # Recent payments
    recent_payments = frappe.get_all(
        "Qalcuity Payment",
        fields=["name", "customer", "amount", "status", "creation"],
        order_by="creation desc",
        limit_page_length=5,
    )

    for p in recent_payments:
        activities.append(
            {
                "type": "payment",
                "icon": "octicon octicon-credit-card",
                "description": f"Payment {p.name} — {p.customer}",
                "detail": f"Rp {flt(p.amount):,.0f}",
                "status": p.status,
                "date": str(p.creation),
            }
        )

    # Recent subscriptions
    recent_subs = frappe.get_all(
        "Qalcuity Subscription",
        fields=["name", "customer", "status", "creation"],
        order_by="creation desc",
        limit_page_length=5,
    )

    for s in recent_subs:
        activities.append(
            {
                "type": "subscription",
                "icon": "octicon octicon-sync",
                "description": f"Subscription {s.name} — {s.customer}",
                "detail": s.status,
                "status": s.status,
                "date": str(s.creation),
            }
        )

    # Recent tenants
    recent_tenants = frappe.get_all(
        "Qalcuity Tenant",
        fields=["name", "tenant_id", "customer", "status", "creation"],
        order_by="creation desc",
        limit_page_length=5,
    )

    for t in recent_tenants:
        activities.append(
            {
                "type": "tenant",
                "icon": "octicon octicon-globe",
                "description": f"Tenant {t.tenant_id or t.name} — {t.customer}",
                "detail": t.status,
                "status": t.status,
                "date": str(t.creation),
            }
        )

    # Sort by date descending and take top 10
    activities.sort(key=lambda x: x["date"], reverse=True)
    return activities[:10]
