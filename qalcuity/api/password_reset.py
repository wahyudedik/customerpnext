# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Password Reset API endpoints for Qalcuity ERP.
Provides whitelisted methods for forgot password / reset password flow.
"""

import frappe
from frappe import _
import re
import time
import hashlib
import hmac
from frappe.utils import get_url
from frappe.utils.password import update_password
from qalcuity.qalcuity.input_validation import validate_email, validate_password


# =============================================================================
# Constants
# =============================================================================

PASSWORD_RESET_TOKEN_TTL = 3600  # 1 hour in seconds
PASSWORD_RESET_RESEND_LIMIT = 3  # max requests per hour per email
PASSWORD_RESET_RESEND_WINDOW = 3600  # 1 hour in seconds


# =============================================================================
# Helpers
# =============================================================================

def _generate_reset_token(email):
    """
    Generate a secure password reset token using HMAC-SHA256.

    Args:
        email: User email address

    Returns:
        str: Token string in format "hex:timestamp"
    """
    secret = frappe.conf.get("secret_key", frappe.local.site)
    timestamp = str(int(time.time()))
    payload = "reset:{0}:{1}".format(email.lower(), timestamp)
    token = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "{0}:{1}".format(token, timestamp)


def _validate_reset_token(email, token_with_timestamp):
    """
    Validate a password reset token.

    Args:
        email: User email address
        token_with_timestamp: Token string in format "hex:timestamp"

    Returns:
        bool: True if token is valid and not expired
    """
    if ":" not in token_with_timestamp:
        return False

    parts = token_with_timestamp.rsplit(":", 1)
    if len(parts) != 2:
        return False

    token_hex, timestamp_str = parts

    try:
        timestamp = int(timestamp_str)
    except (ValueError, TypeError):
        return False

    # Check TTL
    current_time = int(time.time())
    if current_time - timestamp > PASSWORD_RESET_TOKEN_TTL:
        return False

    # Regenerate expected token and compare
    secret = frappe.conf.get("secret_key", frappe.local.site)
    payload = "reset:{0}:{1}".format(email.lower(), timestamp_str)
    expected = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(token_hex, expected)


def _get_stored_reset_token(email):
    """Get the stored reset token from cache."""
    cache_key = "qalcuity_password_reset_{0}".format(email.lower().replace("@", "_at_"))
    return frappe.cache().get_value(cache_key)


def _store_reset_token(email, token):
    """Store reset token in cache with TTL."""
    cache_key = "qalcuity_password_reset_{0}".format(email.lower().replace("@", "_at_"))
    frappe.cache().set_value(cache_key, token, expires_in_sec=PASSWORD_RESET_TOKEN_TTL)


def _invalidate_reset_token(email):
    """Remove stored reset token from cache."""
    cache_key = "qalcuity_password_reset_{0}".format(email.lower().replace("@", "_at_"))
    frappe.cache().delete_value(cache_key)


def _send_reset_email(email, full_name, token):
    """
    Send password reset email to user.

    Args:
        email: Recipient email
        full_name: User's full name
        token: Reset token (with timestamp)

    Returns:
        bool: True if email sent successfully
    """
    site_url = get_url()
    reset_url = "{0}/reset-password?token={1}&email={2}".format(
        site_url, token, email
    )

    subject = "Reset Password Anda - Qalcuity ERP"

    # Qalcuity-branded HTML email
    message = """
    <div style="max-width: 600px; margin: 0 auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <div style="background: #2490ef; padding: 32px; text-align: center; border-radius: 12px 12px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 24px;">Qalcuity ERP</h1>
        </div>
        <div style="background: #ffffff; padding: 32px; border: 1px solid #e2e8f0; border-top: none;">
            <h2 style="color: #333; margin: 0 0 16px 0; font-size: 20px;">Reset Password</h2>
            <p style="color: #555; line-height: 1.6; margin: 0 0 16px 0;">
                Halo <strong>{full_name}</strong>,
            </p>
            <p style="color: #555; line-height: 1.6; margin: 0 0 24px 0;">
                Kami menerima permintaan untuk mereset password akun Qalcuity ERP Anda.
                Klik tombol di bawah ini untuk membuat password baru:
            </p>
            <div style="text-align: center; margin: 0 0 24px 0;">
                <a href="{reset_url}"
                   style="display: inline-block; background: #2490ef; color: #ffffff; text-decoration: none;
                          padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                    Reset Password
                </a>
            </div>
            <p style="color: #888; font-size: 13px; line-height: 1.5; margin: 0 0 8px 0;">
                Jika tombol di atas tidak berfungsi, salin dan tempel link berikut ke browser Anda:
            </p>
            <p style="color: #2490ef; font-size: 13px; word-break: break-all; margin: 0 0 24px 0;">
                <a href="{reset_url}" style="color: #2490ef;">{reset_url}</a>
            </p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 0 0 16px 0;">
            <p style="color: #999; font-size: 12px; margin: 0;">
                Link reset password berlaku selama 1 jam. Jika Anda tidak meminta reset password,
                abaikan email ini. Password Anda tidak akan berubah.
            </p>
        </div>
        <div style="text-align: center; padding: 16px; color: #999; font-size: 12px;">
            &copy; 2026 Qalcuity ERP. All rights reserved.
        </div>
    </div>
    """.format(
        full_name=full_name or "User",
        reset_url=reset_url,
    )

    try:
        frappe.sendmail(
            recipients=[email],
            subject=subject,
            message=message,
            now=True,
        )
        return True
    except Exception as e:
        frappe.log_error(
            title="Qalcuity: Failed to send password reset email to {0}".format(email),
            message=str(e),
        )
        return False


# =============================================================================
# Rate Limiting
# =============================================================================

def _check_resend_rate_limit(email):
    """
    Rate limiting untuk password reset requests.

    Args:
        email: Email address to check rate limit for

    Returns:
        bool: True if request is allowed

    Raises:
        frappe.TooManyRequestsError: If rate limit exceeded
    """
    current_time = int(time.time())
    window_start = current_time - PASSWORD_RESET_RESEND_WINDOW

    cache_key = "qalcuity_reset_rate_{0}".format(email.lower().replace("@", "_at_"))

    request_log = frappe.cache().get_value(cache_key)
    if request_log is None:
        request_log = []

    request_log = [ts for ts in request_log if ts > window_start]

    if len(request_log) >= PASSWORD_RESET_RESEND_LIMIT:
        retry_after = request_log[0] - window_start + 1
        frappe.throw(
            _(
                "Terlalu banyak permintaan reset password. "
                "Maksimal {0} permintaan per jam. Coba lagi dalam {1} detik."
            ).format(PASSWORD_RESET_RESEND_LIMIT, retry_after),
            frappe.TooManyRequestsError,
        )

    request_log.append(current_time)
    frappe.cache().set_value(cache_key, request_log, expires_in_sec=PASSWORD_RESET_RESEND_WINDOW + 60)

    return True


# =============================================================================
# API Endpoints
# =============================================================================

@frappe.whitelist(allow_guest=True)
def request_password_reset(email):
    """
    Request a password reset link.

    Generates a reset token and sends email with reset link.
    Rate limited to max 3 requests per hour per email.

    Args:
        email: User email address

    Returns:
        dict: Success message (always returns success to prevent email enumeration)
    """
    email = (email or "").strip().lower()

    if not email:
        frappe.throw(_("Email wajib diisi."))

    # Validate email format (using centralized validation)
    if not validate_email(email):
        frappe.throw(_("Format email tidak valid."))

    # Always return success message to prevent email enumeration
    success_msg = _(
        "Jika email {0} terdaftar, link reset password telah dikirim. "
        "Silakan cek inbox atau spam folder Anda."
    ).format(email)

    # Check if user exists
    user_name = frappe.db.get_value("User", {"email": email}, "name")
    if not user_name:
        # Return success even if user not found (prevent email enumeration)
        return {
            "success": True,
            "message": success_msg,
        }

    # Check if user is disabled
    user_doc = frappe.get_doc("User", user_name)
    if user_doc.disabled:
        return {
            "success": True,
            "message": success_msg,
        }

    # Rate limiting
    _check_resend_rate_limit(email)

    # Generate token and send email
    token = _generate_reset_token(email)
    _store_reset_token(email, token)
    _send_reset_email(email, user_doc.full_name or email, token)

    return {
        "success": True,
        "message": success_msg,
    }


@frappe.whitelist(allow_guest=True)
def reset_password(token, email, new_password):
    """
    Reset user password using the reset token.

    Validates token, sets new password, and invalidates the token.

    Args:
        token: Reset token (with timestamp)
        email: User email address
        new_password: New password

    Returns:
        dict: Success message
    """
    email = (email or "").strip().lower()
    token = (token or "").strip()
    new_password = new_password or ""

    if not email or not token:
        frappe.throw(_("Token reset password tidak valid."))

    if not new_password:
        frappe.throw(_("Password baru tidak boleh kosong."))

    # Validate password strength (using centralized validation)
    is_valid_pwd, pwd_error = validate_password(new_password)
    if not is_valid_pwd:
        frappe.throw(_(pwd_error))

    # Check if user exists
    user_name = frappe.db.get_value("User", {"email": email}, "name")
    if not user_name:
        frappe.throw(_("User dengan email {0} tidak ditemukan.").format(email))

    # Validate token
    if not _validate_reset_token(email, token):
        frappe.throw(
            _(
                "Token reset password tidak valid atau sudah kedaluwarsa. "
                "Silakan minta link reset password baru."
            )
        )

    # Set new password
    update_password(user_name, new_password)

    # Invalidate token
    _invalidate_reset_token(email)

    frappe.db.commit()

    return {
        "success": True,
        "message": _(
            "Password berhasil diubah! Silakan login dengan password baru Anda."
        ),
    }
