# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity API v1 — Versioned Endpoints
=======================================

Semua wrapper endpoints untuk API v1.
Setiap endpoint:
- Memanggil existing implementation
- Menambahkan auth validation
- Menggunakan standard response format
- Error handling yang konsisten

Endpoint Categories:
- Public (allow_guest): get_plans, register
- Customer (require_customer_role): submit_payment, get_my_payments, dll
- Admin (require_admin_role): approve_payment, reject_payment, dll
- Settings: get_settings

Usage dari client:
    frappe.call({
        "method": "qalcuity.api.v1.endpoints.get_plans",
        "callback": function(r) { ... }
    })

Atau via API:
    POST /api/method/qalcuity.api.v1.endpoints.get_plans
"""

import frappe
from frappe import _

from qalcuity.api.v1.auth import (
    require_authentication,
    require_customer_role,
    require_admin_role,
    get_current_user_info,
    rate_limit_check,
)
from qalcuity.api.v1.responses import (
    success_response,
    error_response,
    ErrorCode,
)


# =============================================================================
# Helper: Standard Error Handler
# =============================================================================

def _handle_endpoint_error(e, endpoint_name):
    """
    Standard error handler untuk semua endpoints.

    Args:
        e: Exception yang terjadi
        endpoint_name: Nama endpoint untuk logging

    Returns:
        dict: Standard error response
    """
    if isinstance(e, frappe.AuthenticationError):
        return error_response(
            message=str(e) or "Authentication required",
            code=ErrorCode.UNAUTHORIZED,
            http_status=401,
        )
    elif isinstance(e, frappe.PermissionError):
        return error_response(
            message=str(e) or "Access denied",
            code=ErrorCode.FORBIDDEN,
            http_status=403,
        )
    elif isinstance(e, frappe.DoesNotExistError):
        return error_response(
            message=str(e) or "Resource not found",
            code=ErrorCode.NOT_FOUND,
            http_status=404,
        )
    elif isinstance(e, frappe.ValidationError):
        return error_response(
            message=str(e) or "Validation error",
            code=ErrorCode.VALIDATION_ERROR,
            http_status=400,
        )
    elif hasattr(frappe, 'TooManyRequestsError') and isinstance(e, frappe.TooManyRequestsError):
        return error_response(
            message=str(e) or "Rate limit exceeded",
            code=ErrorCode.RATE_LIMITED,
            http_status=429,
        )
    else:
        frappe.log_error(
            message=f"API v1 Error [{endpoint_name}]: {str(e)}",
            title="Qalcuity API v1 Error",
        )
        return error_response(
            message="Internal server error",
            code=ErrorCode.SERVER_ERROR,
            http_status=500,
        )


# =============================================================================
# PUBLIC ENDPOINTS (allow_guest)
# =============================================================================

@frappe.whitelist(allow_guest=True)
def get_plans():
    """
    Get all active plans with features.

    Public endpoint — tidak perlu login.

    Returns:
        dict: Standard success response dengan list plans
    """
    try:
        from qalcuity.api.plans import get_active_plans as _get_active_plans

        plans = _get_active_plans()
        return success_response(
            data=plans,
            message="Plans retrieved successfully",
            meta={"total": len(plans) if isinstance(plans, list) else 0},
        )
    except Exception as e:
        return _handle_endpoint_error(e, "get_plans")


@frappe.whitelist(allow_guest=True)
def register(full_name, email, password, company_name, phone):
    """
    Register a new customer.

    Public endpoint — tidak perlu login.
    Membuat: User → Customer → Portal User → Tenant (via hook)

    Args:
        full_name: Nama lengkap customer
        email: Email address (unique)
        password: Password (min 8 chars)
        company_name: Nama perusahaan
        phone: Nomor telepon

    Returns:
        dict: Standard success response dengan registration result
    """
    try:
        from qalcuity.api.registration import register_customer as _register_customer

        result = _register_customer(full_name, email, password, company_name, phone)
        return success_response(
            data=result,
            message="Registration successful. Please check your email for activation.",
        )
    except Exception as e:
        return _handle_endpoint_error(e, "register")


# =============================================================================
# CUSTOMER ENDPOINTS (require_customer_role)
# =============================================================================

@frappe.whitelist()
def submit_payment(subscription, amount, payment_method, payment_date,
                   proof_of_payment=None, reference_number=None):
    """
    Submit a new payment for a subscription.

    Customer endpoint — harus login sebagai customer.

    Args:
        subscription: Name of Qalcuity Subscription
        amount: Payment amount
        payment_method: Bank Transfer, E-Wallet, or Virtual Account
        payment_date: Date of payment
        proof_of_payment: Attached file URL (optional)
        reference_number: Bank reference number (optional)

    Returns:
        dict: Standard success response dengan payment data
    """
    try:
        user_info = require_customer_role()
        rate_limit_check(user_info["user"])

        from qalcuity.api.payment import submit_payment as _submit_payment

        result = _submit_payment(
            subscription=subscription,
            amount=amount,
            payment_method=payment_method,
            payment_date=payment_date,
            proof_of_payment=proof_of_payment,
            reference_number=reference_number,
        )
        return success_response(
            data=result,
            message="Payment submitted successfully",
        )
    except Exception as e:
        return _handle_endpoint_error(e, "submit_payment")


@frappe.whitelist()
def get_my_payments():
    """
    Get payment history for the current customer.

    Customer endpoint — harus login sebagai customer.

    Returns:
        dict: Standard success response dengan list payments
    """
    try:
        user_info = require_customer_role()
        rate_limit_check(user_info["user"])

        from qalcuity.api.payment import get_my_payments as _get_my_payments

        result = _get_my_payments()
        return success_response(
            data=result,
            message="Payment history retrieved successfully",
        )
    except Exception as e:
        return _handle_endpoint_error(e, "get_my_payments")


@frappe.whitelist()
def get_payment_status(payment_name):
    """
    Get status of a specific payment.

    Customer endpoint — harus login sebagai customer.

    Args:
        payment_name: Name of Qalcuity Payment

    Returns:
        dict: Standard success response dengan payment status
    """
    try:
        user_info = require_customer_role()
        rate_limit_check(user_info["user"])

        from qalcuity.api.payment import get_payment_status as _get_payment_status

        result = _get_payment_status(payment_name)
        return success_response(
            data=result,
            message="Payment status retrieved successfully",
        )
    except Exception as e:
        return _handle_endpoint_error(e, "get_payment_status")


@frappe.whitelist()
def get_profile():
    """
    Get profile data for the current user.

    Customer endpoint — harus login.

    Returns:
        dict: Standard success response dengan profile data
    """
    try:
        user_info = require_customer_role()
        rate_limit_check(user_info["user"])

        from qalcuity.api.profile import get_profile as _get_profile

        result = _get_profile()
        return success_response(
            data=result,
            message="Profile retrieved successfully",
        )
    except Exception as e:
        return _handle_endpoint_error(e, "get_profile")


@frappe.whitelist()
def update_profile(data):
    """
    Update profile data for the current user.

    Customer endpoint — harus login.

    Args:
        data: JSON string or dict with fields to update (full_name, phone, company_name)

    Returns:
        dict: Standard success response dengan update result
    """
    try:
        user_info = require_customer_role()
        rate_limit_check(user_info["user"])

        from qalcuity.api.profile import update_profile as _update_profile

        result = _update_profile(data)
        return success_response(
            data=result,
            message=result.get("message", "Profile updated successfully"),
        )
    except Exception as e:
        return _handle_endpoint_error(e, "update_profile")


@frappe.whitelist()
def get_dashboard():
    """
    Get dashboard data for the current customer.

    Customer endpoint — harus login sebagai customer.

    Returns:
        dict: Standard success response dengan dashboard data
    """
    try:
        user_info = require_customer_role()
        rate_limit_check(user_info["user"])

        from qalcuity.api.dashboard import get_dashboard_data as _get_dashboard_data

        result = _get_dashboard_data()
        return success_response(
            data=result,
            message="Dashboard data retrieved successfully",
        )
    except Exception as e:
        return _handle_endpoint_error(e, "get_dashboard")


@frappe.whitelist()
def get_account_status():
    """
    Get comprehensive account status for the current customer.

    Customer endpoint — harus login.

    Returns:
        dict: Standard success response dengan account status
    """
    try:
        user_info = require_customer_role()
        rate_limit_check(user_info["user"])

        from qalcuity.api.account_status import get_account_status as _get_account_status

        result = _get_account_status()
        return success_response(
            data=result,
            message="Account status retrieved successfully",
        )
    except Exception as e:
        return _handle_endpoint_error(e, "get_account_status")


@frappe.whitelist()
def get_my_subscription_history(limit_page_length=20, start=0):
    """
    Get subscription history for the current customer.

    Customer endpoint — harus login.

    Args:
        limit_page_length: Jumlah baris per halaman (default: 20)
        start: Offset untuk pagination (default: 0)

    Returns:
        dict: Standard success response dengan subscription history
    """
    try:
        user_info = require_customer_role()
        rate_limit_check(user_info["user"])

        from qalcuity.api.subscription_history import (
            get_my_subscription_history as _get_my_subscription_history,
        )

        result = _get_my_subscription_history(
            limit_page_length=limit_page_length,
            start=start,
        )
        return success_response(
            data=result.get("data", []),
            message="Subscription history retrieved successfully",
            meta={"total": result.get("total", 0)},
        )
    except Exception as e:
        return _handle_endpoint_error(e, "get_my_subscription_history")


@frappe.whitelist()
def get_my_audit_logs(limit_page_length=20, start=0):
    """
    Get audit logs for the current customer.

    Customer endpoint — harus login.

    Args:
        limit_page_length: Jumlah baris per halaman (default: 20)
        start: Offset untuk pagination (default: 0)

    Returns:
        dict: Standard success response dengan audit logs
    """
    try:
        user_info = require_customer_role()
        rate_limit_check(user_info["user"])

        from qalcuity.api.audit import get_my_audit_logs as _get_my_audit_logs

        result = _get_my_audit_logs(
            limit_page_length=limit_page_length,
            start=start,
        )
        return success_response(
            data=result.get("data", []),
            message="Audit logs retrieved successfully",
            meta={"total": result.get("total", 0)},
        )
    except Exception as e:
        return _handle_endpoint_error(e, "get_my_audit_logs")


# =============================================================================
# ADMIN ENDPOINTS (require_admin_role)
# =============================================================================

@frappe.whitelist()
def get_pending_reviews(filters=None):
    """
    Get payments list for admin review queue.

    Admin endpoint — harus login sebagai admin/superadmin.

    Args:
        filters: dict with optional keys: status, date_from, date_to, customer

    Returns:
        dict: Standard success response dengan list payments
    """
    try:
        user = require_admin_role()
        rate_limit_check(user)

        from qalcuity.api.admin import get_pending_payments as _get_pending_payments

        result = _get_pending_payments(filters=filters)
        return success_response(
            data=result,
            message="Pending reviews retrieved successfully",
            meta={"total": len(result) if isinstance(result, list) else 0},
        )
    except Exception as e:
        return _handle_endpoint_error(e, "get_pending_reviews")


@frappe.whitelist()
def approve_payment(payment_name):
    """
    Approve a single payment.

    Admin endpoint — harus login sebagai admin/superadmin.

    Args:
        payment_name: Name of Qalcuity Payment

    Returns:
        dict: Standard success response dengan updated payment
    """
    try:
        user = require_admin_role()
        rate_limit_check(user)

        from qalcuity.api.admin import approve_payment as _approve_payment

        result = _approve_payment(payment_name)
        return success_response(
            data=result,
            message="Payment approved successfully",
        )
    except Exception as e:
        return _handle_endpoint_error(e, "approve_payment")


@frappe.whitelist()
def reject_payment(payment_name, reason):
    """
    Reject a single payment with reason.

    Admin endpoint — harus login sebagai admin/superadmin.

    Args:
        payment_name: Name of Qalcuity Payment
        reason: Rejection reason

    Returns:
        dict: Standard success response dengan updated payment
    """
    try:
        user = require_admin_role()
        rate_limit_check(user)

        from qalcuity.api.admin import reject_payment as _reject_payment

        result = _reject_payment(payment_name, reason)
        return success_response(
            data=result,
            message="Payment rejected successfully",
        )
    except Exception as e:
        return _handle_endpoint_error(e, "reject_payment")


@frappe.whitelist()
def bulk_approve_payments(payment_names):
    """
    Bulk approve multiple payments.

    Admin endpoint — harus login sebagai admin/superadmin.

    Args:
        payment_names: JSON string or list of payment names

    Returns:
        dict: Standard success response dengan results per payment
    """
    try:
        user = require_admin_role()
        rate_limit_check(user)

        from qalcuity.api.admin import bulk_approve_payments as _bulk_approve_payments

        result = _bulk_approve_payments(payment_names)
        approved_count = len([r for r in result if r.get("status") == "success"]) if isinstance(result, list) else 0
        return success_response(
            data=result,
            message=f"Bulk approve completed. {approved_count} payments approved.",
            meta={"approved_count": approved_count, "total": len(result) if isinstance(result, list) else 0},
        )
    except Exception as e:
        return _handle_endpoint_error(e, "bulk_approve_payments")


@frappe.whitelist()
def bulk_reject_payments(payment_names, reason):
    """
    Bulk reject multiple payments with a reason.

    Admin endpoint — harus login sebagai admin/superadmin.

    Args:
        payment_names: JSON string or list of payment names
        reason: Rejection reason

    Returns:
        dict: Standard success response dengan results per payment
    """
    try:
        user = require_admin_role()
        rate_limit_check(user)

        from qalcuity.api.admin import bulk_reject_payments as _bulk_reject_payments

        result = _bulk_reject_payments(payment_names, reason)
        rejected_count = len([r for r in result if r.get("status") == "success"]) if isinstance(result, list) else 0
        return success_response(
            data=result,
            message=f"Bulk reject completed. {rejected_count} payments rejected.",
            meta={"rejected_count": rejected_count, "total": len(result) if isinstance(result, list) else 0},
        )
    except Exception as e:
        return _handle_endpoint_error(e, "bulk_reject_payments")


@frappe.whitelist()
def get_audit_logs(filters=None, limit_page_length=20, start=0, order_by="timestamp desc"):
    """
    Get audit logs (admin only).

    Admin endpoint — harus login sebagai admin/superadmin.

    Args:
        filters: JSON string filters (optional)
        limit_page_length: Jumlah baris per halaman (default: 20)
        start: Offset untuk pagination (default: 0)
        order_by: Ordering (default: timestamp desc)

    Returns:
        dict: Standard success response dengan audit logs
    """
    try:
        user = require_admin_role()
        rate_limit_check(user)

        from qalcuity.api.audit import get_audit_logs as _get_audit_logs

        result = _get_audit_logs(
            filters=filters,
            limit_page_length=limit_page_length,
            start=start,
            order_by=order_by,
        )
        return success_response(
            data=result.get("data", []),
            message="Audit logs retrieved successfully",
            meta={"total": result.get("total", 0)},
        )
    except Exception as e:
        return _handle_endpoint_error(e, "get_audit_logs")


@frappe.whitelist()
def get_all_subscription_history(limit_page_length=20, start=0):
    """
    Get subscription history for all subscriptions (admin only).

    Admin endpoint — harus login sebagai admin/superadmin.

    Args:
        limit_page_length: Jumlah baris per halaman (default: 20)
        start: Offset untuk pagination (default: 0)

    Returns:
        dict: Standard success response dengan subscription history
    """
    try:
        user = require_admin_role()
        rate_limit_check(user)

        from qalcuity.api.subscription_history import (
            get_my_subscription_history as _get_subscription_history,
        )

        # Admin uses get_my_subscription_history which already handles admin vs customer
        result = _get_subscription_history(
            limit_page_length=limit_page_length,
            start=start,
        )
        return success_response(
            data=result.get("data", []),
            message="Subscription history retrieved successfully",
            meta={"total": result.get("total", 0)},
        )
    except Exception as e:
        return _handle_endpoint_error(e, "get_all_subscription_history")


# =============================================================================
# SETTINGS ENDPOINTS
# =============================================================================

@frappe.whitelist(allow_guest=True)
def get_settings():
    """
    Get Qalcuity global settings.

    Public endpoint — bisa diakses tanpa login (untuk pricing page, dll).

    Returns:
        dict: Standard success response dengan settings data
    """
    try:
        from qalcuity.qalcuity.doctype.qalcuity_settings.qalcuity_settings import (
            get_settings as _get_settings,
        )

        result = _get_settings()
        return success_response(
            data=result,
            message="Settings retrieved successfully",
        )
    except Exception as e:
        return _handle_endpoint_error(e, "get_settings")


# =============================================================================
# USER INFO ENDPOINT
# =============================================================================

@frappe.whitelist()
def get_user_info():
    """
    Get current user information.

    Customer endpoint — harus login.

    Returns:
        dict: Standard success response dengan user info
    """
    try:
        user = require_authentication()
        rate_limit_check(user)

        result = get_current_user_info()
        return success_response(
            data=result,
            message="User info retrieved successfully",
        )
    except Exception as e:
        return _handle_endpoint_error(e, "get_user_info")
