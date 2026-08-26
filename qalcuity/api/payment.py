# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Payment API endpoints for Qalcuity ERP.
Provides whitelisted methods for payment operations.
"""

import frappe
from frappe import _
from qalcuity.upload_security import validate_upload, sanitize_filename, get_max_file_size_mb
from qalcuity.input_validation import validate_amount, validate_reference_number, sanitize_text


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

    # Validate amount (enhanced with input_validation)
    amount = frappe.utils.flt(amount)
    is_valid_amount, amount_error = validate_amount(amount)
    if not is_valid_amount:
        frappe.throw(_(amount_error))
    if amount <= 0:
        frappe.throw(_("Payment amount must be greater than 0."))

    # Validate reference number
    if reference_number:
        is_valid_ref, ref_error = validate_reference_number(reference_number)
        if not is_valid_ref:
            frappe.throw(_(ref_error))
        reference_number = sanitize_text(reference_number, max_length=50)

    # Validate proof of payment file
    if proof_of_payment:
        # Validate file URL format
        if not proof_of_payment.startswith("/files/"):
            frappe.throw(_("Invalid file upload. Please re-upload your proof of payment."))

        # Extract filename from URL and validate extension
        import os
        proof_filename = os.path.basename(proof_of_payment)
        _, ext = os.path.splitext(proof_filename)
        ext = ext.lower()

        allowed_extensions = [".jpg", ".jpeg", ".png", ".webp", ".pdf"]
        if ext not in allowed_extensions:
            frappe.throw(
                _("File type '{0}' is not allowed. Allowed: {1}.").format(
                    ext, ", ".join(allowed_extensions)
                )
            )

        # Check for dangerous double extensions
        name_without_ext = os.path.splitext(proof_filename)[0]
        if "." in name_without_ext:
            frappe.throw(_("File name with multiple extensions is not allowed."))

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

    # Sanitize reason
    reason = sanitize_text(reason, max_length=500)
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
def get_my_payments(page=1, page_size=10):
    """
    Get payments for the current user (Customer role) with pagination.

    Args:
        page: Page number (default: 1)
        page_size: Items per page (default: 10)

    Returns:
        dict: {data: [...], total: int, page: int, page_size: int, total_pages: int}
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
        return {
            "data": [],
            "total": 0,
            "page": 1,
            "page_size": int(page_size),
            "total_pages": 0,
        }

    # Validate pagination params
    page = max(1, int(page))
    page_size = max(1, min(50, int(page_size)))
    start = (page - 1) * page_size

    # Get total count
    total = frappe.db.count(
        "Qalcuity Payment",
        filters={"subscription": ["in", subscriptions]},
    )

    total_pages = max(1, -(-total // page_size))  # Ceiling division

    # Get paginated payments
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
        limit_page_length=page_size,
        start=start,
    )

    return {
        "data": payments,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


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
            # Rollback semua yang sudah di-approve dalam batch ini
            if approved_count > 0:
                frappe.db.rollback()
                approved_count = 0
                results = [
                    r for r in results if r.get("status") != "success"
                ]
                # Tandai semua yang sebelumnya sukses sebagai error
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

    # Sanitize reason
    reason = sanitize_text(reason, max_length=500)
    if not reason:
        frappe.throw(_("Rejection reason is required."))

    if isinstance(payment_names, str):
        payment_names = frappe.parse_json(payment_names)

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
            # Rollback semua yang sudah di-reject dalam batch ini
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
    return results
