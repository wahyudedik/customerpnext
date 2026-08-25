# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity API v1 — Standard Response Format
============================================

Menyediakan response format yang konsisten untuk semua API v1 endpoints.

Format:
    Success: {"success": true, "message": "...", "data": {...}, "meta": {...}}
    Error:   {"success": false, "message": "...", "code": "...", "details": "..."}
"""


def success_response(data=None, message="Success", meta=None):
    """
    Standard success response.

    Args:
        data: Response data (dict, list, or any serializable object)
        message: Human-readable success message
        meta: Optional metadata (pagination info, counts, etc.)

    Returns:
        dict: Standardized success response

    Examples:
        >>> success_response({"name": "PAY-001"}, "Payment submitted")
        {"success": true, "message": "Payment submitted", "data": {"name": "PAY-001"}}

        >>> success_response(data_list, meta={"page": 1, "total": 50})
        {"success": true, "message": "Success", "data": [...], "meta": {"page": 1, "total": 50}}
    """
    response = {
        "success": True,
        "message": message,
        "data": data,
    }
    if meta:
        response["meta"] = meta
    return response


def error_response(message="An error occurred", code=None, details=None, http_status=None):
    """
    Standard error response.

    Args:
        message: Human-readable error message
        code: Machine-readable error code (e.g., "VALIDATION_ERROR", "NOT_FOUND")
        details: Additional error details (exception message, field errors, etc.)
        http_status: HTTP status code for reference (not included in response body)

    Returns:
        dict: Standardized error response

    Examples:
        >>> error_response("Payment not found", "NOT_FOUND")
        {"success": false, "message": "Payment not found", "code": "NOT_FOUND"}

        >>> error_response("Invalid input", "VALIDATION_ERROR", details="Amount must be > 0")
        {"success": false, "message": "Invalid input", "code": "VALIDATION_ERROR", "details": "Amount must be > 0"}
    """
    response = {
        "success": False,
        "message": message,
    }
    if code:
        response["code"] = code
    if details:
        response["details"] = details
    if http_status:
        response["http_status"] = http_status
    return response


# =============================================================================
# Error Code Constants
# =============================================================================

class ErrorCode:
    """Standard error codes for API v1."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    RATE_LIMITED = "RATE_LIMITED"
    SERVER_ERROR = "SERVER_ERROR"
    PAYMENT_NOT_FOUND = "PAYMENT_NOT_FOUND"
    SUBSCRIPTION_NOT_FOUND = "SUBSCRIPTION_NOT_FOUND"
    PLAN_NOT_FOUND = "PLAN_NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    INVALID_INPUT = "INVALID_INPUT"
    ACTION_NOT_ALLOWED = "ACTION_NOT_ALLOWED"
