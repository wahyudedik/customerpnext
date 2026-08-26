# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Data Export API for Qalcuity ERP.
Provides CSV export for subscriptions, payments, plan changes, and login logs.
Customer: hanya data sendiri.
Admin/System Manager: semua data.
"""

import frappe
import csv
import io
from frappe import _


def _is_admin():
    """Cek apakah user adalah admin/superadmin/system manager."""
    user = frappe.session.user
    roles = frappe.get_roles(user)
    return any(r in roles for r in ["System Manager", "Qalcuity Superadmin", "Qalcuity Admin"])


def _get_customer():
    """Ambil customer dari Portal User. Return None jika admin."""
    user = frappe.session.user
    return frappe.db.get_value("Portal User", {"user": user}, "parent")


def _get_subscription_ids(customer):
    """Ambil semua subscription ID milik customer."""
    subs = frappe.get_all(
        "Qalcuity Subscription",
        filters={"customer": customer},
        fields=["name"],
    )
    return [s.name for s in subs]


def _set_csv_response(filename, output):
    """Set frappe response untuk CSV download."""
    frappe.response["type"] = "download"
    frappe.response["content_type"] = "text/csv; charset=utf-8"
    frappe.response["filename"] = filename
    frappe.response["filecontent"] = "\ufeff" + output.getvalue()  # BOM for Excel


# =============================================================================
# Export Subscriptions
# =============================================================================
@frappe.whitelist()
def export_subscriptions(format="csv"):
    """
    Export subscriptions.
    Customer: hanya subscription sendiri.
    Admin: semua subscriptions.
    """
    is_admin = _is_admin()
    customer = _get_customer()

    filters = {}
    if not is_admin and customer:
        filters["customer"] = customer
    elif not is_admin and not customer:
        # Non-admin non-customer — return empty
        frappe.response["type"] = "download"
        frappe.response["content_type"] = "text/csv; charset=utf-8"
        frappe.response["filename"] = "subscriptions.csv"
        frappe.response["filecontent"] = "ID,Customer,Plan,Status,Start Date,End Date,Trial,Auto Renew,Created"
        return

    subs = frappe.get_all(
        "Qalcuity Subscription",
        filters=filters,
        fields=["name", "customer", "plan", "status", "start_date", "end_date", "is_trial", "auto_renew", "creation"],
        order_by="creation desc",
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Customer", "Plan", "Status", "Start Date", "End Date", "Trial", "Auto Renew", "Created"])

    for sub in subs:
        writer.writerow([
            sub.name,
            sub.customer or "",
            sub.plan or "",
            sub.status or "",
            sub.start_date or "",
            sub.end_date or "",
            "Yes" if sub.is_trial else "No",
            "Yes" if sub.auto_renew else "No",
            str(sub.creation) if sub.creation else "",
        ])

    _set_csv_response("subscriptions.csv", output)


# =============================================================================
# Export Payments
# =============================================================================
@frappe.whitelist()
def export_payments(format="csv"):
    """
    Export payments.
    Customer: hanya payments sendiri (via subscription).
    Admin: semua payments.
    """
    is_admin = _is_admin()
    customer = _get_customer()

    filters = {}
    if not is_admin and customer:
        # Customer — get subscription IDs first, then filter payments
        sub_ids = _get_subscription_ids(customer)
        if not sub_ids:
            frappe.response["type"] = "download"
            frappe.response["content_type"] = "text/csv; charset=utf-8"
            frappe.response["filename"] = "payments.csv"
            frappe.response["filecontent"] = "ID,Subscription,Amount,Currency,Payment Method,Payment Date,Status,Reference Number,Bank Account,Created"
            return
        filters["subscription"] = ["in", sub_ids]
    elif not is_admin and not customer:
        frappe.response["type"] = "download"
        frappe.response["content_type"] = "text/csv; charset=utf-8"
        frappe.response["filename"] = "payments.csv"
        frappe.response["filecontent"] = "ID,Subscription,Amount,Currency,Payment Method,Payment Date,Status,Reference Number,Bank Account,Created"
        return

    payments = frappe.get_all(
        "Qalcuity Payment",
        filters=filters,
        fields=[
            "name", "subscription", "amount", "currency", "payment_method",
            "payment_date", "status", "reference_number", "bank_account_name", "creation",
        ],
        order_by="creation desc",
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Subscription", "Amount", "Currency", "Payment Method", "Payment Date", "Status", "Reference Number", "Bank Account", "Created"])

    for p in payments:
        writer.writerow([
            p.name,
            p.subscription or "",
            p.amount or 0,
            p.currency or "IDR",
            p.payment_method or "",
            p.payment_date or "",
            p.status or "",
            p.reference_number or "",
            p.bank_account_name or "",
            str(p.creation) if p.creation else "",
        ])

    _set_csv_response("payments.csv", output)


# =============================================================================
# Export Plan Changes
# =============================================================================
@frappe.whitelist()
def export_plan_changes(format="csv"):
    """
    Export plan changes history.
    Customer: hanya perubahan sendiri.
    Admin: semua perubahan.
    """
    is_admin = _is_admin()
    customer = _get_customer()

    filters = {}
    if not is_admin and customer:
        filters["customer"] = customer
    elif not is_admin and not customer:
        frappe.response["type"] = "download"
        frappe.response["content_type"] = "text/csv; charset=utf-8"
        frappe.response["filename"] = "plan_changes.csv"
        frappe.response["filecontent"] = "ID,Customer,Subscription,Current Plan,New Plan,Change Type,Status,Effective Date,Reason,Amount to Pay,Created"
        return

    changes = frappe.get_all(
        "Qalcuity Plan Change",
        filters=filters,
        fields=[
            "name", "customer", "subscription", "current_plan", "new_plan",
            "change_type", "status", "effective_date", "reason", "amount_to_pay", "creation",
        ],
        order_by="creation desc",
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Customer", "Subscription", "Current Plan", "New Plan", "Change Type", "Status", "Effective Date", "Reason", "Amount to Pay", "Created"])

    for c in changes:
        writer.writerow([
            c.name,
            c.customer or "",
            c.subscription or "",
            c.current_plan or "",
            c.new_plan or "",
            c.change_type or "",
            c.status or "",
            c.effective_date or "",
            (c.reason or "").replace("\n", " "),
            c.amount_to_pay or 0,
            str(c.creation) if c.creation else "",
        ])

    _set_csv_response("plan_changes.csv", output)


# =============================================================================
# Export Login Logs
# =============================================================================
@frappe.whitelist()
def export_login_logs(format="csv"):
    """
    Export login logs — admin only.
    Customer tidak bisa export login logs.
    """
    if not _is_admin():
        frappe.throw(_("You do not have permission to export login logs."), frappe.PermissionError)

    logs = frappe.get_all(
        "Qalcuity Login Log",
        fields=[
            "name", "user", "customer", "status", "login_method",
            "ip_address", "timestamp", "session_id", "user_agent", "failure_reason", "creation",
        ],
        order_by="creation desc",
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "User", "Customer", "Status", "Login Method", "IP Address", "Timestamp", "Session ID", "User Agent", "Failure Reason", "Created"])

    for log in logs:
        writer.writerow([
            log.name,
            log.user or "",
            log.customer or "",
            log.status or "",
            log.login_method or "",
            log.ip_address or "",
            str(log.timestamp) if log.timestamp else "",
            log.session_id or "",
            (log.user_agent or "").replace("\n", " "),
            (log.failure_reason or "").replace("\n", " "),
            str(log.creation) if log.creation else "",
        ])

    _set_csv_response("login_logs.csv", output)


# =============================================================================
# Export Preview
# =============================================================================
@frappe.whitelist()
def get_export_preview(data_type, limit=10):
    """
    Preview data sebelum export.
    Return: {columns: [...], rows: [...], total: X}

    Args:
        data_type: 'subscriptions', 'payments', 'plan_changes', or 'login_logs'
        limit: number of preview rows (default 10)
    """
    is_admin = _is_admin()
    customer = _get_customer()
    limit = min(int(limit), 50)  # Cap at 50

    if data_type == "subscriptions":
        return _preview_subscriptions(is_admin, customer, limit)
    elif data_type == "payments":
        return _preview_payments(is_admin, customer, limit)
    elif data_type == "plan_changes":
        return _preview_plan_changes(is_admin, customer, limit)
    elif data_type == "login_logs":
        if not is_admin:
            frappe.throw(_("You do not have permission to preview login logs."), frappe.PermissionError)
        return _preview_login_logs(limit)
    else:
        frappe.throw(_("Invalid data type: {0}").format(data_type))


def _preview_subscriptions(is_admin, customer, limit):
    """Preview subscriptions data."""
    filters = {}
    if not is_admin and customer:
        filters["customer"] = customer
    elif not is_admin and not customer:
        return {"columns": [], "rows": [], "total": 0}

    total = frappe.db.count("Qalcuity Subscription", filters=filters)
    subs = frappe.get_all(
        "Qalcuity Subscription",
        filters=filters,
        fields=["name", "customer", "plan", "status", "start_date", "end_date", "is_trial", "auto_renew", "creation"],
        order_by="creation desc",
        limit_page_length=limit,
    )

    columns = ["ID", "Customer", "Plan", "Status", "Start Date", "End Date", "Trial", "Auto Renew", "Created"]
    rows = []
    for sub in subs:
        rows.append([
            sub.name,
            sub.customer or "",
            sub.plan or "",
            sub.status or "",
            str(sub.start_date) if sub.start_date else "",
            str(sub.end_date) if sub.end_date else "",
            "Yes" if sub.is_trial else "No",
            "Yes" if sub.auto_renew else "No",
            str(sub.creation) if sub.creation else "",
        ])

    return {"columns": columns, "rows": rows, "total": total}


def _preview_payments(is_admin, customer, limit):
    """Preview payments data."""
    filters = {}
    if not is_admin and customer:
        sub_ids = _get_subscription_ids(customer)
        if not sub_ids:
            return {"columns": [], "rows": [], "total": 0}
        filters["subscription"] = ["in", sub_ids]
    elif not is_admin and not customer:
        return {"columns": [], "rows": [], "total": 0}

    total = frappe.db.count("Qalcuity Payment", filters=filters)
    payments = frappe.get_all(
        "Qalcuity Payment",
        filters=filters,
        fields=[
            "name", "subscription", "amount", "currency", "payment_method",
            "payment_date", "status", "reference_number", "bank_account_name", "creation",
        ],
        order_by="creation desc",
        limit_page_length=limit,
    )

    columns = ["ID", "Subscription", "Amount", "Currency", "Payment Method", "Payment Date", "Status", "Reference Number", "Bank Account", "Created"]
    rows = []
    for p in payments:
        rows.append([
            p.name,
            p.subscription or "",
            p.amount or 0,
            p.currency or "IDR",
            p.payment_method or "",
            str(p.payment_date) if p.payment_date else "",
            p.status or "",
            p.reference_number or "",
            p.bank_account_name or "",
            str(p.creation) if p.creation else "",
        ])

    return {"columns": columns, "rows": rows, "total": total}


def _preview_plan_changes(is_admin, customer, limit):
    """Preview plan changes data."""
    filters = {}
    if not is_admin and customer:
        filters["customer"] = customer
    elif not is_admin and not customer:
        return {"columns": [], "rows": [], "total": 0}

    total = frappe.db.count("Qalcuity Plan Change", filters=filters)
    changes = frappe.get_all(
        "Qalcuity Plan Change",
        filters=filters,
        fields=[
            "name", "customer", "subscription", "current_plan", "new_plan",
            "change_type", "status", "effective_date", "reason", "amount_to_pay", "creation",
        ],
        order_by="creation desc",
        limit_page_length=limit,
    )

    columns = ["ID", "Customer", "Subscription", "Current Plan", "New Plan", "Change Type", "Status", "Effective Date", "Reason", "Amount to Pay", "Created"]
    rows = []
    for c in changes:
        rows.append([
            c.name,
            c.customer or "",
            c.subscription or "",
            c.current_plan or "",
            c.new_plan or "",
            c.change_type or "",
            c.status or "",
            str(c.effective_date) if c.effective_date else "",
            (c.reason or "").replace("\n", " "),
            c.amount_to_pay or 0,
            str(c.creation) if c.creation else "",
        ])

    return {"columns": columns, "rows": rows, "total": total}


def _preview_login_logs(limit):
    """Preview login logs data (admin only)."""
    total = frappe.db.count("Qalcuity Login Log")
    logs = frappe.get_all(
        "Qalcuity Login Log",
        fields=[
            "name", "user", "customer", "status", "login_method",
            "ip_address", "timestamp", "session_id", "user_agent", "failure_reason", "creation",
        ],
        order_by="creation desc",
        limit_page_length=limit,
    )

    columns = ["ID", "User", "Customer", "Status", "Login Method", "IP Address", "Timestamp", "Session ID", "User Agent", "Failure Reason", "Created"]
    rows = []
    for log in logs:
        rows.append([
            log.name,
            log.user or "",
            log.customer or "",
            log.status or "",
            log.login_method or "",
            log.ip_address or "",
            str(log.timestamp) if log.timestamp else "",
            log.session_id or "",
            (log.user_agent or "").replace("\n", " "),
            (log.failure_reason or "").replace("\n", " "),
            str(log.creation) if log.creation else "",
        ])

    return {"columns": columns, "rows": rows, "total": total}
