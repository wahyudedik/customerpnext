# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Login Log API endpoints for Qalcuity ERP.
Provides whitelisted methods for querying login audit trail.
"""

import frappe
from frappe import _


@frappe.whitelist()
def get_login_logs(user=None, status=None, from_date=None, to_date=None, limit_page_length=20, start=0):
    """Get login logs.

    Admin/Superadmin/System Manager → semua logs.
    Customer → hanya log milik sendiri.

    Args:
        user: Filter by username (admin only)
        status: Filter by status (Success/Failed/Blocked)
        from_date: Filter from date (YYYY-MM-DD)
        to_date: Filter to date (YYYY-MM-DD)
        limit_page_length: Pagination limit (default 20)
        start: Pagination offset (default 0)

    Returns:
        dict: {logs: [...], total: int}
    """
    current_user = frappe.session.user
    roles = frappe.get_roles(current_user)
    is_admin = (
        current_user == "Administrator"
        or "System Manager" in roles
        or "Qalcuity Superadmin" in roles
        or "Qalcuity Admin" in roles
    )

    filters = {}

    # Customer — hanya bisa lihat log sendiri
    if not is_admin:
        filters["user"] = current_user
    elif user:
        filters["user"] = user

    if status:
        filters["status"] = status

    if from_date:
        filters["timestamp"] = (">=", from_date)

    if to_date:
        if "timestamp" in filters and isinstance(filters["timestamp"], tuple):
            filters["timestamp"] = (">=", from_date, "<=", to_date + " 23:59:59")
        else:
            filters["timestamp"] = ("<=", to_date + " 23:59:59")

    # Count total
    total = frappe.db.count("Qalcuity Login Log", filters)

    # Fetch logs
    logs = frappe.get_all(
        "Qalcuity Login Log",
        filters=filters,
        fields=[
            "name", "user", "customer", "status", "login_method",
            "ip_address", "user_agent", "failure_reason", "session_id", "timestamp",
        ],
        order_by="timestamp desc",
        start=start,
        page_length=limit_page_length,
    )

    # Enrich with customer name
    for log in logs:
        if log.customer:
            log.customer_name = frappe.db.get_value("Customer", log.customer, "customer_name")
        else:
            log.customer_name = None

    return {"logs": logs, "total": total}


@frappe.whitelist()
def get_login_stats():
    """Login statistics untuk admin dashboard.

    Returns:
        dict: Statistik login hari ini dan 7 hari terakhir
    """
    current_user = frappe.session.user
    roles = frappe.get_roles(current_user)
    is_admin = (
        current_user == "Administrator"
        or "System Manager" in roles
        or "Qalcuity Superadmin" in roles
        or "Qalcuity Admin" in roles
    )

    if not is_admin:
        frappe.throw(_("Insufficient permissions."))

    from frappe.utils import today, add_days, nowdate

    today_str = today()

    # Total attempts today
    total_today = frappe.db.count(
        "Qalcuity Login Log",
        filters={"timestamp": (">=", today_str)},
    )

    # Failed attempts today
    failed_today = frappe.db.count(
        "Qalcuity Login Log",
        filters={"timestamp": (">=", today_str), "status": "Failed"},
    )

    # Blocked attempts today
    blocked_today = frappe.db.count(
        "Qalcuity Login Log",
        filters={"timestamp": (">=", today_str), "status": "Blocked"},
    )

    # Unique IPs today
    unique_ips_today = frappe.db.sql(
        """SELECT COUNT(DISTINCT ip_address) FROM `tabQalcuity Login Log`
           WHERE DATE(timestamp) = %s AND ip_address IS NOT NULL AND ip_address != ''""",
        (today_str,),
    )[0][0]

    # Success rate
    success_today = frappe.db.count(
        "Qalcuity Login Log",
        filters={"timestamp": (">=", today_str), "status": "Success"},
    )
    success_rate = round((success_today / total_today * 100), 1) if total_today > 0 else 100

    # Failed attempts per day (last 7 days)
    failed_last_7 = []
    for i in range(6, -1, -1):
        day = add_days(today_str, -i)
        day_str = str(day)[:10]
        count = frappe.db.count(
            "Qalcuity Login Log",
            filters={"timestamp": (">=", day_str + " 00:00:00", "<", day_str + " 23:59:59"), "status": "Failed"},
        )
        failed_last_7.append({"date": day_str, "count": count})

    # Top failed IPs (last 7 days)
    seven_days_ago = add_days(today_str, -7)
    top_failed_ips = frappe.db.sql(
        """SELECT ip_address, COUNT(*) as count
           FROM `tabQalcuity Login Log`
           WHERE timestamp >= %s AND status IN ('Failed', 'Blocked') AND ip_address IS NOT NULL
           GROUP BY ip_address
           ORDER BY count DESC
           LIMIT 10""",
        (seven_days_ago,),
        as_dict=True,
    )

    return {
        "total_today": total_today,
        "failed_today": failed_today,
        "blocked_today": blocked_today,
        "unique_ips_today": unique_ips_today or 0,
        "success_rate": success_rate,
        "failed_last_7": failed_last_7,
        "top_failed_ips": top_failed_ips,
    }
