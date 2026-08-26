# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Plan Change API endpoints for Qalcuity ERP.
Provides whitelisted methods for plan upgrade/downgrade operations.
"""

import frappe
from frappe import _
from frappe.utils import getdate, date_diff, today
from qalcuity.qalcuity.input_validation import sanitize_text, validate_reason


@frappe.whitelist()
def preview_plan_change(subscription_id, new_plan_id):
    """
    Preview prorated calculation tanpa submit.

    Args:
        subscription_id: Name of Qalcuity Subscription
        new_plan_id: Name of Qalcuity Plan (new plan)

    Returns:
        dict: Preview data (current_plan, new_plan, prorated_credit, amount_to_pay, etc.)
    """
    # Validate subscription
    if not frappe.db.exists("Qalcuity Subscription", subscription_id):
        frappe.throw(_("Subscription {0} not found.").format(subscription_id))

    sub = frappe.get_doc("Qalcuity Subscription", subscription_id)

    # Validate subscription status
    if sub.status not in ("Active", "Grace Period"):
        frappe.throw(_("Only active subscriptions can change plans."))

    # Validate plan exists and is active
    if not frappe.db.exists("Qalcuity Plan", new_plan_id):
        frappe.throw(_("Plan {0} not found.").format(new_plan_id))

    if not frappe.db.get_value("Qalcuity Plan", new_plan_id, "is_active"):
        frappe.throw(_("Selected plan is not active."))

    # Get pricing info
    current_plan = sub.plan
    current_price = frappe.db.get_value("Qalcuity Plan", current_plan, "price") or 0
    new_price = frappe.db.get_value("Qalcuity Plan", new_plan_id, "price") or 0
    change_type = "Upgrade" if new_price > current_price else "Downgrade"

    # Calculate prorated credit
    prorated_credit = 0
    remaining_days = 0
    total_days = 0

    if sub.start_date and sub.end_date:
        end_date = getdate(sub.end_date)
        start_date = getdate(sub.start_date)
        effective = getdate(today())

        total_days = date_diff(end_date, start_date)
        remaining_days = date_diff(end_date, effective)

        if total_days > 0 and remaining_days > 0:
            prorated_credit = round((remaining_days / total_days) * current_price)

    amount_to_pay = max(0, new_price - prorated_credit)

    return {
        "current_plan": current_plan,
        "new_plan": new_plan_id,
        "change_type": change_type,
        "current_plan_price": current_price,
        "new_plan_price": new_price,
        "prorated_credit": prorated_credit,
        "amount_to_pay": amount_to_pay,
        "total_days": total_days,
        "remaining_days": remaining_days,
        "subscription_status": sub.status,
    }


@frappe.whitelist()
def submit_plan_change(subscription_id, new_plan_id, effective_date=None, reason=None):
    """
    Submit a plan change request.

    Args:
        subscription_id: Name of Qalcuity Subscription
        new_plan_id: Name of Qalcuity Plan (new plan)
        effective_date: Date when change takes effect (default: today)
        reason: Optional reason for change

    Returns:
        dict: Created plan change document
    """
    user = frappe.session.user
    customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
    if not customer:
        frappe.throw(_("No customer account found for current user."))

    # Validate subscription
    if not frappe.db.exists("Qalcuity Subscription", subscription_id):
        frappe.throw(_("Subscription {0} not found.").format(subscription_id))

    sub = frappe.get_doc("Qalcuity Subscription", subscription_id)
    if sub.customer != customer:
        frappe.throw(_("Subscription does not belong to this customer."))

    if sub.status not in ("Active", "Grace Period"):
        frappe.throw(_("Only active subscriptions can change plans."))

    # Validate plan
    if not frappe.db.exists("Qalcuity Plan", new_plan_id):
        frappe.throw(_("Plan {0} not found.").format(new_plan_id))

    if not frappe.db.get_value("Qalcuity Plan", new_plan_id, "is_active"):
        frappe.throw(_("Selected plan is not active."))

    if sub.plan == new_plan_id:
        frappe.throw(_("New plan must be different from current plan."))

    # Check for pending plan change
    pending = frappe.db.exists(
        "Qalcuity Plan Change",
        {"subscription": subscription_id, "status": "Pending"},
    )
    if pending:
        frappe.throw(
            _("You already have a pending plan change ({0}). Please wait for it to be processed.").format(
                pending
            )
        )

    # Sanitize reason if provided
    if reason:
        reason = sanitize_text(reason, max_length=500)
        is_valid_reason, reason_error = validate_reason(reason)
        if not is_valid_reason:
            frappe.throw(_(reason_error))

    # Create plan change
    plan_change = frappe.get_doc({
        "doctype": "Qalcuity Plan Change",
        "customer": customer,
        "subscription": subscription_id,
        "new_plan": new_plan_id,
        "effective_date": effective_date or today(),
        "reason": reason,
    })
    plan_change.insert(ignore_permissions=True)
    frappe.db.commit()

    return plan_change.as_dict()


@frappe.whitelist()
def get_my_plan_changes(page=1, page_size=10):
    """
    Get plan changes for the current user (Customer role) with pagination.

    Args:
        page: Page number (default: 1)
        page_size: Items per page (default: 10)

    Returns:
        dict: {data: [...], total: int, page: int, page_size: int, total_pages: int}
    """
    user = frappe.session.user
    customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
    if not customer:
        frappe.throw(_("No customer account found for current user."))

    # Validate pagination params
    page = max(1, int(page))
    page_size = max(1, min(50, int(page_size)))
    start = (page - 1) * page_size

    # Get total count
    total = frappe.db.count(
        "Qalcuity Plan Change",
        filters={"customer": customer},
    )

    total_pages = max(1, -(-total // page_size))  # Ceiling division

    # Get paginated plan changes
    plan_changes = frappe.get_all(
        "Qalcuity Plan Change",
        filters={"customer": customer},
        fields=[
            "name",
            "subscription",
            "current_plan",
            "new_plan",
            "change_type",
            "status",
            "current_plan_price",
            "new_plan_price",
            "prorated_credit",
            "amount_to_pay",
            "effective_date",
            "reason",
            "reviewed_by",
            "review_date",
            "rejection_reason",
            "creation",
        ],
        order_by="creation desc",
        limit_page_length=page_size,
        start=start,
    )

    return {
        "data": plan_changes,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@frappe.whitelist()
def get_pending_plan_changes(page=1, page_size=20):
    """
    Get pending plan changes for admin review.

    Args:
        page: Page number (default: 1)
        page_size: Items per page (default: 20)

    Returns:
        dict: {data: [...], total: int, page: int, page_size: int, total_pages: int}
    """
    # Check permissions
    if not frappe.has_permission("Qalcuity Plan Change", "write"):
        frappe.throw(_("Insufficient permissions to view pending plan changes."))

    # Validate pagination params
    page = max(1, int(page))
    page_size = max(1, min(50, int(page_size)))
    start = (page - 1) * page_size

    # Get total count
    total = frappe.db.count(
        "Qalcuity Plan Change",
        filters={"status": "Pending"},
    )

    total_pages = max(1, -(-total // page_size))

    plan_changes = frappe.get_all(
        "Qalcuity Plan Change",
        filters={"status": "Pending"},
        fields=[
            "name",
            "customer",
            "subscription",
            "current_plan",
            "new_plan",
            "change_type",
            "status",
            "current_plan_price",
            "new_plan_price",
            "prorated_credit",
            "amount_to_pay",
            "effective_date",
            "reason",
            "creation",
        ],
        order_by="creation asc",
        limit_page_length=page_size,
        start=start,
    )

    return {
        "data": plan_changes,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@frappe.whitelist()
def approve_plan_change(plan_change_id):
    """
    Approve a pending plan change (admin).

    Args:
        plan_change_id: Name of Qalcuity Plan Change

    Returns:
        dict: Updated plan change document
    """
    # Check permissions
    if not frappe.has_permission("Qalcuity Plan Change", "write"):
        frappe.throw(_("Insufficient permissions to approve plan changes."))

    plan_change = frappe.get_doc("Qalcuity Plan Change", plan_change_id)

    if plan_change.status != "Pending":
        frappe.throw(
            _("Plan change {0} is not pending (status: {1}).").format(
                plan_change_id, plan_change.status
            )
        )

    # Update status and submit (triggers on_submit → process_plan_change)
    plan_change.status = "Approved"
    plan_change.save(ignore_permissions=True)
    frappe.db.commit()

    # Reload to get completed status
    plan_change.reload()

    return plan_change.as_dict()


@frappe.whitelist()
def reject_plan_change(plan_change_id, reason):
    """
    Reject a pending plan change (admin).

    Args:
        plan_change_id: Name of Qalcuity Plan Change
        reason: Rejection reason

    Returns:
        dict: Updated plan change document
    """
    # Check permissions
    if not frappe.has_permission("Qalcuity Plan Change", "write"):
        frappe.throw(_("Insufficient permissions to reject plan changes."))

    if not reason:
        frappe.throw(_("Rejection reason is required."))

    # Sanitize reason
    reason = sanitize_text(reason, max_length=500)
    if not reason:
        frappe.throw(_("Rejection reason is required."))

    plan_change = frappe.get_doc("Qalcuity Plan Change", plan_change_id)

    if plan_change.status != "Pending":
        frappe.throw(
            _("Plan change {0} is not pending (status: {1}).").format(
                plan_change_id, plan_change.status
            )
        )

    plan_change.status = "Rejected"
    plan_change.rejection_reason = reason
    plan_change.reviewed_by = frappe.session.user
    plan_change.review_date = frappe.utils.now_datetime()
    plan_change.save(ignore_permissions=True)
    frappe.db.commit()

    return plan_change.as_dict()


@frappe.whitelist()
def cancel_plan_change(plan_change_id):
    """
    Cancel a pending plan change (customer can cancel their own).

    Args:
        plan_change_id: Name of Qalcuity Plan Change

    Returns:
        dict: Updated plan change document
    """
    plan_change = frappe.get_doc("Qalcuity Plan Change", plan_change_id)

    # Customer can only cancel their own
    user = frappe.session.user
    roles = frappe.get_roles(user)
    if "System Manager" not in roles and "Qalcuity Superadmin" not in roles and "Qalcuity Admin" not in roles:
        customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
        if not customer or plan_change.customer != customer:
            frappe.throw(_("You can only cancel your own plan changes."))

    if plan_change.status != "Pending":
        frappe.throw(
            _("Only pending plan changes can be cancelled (current status: {0}).").format(
                plan_change.status
            )
        )

    plan_change.status = "Cancelled"
    plan_change.save(ignore_permissions=True)
    frappe.db.commit()

    return plan_change.as_dict()
