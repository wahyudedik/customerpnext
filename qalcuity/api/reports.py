# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Reports API endpoints for Qalcuity ERP.
Provides revenue, MRR, churn, plan distribution, and overview stats.
"""

import frappe
from frappe import _
from frappe.utils import getdate, add_months, nowdate, flt, cint


@frappe.whitelist()
def get_revenue_report(from_date=None, to_date=None):
    """
    Revenue dari approved payments per bulan.

    Args:
        from_date: Start date (default: 12 bulan lalu)
        to_date: End date (default: today)

    Returns:
        dict: {labels: [...], data: [...], total: X}
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please login to access reports."))

    from qalcuity.qalcuity.isolation import is_admin_user
    if not is_admin_user():
        frappe.throw(_("You do not have permission to access reports."))

    today = getdate(nowdate())
    to_date = getdate(to_date) if to_date else today
    from_date = getdate(from_date) if from_date else add_months(today, -11).replace(day=1)

    labels = []
    data = []
    total = 0

    current = from_date.replace(day=1)
    while current <= to_date:
        month_start = current
        month_end = add_months(current, 1).replace(day=1)

        # Ensure we don't go past to_date
        effective_end = month_end if month_end <= to_date else to_date

        revenue = frappe.db.sql(
            """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM `tabQalcuity Payment`
            WHERE status = 'Approved'
            AND payment_date BETWEEN %s AND %s
            """,
            (month_start, effective_end),
            as_dict=True,
        )

        month_revenue = flt(revenue[0].total) if revenue else 0
        labels.append(current.strftime("%b %Y"))
        data.append(month_revenue)
        total += month_revenue

        current = add_months(current, 1)

    return {
        "labels": labels,
        "data": data,
        "total": total,
    }


@frappe.whitelist()
def get_mrr_report(from_date=None, to_date=None):
    """
    Monthly Recurring Revenue dari active subscriptions.
    MRR = jumlah subscription aktif × plan price per bulan.

    Args:
        from_date: Start date (default: 12 bulan lalu)
        to_date: End date (default: today)

    Returns:
        dict: {labels: [...], data: [...], total: X}
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please login to access reports."))

    from qalcuity.qalcuity.isolation import is_admin_user
    if not is_admin_user():
        frappe.throw(_("You do not have permission to access reports."))

    today = getdate(nowdate())
    to_date = getdate(to_date) if to_date else today
    from_date = getdate(from_date) if from_date else add_months(today, -11).replace(day=1)

    labels = []
    data = []
    total = 0

    current = from_date.replace(day=1)
    while current <= to_date:
        # Count active subscriptions during this month
        # Subscription is active if:
        # - status = 'Active' or 'Grace Period'
        # - created on or before end of month
        # - not expired/cancelled before start of month
        month_start = current
        month_end = add_months(current, 1).replace(day=1)

        active_subs = frappe.db.sql(
            """
            SELECT COUNT(*) as cnt, COALESCE(SUM(plan_price), 0) as mrr
            FROM `tabQalcuity Subscription`
            WHERE status IN ('Active', 'Grace Period')
            AND creation <= %s
            """,
            (month_end,),
            as_dict=True,
        )

        # More accurate: count subscriptions active at end of this month
        # that were created before or during this month
        mrr = flt(active_subs[0].mrr) if active_subs else 0

        labels.append(current.strftime("%b %Y"))
        data.append(mrr)
        total += mrr

        current = add_months(current, 1)

    return {
        "labels": labels,
        "data": data,
        "total": total,
    }


@frappe.whitelist()
def get_churn_report(from_date=None, to_date=None):
    """
    Churn = subscriptions yang expired/cancelled per bulan.

    Args:
        from_date: Start date (default: 12 bulan lalu)
        to_date: End date (default: today)

    Returns:
        dict: {labels: [...], data: [...], total: X}
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please login to access reports."))

    from qalcuity.qalcuity.isolation import is_admin_user
    if not is_admin_user():
        frappe.throw(_("You do not have permission to access reports."))

    today = getdate(nowdate())
    to_date = getdate(to_date) if to_date else today
    from_date = getdate(from_date) if from_date else add_months(today, -11).replace(day=1)

    labels = []
    data = []
    total = 0

    current = from_date.replace(day=1)
    while current <= to_date:
        month_start = current
        month_end = add_months(current, 1).replace(day=1)

        # Count subscriptions that became expired or cancelled in this month
        churn = frappe.db.sql(
            """
            SELECT COUNT(*) as cnt
            FROM `tabQalcuity Subscription`
            WHERE status IN ('Expired', 'Cancelled')
            AND modified BETWEEN %s AND %s
            """,
            (month_start, month_end),
            as_dict=True,
        )

        month_churn = cint(churn[0].cnt) if churn else 0
        labels.append(current.strftime("%b %Y"))
        data.append(month_churn)
        total += month_churn

        current = add_months(current, 1)

    return {
        "labels": labels,
        "data": data,
        "total": total,
    }


@frappe.whitelist()
def get_plan_distribution():
    """
    Distribusi subscription per plan (active only).

    Returns:
        dict: {labels: [plan names], data: [counts]}
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please login to access reports."))

    from qalcuity.qalcuity.isolation import is_admin_user
    if not is_admin_user():
        frappe.throw(_("You do not have permission to access reports."))

    distribution = frappe.db.sql(
        """
        SELECT p.plan_name, COUNT(s.name) as cnt
        FROM `tabQalcuity Subscription` s
        JOIN `tabQalcuity Plan` p ON s.plan = p.name
        WHERE s.status IN ('Active', 'Grace Period')
        GROUP BY p.plan_name
        ORDER BY cnt DESC
        """,
        as_dict=True,
    )

    labels = [d.plan_name for d in distribution]
    data = [cint(d.cnt) for d in distribution]

    return {
        "labels": labels,
        "data": data,
    }


@frappe.whitelist()
def get_overview_stats():
    """
    Overview stats untuk reports page.

    Returns:
        dict: overview statistics
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please login to access reports."))

    from qalcuity.qalcuity.isolation import is_admin_user
    if not is_admin_user():
        frappe.throw(_("You do not have permission to access reports."))

    today = getdate(nowdate())

    # Total revenue (all approved payments)
    total_revenue = frappe.db.sql(
        """
        SELECT COALESCE(SUM(amount), 0) as total
        FROM `tabQalcuity Payment`
        WHERE status = 'Approved'
        """,
        as_dict=True,
    )

    # This month revenue
    month_start = today.replace(day=1)
    month_revenue = frappe.db.sql(
        """
        SELECT COALESCE(SUM(amount), 0) as total
        FROM `tabQalcuity Payment`
        WHERE status = 'Approved'
        AND payment_date >= %s
        """,
        (month_start,),
        as_dict=True,
    )

    # MRR (current month)
    mrr = frappe.db.sql(
        """
        SELECT COALESCE(SUM(plan_price), 0) as total
        FROM `tabQalcuity Subscription`
        WHERE status IN ('Active', 'Grace Period')
        """,
        as_dict=True,
    )

    # Total customers
    total_customers = frappe.db.count("Customer") or 0

    # Active subscriptions
    active_subs = frappe.db.count("Qalcuity Subscription", {"status": "Active"}) or 0

    # Grace period subs
    grace_subs = frappe.db.count("Qalcuity Subscription", {"status": "Grace Period"}) or 0

    # Expired subscriptions (this month)
    expired_this_month = frappe.db.sql(
        """
        SELECT COUNT(*) as cnt
        FROM `tabQalcuity Subscription`
        WHERE status = 'Expired'
        AND modified >= %s
        """,
        (month_start,),
        as_dict=True,
    )

    # Total subscriptions (for churn rate calculation)
    total_subs = frappe.db.count("Qalcuity Subscription") or 0

    # Churn rate: expired this month / total subs
    churn_rate = 0
    if total_subs > 0:
        churn_rate = round(
            (cint(expired_this_month[0].cnt) / total_subs) * 100, 1
        )

    return {
        "total_revenue": flt(total_revenue[0].total) if total_revenue else 0,
        "month_revenue": flt(month_revenue[0].total) if month_revenue else 0,
        "mrr": flt(mrr[0].total) if mrr else 0,
        "total_customers": total_customers,
        "active_subs": active_subs,
        "grace_subs": grace_subs,
        "expired_this_month": cint(expired_this_month[0].cnt) if expired_this_month else 0,
        "total_subs": total_subs,
        "churn_rate": churn_rate,
    }
