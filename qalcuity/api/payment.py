# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Payment API endpoints for Qalcuity ERP.
Provides whitelisted methods for payment operations.
"""

import frappe
from frappe import _


@frappe.whitelist()
def submit_payment(subscription, amount, payment_method, payment_date, proof_of_payment=None, reference_number=None):
    """
    Submit a new payment for a subscription.

    Args:
        subscription: Name of Qalcuity Subscription
        amount: Payment amount
        payment_method: Bank Transfer, E-Wallet, or Virtual Account
        payment_date: Date of payment
        proof_of_payment: Attached file URL
        reference_number: Bank reference number

    Returns:
        dict: Created payment document
    """
    # Validate subscription exists
    if not frappe.db.exists("Qalcuity Subscription", subscription):
        frappe.throw(_("Subscription {0} not found.").format(subscription))

    # Validate subscription status
    sub_status = frappe.db.get_value("Qalcuity Subscription", subscription, "status")
    if sub_status not in ["Draft", "Pending Payment"]:
        frappe.throw(
            _("Cannot submit payment for a {0} subscription.").format(sub_status)
        )

    # Validate amount
    amount = frappe.utils.flt(amount)
    if amount <= 0:
        frappe.throw(_("Payment amount must be greater than 0."))

    # Get plan price for validation
    plan_price = frappe.db.get_value(
        "Qalcuity Plan",
        frappe.db.get_value("Qalcuity Subscription", subscription, "plan"),
        "price",
    )
    if amount < plan_price:
        frappe.msgprint(
            _("Warning: Payment amount ({0}) is less than plan price ({1}).").format(
                amount, plan_price
            ),
            indicator="orange",
        )

    # Create payment
    payment = frappe.get_doc(
        {
            "doctype": "Qalcuity Payment",
            "subscription": subscription,
            "amount": amount,
            "currency": "IDR",
            "payment_method": payment_method,
            "payment_date": payment_date,
            "proof_of_payment": proof_of_payment,
            "reference_number": reference_number,
            "status": "Pending",
        }
    )
    payment.insert(ignore_permissions=True)
    frappe.db.commit()

    return payment.as_dict()


@frappe.whitelist()
def approve_payment(payment_name):
    """
    Approve a pending payment.

    Args:
        payment_name: Name of Qalcuity Payment

    Returns:
        dict: Updated payment document
    """
    # Check permissions
    if not frappe.has_permission("Qalcuity Payment", "write"):
        frappe.throw(_("Insufficient permissions to approve payments."))

    payment = frappe.get_doc("Qalcuity Payment", payment_name)

    if payment.status != "Pending":
        frappe.throw(
            _("Payment {0} is not pending (status: {1}).").format(
                payment_name, payment.status
            )
        )

    payment.approve()
    frappe.db.commit()

    return payment.as_dict()


@frappe.whitelist()
def reject_payment(payment_name, reason):
    """
    Reject a pending payment.

    Args:
        payment_name: Name of Qalcuity Payment
        reason: Rejection reason

    Returns:
        dict: Updated payment document
    """
    # Check permissions
    if not frappe.has_permission("Qalcuity Payment", "write"):
        frappe.throw(_("Insufficient permissions to reject payments."))

    if not reason:
        frappe.throw(_("Rejection reason is required."))

    payment = frappe.get_doc("Qalcuity Payment", payment_name)

    if payment.status != "Pending":
        frappe.throw(
            _("Payment {0} is not pending (status: {1}).").format(
                payment_name, payment.status
            )
        )

    payment.reject(reason=reason)
    frappe.db.commit()

    return payment.as_dict()


@frappe.whitelist()
def get_payment_status(payment_name):
    """
    Get payment status and details.

    Args:
        payment_name: Name of Qalcuity Payment

    Returns:
        dict: Payment status information
    """
    payment = frappe.get_doc("Qalcuity Payment", payment_name)
    return {
        "name": payment.name,
        "status": payment.status,
        "amount": payment.amount,
        "currency": payment.currency,
        "payment_method": payment.payment_method,
        "payment_date": payment.payment_date,
        "reference_number": payment.reference_number,
        "reviewed_by": payment.reviewed_by,
        "review_date": payment.review_date,
        "rejection_reason": payment.rejection_reason,
    }


@frappe.whitelist()
def get_my_payments():
    """
    Get payments for the current user (Customer role).

    Returns:
        list: List of payment records
    """
    user = frappe.session.user

    # Get customer linked to user
    customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
    if not customer:
        frappe.throw(_("No customer account found for current user."))

    # Get subscriptions for this customer
    subscriptions = frappe.get_all(
        "Qalcuity Subscription",
        filters={"customer": customer},
        pluck="name",
    )

    if not subscriptions:
        return []

    # Get payments for these subscriptions
    payments = frappe.get_all(
        "Qalcuity Payment",
        filters={"subscription": ["in", subscriptions]},
        fields=[
            "name",
            "subscription",
            "amount",
            "currency",
            "payment_method",
            "payment_date",
            "status",
            "reference_number",
        ],
        order_by="creation desc",
    )

    return payments


@frappe.whitelist()
def bulk_approve_payments(payment_names):
    """Bulk approve multiple payments. Used by list view.

    Args:
        payment_names: JSON array of payment names

    Returns:
        list: Results for each payment
    """
    # Check permissions
    if not frappe.has_permission("Qalcuity Payment", "write"):
        frappe.throw(_("Insufficient permissions to approve payments."))

    if isinstance(payment_names, str):
        payment_names = frappe.parse_json(payment_names)

    results = []
    for name in payment_names:
        try:
            doc = frappe.get_doc("Qalcuity Payment", name)
            if doc.status == "Pending":
                doc.approve()
                results.append({"name": name, "status": "success"})
            else:
                results.append({
                    "name": name,
                    "status": "skipped",
                    "reason": "Status is {0}".format(doc.status),
                })
        except Exception as e:
            frappe.db.rollback()
            results.append({"name": name, "status": "error", "reason": str(e)})

    frappe.db.commit()
    return results


@frappe.whitelist()
def bulk_reject_payments(payment_names, reason):
    """Bulk reject multiple payments with a reason.

    Args:
        payment_names: JSON array of payment names
        reason: Rejection reason

    Returns:
        list: Results for each payment
    """
    # Check permissions
    if not frappe.has_permission("Qalcuity Payment", "write"):
        frappe.throw(_("Insufficient permissions to reject payments."))

    if not reason:
        frappe.throw(_("Rejection reason is required."))

    if isinstance(payment_names, str):
        payment_names = frappe.parse_json(payment_names)

    results = []
    for name in payment_names:
        try:
            doc = frappe.get_doc("Qalcuity Payment", name)
            if doc.status == "Pending":
                doc.reject(reason=reason)
                results.append({"name": name, "status": "success"})
            else:
                results.append({
                    "name": name,
                    "status": "skipped",
                    "reason": "Status is {0}".format(doc.status),
                })
        except Exception as e:
            frappe.db.rollback()
            results.append({"name": name, "status": "error", "reason": str(e)})

    frappe.db.commit()
    return results
