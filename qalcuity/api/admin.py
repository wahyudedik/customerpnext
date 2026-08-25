# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Admin Review Queue API endpoints for Qalcuity ERP.
Provides whitelisted methods for superadmin/admin payment review operations.
"""

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from qalcuity.qalcuity.isolation import is_admin_user


# =============================================================================
# Permission Helper
# =============================================================================

def _require_admin():
    """Pastikan user adalah Superadmin atau Admin. Throw error jika bukan."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please login to access admin functions."))

    if not is_admin_user(user):
        frappe.throw(
            _("Access denied. Only Qalcuity Superadmin or Admin can perform this action."),
            frappe.PermissionError,
        )


# =============================================================================
# API Endpoints
# =============================================================================

@frappe.whitelisted()
def get_pending_payments(filters=None):
    """
    Get payments list with filters for admin review queue.

    Args:
        filters: dict with optional keys:
            - status: "Pending", "Approved", "Rejected" (default: all)
            - date_from: start date string (YYYY-MM-DD)
            - date_to: end date string (YYYY-MM-DD)
            - customer: customer name filter

    Returns:
        list: List of payment dicts with customer info
    """
    _require_admin()

    if isinstance(filters, str):
        filters = frappe.parse_json(filters)

    if not filters:
        filters = {}

    # Build filter list for frappe.get_all
    conditions = []

    status = filters.get("status")
    if status:
        conditions.append({"status": status})
    else:
        # Default: show Pending only
        conditions.append({"status": "Pending"})

    date_from = filters.get("date_from")
    if date_from:
        conditions.append({"payment_date": [">=", date_from]})

    date_to = filters.get("date_to")
    if date_to:
        conditions.append({"payment_date": ["<=", date_to]})

    # Combine conditions
    filter_dict = {}
    if conditions:
        # frappe.get_all only supports simple filters, so we build them
        pass

    # Use frappe.get_list for more flexible querying
    payment_filters = {}
    if status:
        payment_filters["status"] = status
    else:
        payment_filters["status"] = "Pending"

    if date_from:
        payment_filters["payment_date"] = [">=", date_from]
    if date_to:
        if "payment_date" in payment_filters:
            payment_filters["payment_date"] = [">=", date_from, "<=", date_to]
        else:
            payment_filters["payment_date"] = ["<=", date_to]

    payments = frappe.get_all(
        "Qalcuity Payment",
        filters=payment_filters,
        fields=[
            "name",
            "subscription",
            "amount",
            "currency",
            "payment_method",
            "payment_date",
            "status",
            "reference_number",
            "proof_of_payment",
            "reviewed_by",
            "review_date",
            "rejection_reason",
            "creation",
        ],
        order_by="creation desc",
    )

    # Enrich with customer info
    result = []
    for p in payments:
        customer_name = None
        customer_email = None
        plan_name = None

        if p.subscription:
            sub_info = frappe.db.get_value(
                "Qalcuity Subscription",
                p.subscription,
                ["customer", "plan"],
                as_dict=True,
            )
            if sub_info:
                customer_name = sub_info.customer
                if sub_info.plan:
                    plan_name = frappe.db.get_value(
                        "Qalcuity Plan", sub_info.plan, "plan_name"
                    )

        # Apply customer filter if specified
        if filters.get("customer") and customer_name != filters["customer"]:
            continue

        if customer_name:
            customer_email = frappe.db.get_value("Customer", customer_name, "email_id")
            if not customer_email:
                # Fallback: get from portal user
                portal_user = frappe.db.get_value(
                    "Portal User",
                    {"parent": customer_name, "parenttype": "Customer"},
                    "user",
                )
                if portal_user:
                    customer_email = frappe.db.get_value("User", portal_user, "email")

        result.append({
            "name": p.name,
            "subscription": p.subscription,
            "amount": p.amount,
            "currency": p.currency or "IDR",
            "payment_method": p.payment_method,
            "payment_date": str(p.payment_date) if p.payment_date else None,
            "status": p.status,
            "reference_number": p.reference_number,
            "proof_of_payment": p.proof_of_payment,
            "reviewed_by": p.reviewed_by,
            "review_date": str(p.review_date) if p.review_date else None,
            "rejection_reason": p.rejection_reason,
            "creation": str(p.creation),
            "customer_name": customer_name,
            "customer_email": customer_email,
            "plan_name": plan_name,
        })

    return result


@frappe.whitelisted()
def approve_payment(payment_name):
    """
    Approve a single payment.

    Args:
        payment_name: Name of Qalcuity Payment

    Returns:
        dict: Updated payment document
    """
    _require_admin()

    if not frappe.db.exists("Qalcuity Payment", payment_name):
        frappe.throw(_("Payment {0} not found.").format(payment_name))

    payment = frappe.get_doc("Qalcuity Payment", payment_name)

    if payment.status != "Pending":
        frappe.throw(
            _("Payment {0} is not pending (status: {1}).").format(
                payment_name, payment.status
            )
        )

    payment.approve()
    frappe.db.commit()

    frappe.logger().info(
        "Qalcuity Admin: Payment {0} approved by {1}".format(
            payment_name, frappe.session.user
        )
    )

    return payment.as_dict()


@frappe.whitelisted()
def reject_payment(payment_name, reason):
    """
    Reject a single payment with reason.

    Args:
        payment_name: Name of Qalcuity Payment
        reason: Rejection reason

    Returns:
        dict: Updated payment document
    """
    _require_admin()

    if not reason:
        frappe.throw(_("Rejection reason is required."))

    if not frappe.db.exists("Qalcuity Payment", payment_name):
        frappe.throw(_("Payment {0} not found.").format(payment_name))

    payment = frappe.get_doc("Qalcuity Payment", payment_name)

    if payment.status != "Pending":
        frappe.throw(
            _("Payment {0} is not pending (status: {1}).").format(
                payment_name, payment.status
            )
        )

    payment.reject(reason=reason)
    frappe.db.commit()

    frappe.logger().info(
        "Qalcuity Admin: Payment {0} rejected by {1} — reason: {2}".format(
            payment_name, frappe.session.user, reason
        )
    )

    return payment.as_dict()


@frappe.whitelisted()
def bulk_approve_payments(payment_names):
    """
    Bulk approve multiple payments.

    Args:
        payment_names: JSON string or list of payment names

    Returns:
        list: Results for each payment
    """
    _require_admin()

    if isinstance(payment_names, str):
        payment_names = frappe.parse_json(payment_names)

    if not payment_names:
        frappe.throw(_("No payments selected."))

    results = []
    approved_count = 0

    for name in payment_names:
        try:
            doc = frappe.get_doc("Qalcuity Payment", name)
            if doc.status == "Pending":
                doc.approve()
                approved_count += 1
                results.append({"name": name, "status": "success"})
            else:
                results.append({
                    "name": name,
                    "status": "skipped",
                    "reason": "Status is {0}".format(doc.status),
                })
        except Exception as e:
            if approved_count > 0:
                frappe.db.rollback()
                approved_count = 0
                results = [
                    r for r in results if r.get("status") != "success"
                ]
                for r in results:
                    if r.get("status") not in ("error",):
                        r["status"] = "error"
                        r["reason"] = "Batch rolled back due to error: {0}".format(str(e))
                results.append({"name": name, "status": "error", "reason": str(e)})
            else:
                results.append({"name": name, "status": "error", "reason": str(e)})
            break

    if approved_count > 0:
        frappe.db.commit()

    frappe.logger().info(
        "Qalcuity Admin: Bulk approve by {0} — {1} payments approved".format(
            frappe.session.user, approved_count
        )
    )

    return results


@frappe.whitelisted()
def bulk_reject_payments(payment_names, reason):
    """
    Bulk reject multiple payments with a reason.

    Args:
        payment_names: JSON string or list of payment names
        reason: Rejection reason

    Returns:
        list: Results for each payment
    """
    _require_admin()

    if not reason:
        frappe.throw(_("Rejection reason is required."))

    if isinstance(payment_names, str):
        payment_names = frappe.parse_json(payment_names)

    if not payment_names:
        frappe.throw(_("No payments selected."))

    results = []
    rejected_count = 0

    for name in payment_names:
        try:
            doc = frappe.get_doc("Qalcuity Payment", name)
            if doc.status == "Pending":
                doc.reject(reason=reason)
                rejected_count += 1
                results.append({"name": name, "status": "success"})
            else:
                results.append({
                    "name": name,
                    "status": "skipped",
                    "reason": "Status is {0}".format(doc.status),
                })
        except Exception as e:
            if rejected_count > 0:
                frappe.db.rollback()
                rejected_count = 0
                results = [
                    r for r in results if r.get("status") != "success"
                ]
                for r in results:
                    if r.get("status") not in ("error",):
                        r["status"] = "error"
                        r["reason"] = "Batch rolled back due to error: {0}".format(str(e))
                results.append({"name": name, "status": "error", "reason": str(e)})
            else:
                results.append({"name": name, "status": "error", "reason": str(e)})
            break

    if rejected_count > 0:
        frappe.db.commit()

    frappe.logger().info(
        "Qalcuity Admin: Bulk reject by {0} — {1} payments rejected".format(
            frappe.session.user, rejected_count
        )
    )

    return results


@frappe.whitelisted()
def get_review_stats():
    """
    Get review queue statistics for the admin dashboard.

    Returns:
        dict: Statistics with total_pending, total_approved, total_rejected,
              total_amount_pending, total_amount_approved, pending_today, etc.
    """
    _require_admin()

    today = getdate(nowdate())

    # Total pending
    total_pending = frappe.db.count("Qalcuity Payment", {"status": "Pending"})

    # Total approved (all time)
    total_approved = frappe.db.count("Qalcuity Payment", {"status": "Approved"})

    # Total rejected (all time)
    total_rejected = frappe.db.count("Qalcuity Payment", {"status": "Rejected"})

    # Total amount pending
    total_amount_pending = frappe.db.sql(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM `tabQalcuity Payment`
        WHERE status = 'Pending'
        """,
        as_dict=True,
    )[0].get("coalesce(sum(amount), 0)", 0)

    # Total amount approved
    total_amount_approved = frappe.db.sql(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM `tabQalcuity Payment`
        WHERE status = 'Approved'
        """,
        as_dict=True,
    )[0].get("coalesce(sum(amount), 0)", 0)

    # Pending today
    pending_today = frappe.db.count(
        "Qalcuity Payment",
        {"status": "Pending", "creation": [">=", str(today)]},
    )

    # Approved today
    approved_today = frappe.db.count(
        "Qalcuity Payment",
        {"status": "Approved", "review_date": ["like", "{0}%".format(str(today))]},
    )

    # Rejected today
    rejected_today = frappe.db.count(
        "Qalcuity Payment",
        {"status": "Rejected", "review_date": ["like", "{0}%".format(str(today))]},
    )

    return {
        "total_pending": total_pending,
        "total_approved": total_approved,
        "total_rejected": total_rejected,
        "total_amount_pending": total_amount_pending,
        "total_amount_approved": total_amount_approved,
        "pending_today": pending_today,
        "approved_today": approved_today,
        "rejected_today": rejected_today,
    }
