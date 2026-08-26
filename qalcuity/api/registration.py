# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Registration API endpoints for Qalcuity ERP.
Provides whitelisted methods for customer registration with email verification.
"""

import frappe
from frappe import _
import re
import time
import hashlib
import hmac
from frappe.utils import now_datetime, add_to_date, get_url
from qalcuity.input_validation import (
    sanitize_text, validate_email, validate_password, validate_phone,
    validate_name, sanitize_html
)


# =============================================================================
# Constants
# =============================================================================

REGISTRATION_RATE_LIMIT = 5  # max registrations per hour per IP
REGISTRATION_RATE_WINDOW = 3600  # 1 hour in seconds
VERIFICATION_TOKEN_TTL = 86400  # 24 hours in seconds
VERIFICATION_RESEND_LIMIT = 3  # max resends per hour per email
VERIFICATION_RESEND_WINDOW = 3600  # 1 hour in seconds


# =============================================================================
# Helpers
# =============================================================================

def _get_client_ip():
    """
    Get client IP address from request headers or fallback to remote_addr.

    Returns:
        str: Client IP address
    """
    forwarded_for = frappe.get_request_header("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = frappe.get_request_header("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return frappe.request.remote_addr or "unknown"


def _get_site_url():
    """Get the base URL for the site."""
    return get_url()


def _generate_verification_token(email):
    """
    Generate a secure verification token using HMAC-SHA256.

    Args:
        email: User email address

    Returns:
        str: Hex token string
    """
    secret = frappe.conf.get("secret_key", frappe.local.site)
    timestamp = str(int(time.time()))
    payload = "{0}:{1}".format(email.lower(), timestamp)
    token = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    # Store as token:timestamp so we can validate TTL
    return "{0}:{1}".format(token, timestamp)


def _validate_verification_token(email, token_with_timestamp):
    """
    Validate a verification token.

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
    if current_time - timestamp > VERIFICATION_TOKEN_TTL:
        return False

    # Regenerate expected token and compare
    secret = frappe.conf.get("secret_key", frappe.local.site)
    payload = "{0}:{1}".format(email.lower(), timestamp_str)
    expected = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(token_hex, expected)


def _get_stored_verification_token(email):
    """Get the stored verification token from cache."""
    cache_key = "qalcuity_email_verify_{0}".format(email.lower().replace("@", "_at_"))
    return frappe.cache().get_value(cache_key)


def _store_verification_token(email, token):
    """Store verification token in cache with TTL."""
    cache_key = "qalcuity_email_verify_{0}".format(email.lower().replace("@", "_at_"))
    frappe.cache().set_value(cache_key, token, expires_in_sec=VERIFICATION_TOKEN_TTL)


def _invalidate_verification_token(email):
    """Remove stored verification token from cache."""
    cache_key = "qalcuity_email_verify_{0}".format(email.lower().replace("@", "_at_"))
    frappe.cache().delete_value(cache_key)


def _send_verification_email(email, full_name, token):
    """
    Send email verification link to user.

    Args:
        email: Recipient email
        full_name: User's full name
        token: Verification token (with timestamp)

    Returns:
        bool: True if email sent successfully
    """
    site_url = _get_site_url()
    verify_url = "{0}/verify-email?token={1}&email={2}".format(
        site_url, token, email
    )

    subject = "Verifikasi Email Anda - Qalcuity ERP"

    # Qalcuity-branded HTML email
    message = """
    <div style="max-width: 600px; margin: 0 auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <div style="background: #2490ef; padding: 32px; text-align: center; border-radius: 12px 12px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 24px;">Qalcuity ERP</h1>
        </div>
        <div style="background: #ffffff; padding: 32px; border: 1px solid #e2e8f0; border-top: none;">
            <h2 style="color: #333; margin: 0 0 16px 0; font-size: 20px;">Verifikasi Email Anda</h2>
            <p style="color: #555; line-height: 1.6; margin: 0 0 16px 0;">
                Halo <strong>{full_name}</strong>,
            </p>
            <p style="color: #555; line-height: 1.6; margin: 0 0 24px 0;">
                Terima kasih telah mendaftar di Qalcuity ERP. Untuk mengaktifkan akun Anda,
                silakan klik tombol di bawah ini untuk memverifikasi alamat email Anda:
            </p>
            <div style="text-align: center; margin: 0 0 24px 0;">
                <a href="{verify_url}"
                   style="display: inline-block; background: #2490ef; color: #ffffff; text-decoration: none;
                          padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                    Verifikasi Email
                </a>
            </div>
            <p style="color: #888; font-size: 13px; line-height: 1.5; margin: 0 0 8px 0;">
                Jika tombol di atas tidak berfungsi, salin dan tempel link berikut ke browser Anda:
            </p>
            <p style="color: #2490ef; font-size: 13px; word-break: break-all; margin: 0 0 24px 0;">
                <a href="{verify_url}" style="color: #2490ef;">{verify_url}</a>
            </p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 0 0 16px 0;">
            <p style="color: #999; font-size: 12px; margin: 0;">
                Link verifikasi berlaku selama 24 jam. Jika Anda tidak mendaftar di Qalcuity ERP,
                abaikan email ini.
            </p>
        </div>
        <div style="text-align: center; padding: 16px; color: #999; font-size: 12px;">
            &copy; 2026 Qalcuity ERP. All rights reserved.
        </div>
    </div>
    """.format(
        full_name=full_name or "User",
        verify_url=verify_url,
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
            title="Qalcuity: Failed to send verification email to {0}".format(email),
            message=str(e),
        )
        return False


# =============================================================================
# Rate Limiting
# =============================================================================

def _check_registration_rate_limit():
    """
    Rate limiting untuk registration endpoint menggunakan frappe.cache().

    Returns:
        bool: True if request is allowed

    Raises:
        frappe.TooManyRequestsError: If rate limit exceeded
    """
    client_ip = _get_client_ip()
    current_time = int(time.time())
    window_start = current_time - REGISTRATION_RATE_WINDOW

    cache_key = "qalcuity_registration_rate_{0}".format(client_ip)

    # Get current request log from cache
    request_log = frappe.cache().get_value(cache_key)
    if request_log is None:
        request_log = []

    # Filter out expired entries (outside the window)
    request_log = [ts for ts in request_log if ts > window_start]

    # Check if limit exceeded
    if len(request_log) >= REGISTRATION_RATE_LIMIT:
        retry_after = request_log[0] - window_start + 1
        frappe.throw(
            _(
                "Terlalu banyak percobaan registrasi dari IP ini. "
                "Maksimal {0} registrasi per jam. Coba lagi dalam {1} detik."
            ).format(REGISTRATION_RATE_LIMIT, retry_after),
            frappe.TooManyRequestsError,
        )

    # Add current request
    request_log.append(current_time)

    # Save updated log with TTL slightly longer than window
    frappe.cache().set_value(cache_key, request_log, expires_in_sec=REGISTRATION_RATE_WINDOW + 60)

    return True


def _check_resend_rate_limit(email):
    """
    Rate limiting untuk resend verification email.

    Args:
        email: Email address to check rate limit for

    Returns:
        bool: True if request is allowed

    Raises:
        frappe.TooManyRequestsError: If rate limit exceeded
    """
    current_time = int(time.time())
    window_start = current_time - VERIFICATION_RESEND_WINDOW

    cache_key = "qalcuity_verify_resend_{0}".format(email.lower().replace("@", "_at_"))

    request_log = frappe.cache().get_value(cache_key)
    if request_log is None:
        request_log = []

    request_log = [ts for ts in request_log if ts > window_start]

    if len(request_log) >= VERIFICATION_RESEND_LIMIT:
        retry_after = request_log[0] - window_start + 1
        frappe.throw(
            _(
                "Terlalu banyak permintaan verifikasi ulang. "
                "Maksimal {0} permintaan per jam. Coba lagi dalam {1} detik."
            ).format(VERIFICATION_RESEND_LIMIT, retry_after),
            frappe.TooManyRequestsError,
        )

    request_log.append(current_time)
    frappe.cache().set_value(cache_key, request_log, expires_in_sec=VERIFICATION_RESEND_WINDOW + 60)

    return True


# =============================================================================
# Registration
# =============================================================================

@frappe.whitelist(allow_guest=True)
def register_customer(full_name, email, password, company_name, phone):
    """
    Register a new customer with email verification.

    Creates: User (disabled) → Customer → Portal User → Tenant (via hook)
    Then sends verification email.

    Args:
        full_name: Nama lengkap customer
        email: Email address (unique)
        password: Password (min 8 chars, kombinasi huruf+angka)
        company_name: Nama perusahaan
        phone: Nomor telepon

    Returns:
        dict: Success message with instructions to check email
    """
    # ── 0. Rate limiting ───────────────────────────────────────────────
    _check_registration_rate_limit()

    # ── 1. Validasi & sanitasi input ──────────────────────────────────
    full_name = sanitize_text(full_name, max_length=100)
    full_name = sanitize_html(full_name) if full_name else full_name
    email = (email or "").strip().lower()
    password = password or ""
    company_name = sanitize_text(company_name, max_length=200)
    phone = (phone or "").strip()

    if not full_name:
        frappe.throw(_("Nama lengkap wajib diisi."))

    is_valid_name, name_error = validate_name(full_name)
    if not is_valid_name:
        frappe.throw(_(name_error))

    if not email:
        frappe.throw(_("Email wajib diisi."))

    if not password:
        frappe.throw(_("Password wajib diisi."))

    if not company_name:
        frappe.throw(_("Nama perusahaan wajib diisi."))

    if not phone:
        frappe.throw(_("Nomor telepon wajib diisi."))

    # ── 2. Validasi email format ───────────────────────────────────────
    if not validate_email(email):
        frappe.throw(_("Format email tidak valid."))

    # ── 3. Cek email belum terdaftar ───────────────────────────────────
    if frappe.db.exists("User", {"email": email}):
        frappe.throw(
            _("Email {0} sudah terdaftar. Silakan gunakan email lain atau login.").format(
                email
            )
        )

    # ── 4. Validasi password strength ──────────────────────────────────
    is_valid_pwd, pwd_error = validate_password(password)
    if not is_valid_pwd:
        frappe.throw(_(pwd_error))

    # ── 5. Validasi phone format ───────────────────────────────────────
    if not validate_phone(phone):
        frappe.throw(
            _(
                "Format nomor telepon tidak valid. Gunakan format: +62xxxxxxxxxx atau 08xxxxxxxxxx"
            )
        )

    try:
        # ── 6. Buat User (DISABLED — menunggu verifikasi) ─────────────
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": full_name,
                "full_name": full_name,
                "password": password,
                "user_type": "Website User",
                "send_welcome_email": 0,
                "disabled": 1,  # Disabled sampai terverifikasi
            }
        )
        user.append("roles", {"role": "Customer"})
        user.insert(ignore_permissions=True)

        # ── 7. Buat Customer (ERPNext) ────────────────────────────────
        customer = frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": company_name,
                "customer_group": frappe.db.get_single_value(
                    "Selling Settings", "customer_group"
                )
                or "All Customer Groups",
                "territory": frappe.db.get_single_value(
                    "Selling Settings", "territory"
                )
                or "All Territories",
                "customer_type": "Company",
                "customer_details": company_name,
            }
        )
        customer.insert(ignore_permissions=True)

        # ── 8. Buat Portal User (link User ↔ Customer) ────────────────
        portal_user = frappe.get_doc(
            {
                "doctype": "Portal User",
                "user": email,
                "parenttype": "Customer",
                "parent": customer.name,
                "parentfield": "portal_users",
            }
        )
        portal_user.insert(ignore_permissions=True)

        # ── 9. Buat Qalcuity Tenant (via hook after_customer_insert) ───
        if not frappe.db.exists("Qalcuity Tenant", {"customer": customer.name}):
            try:
                tenant = frappe.get_doc(
                    {
                        "doctype": "Qalcuity Tenant",
                        "customer": customer.name,
                        "status": "Active",
                    }
                )
                tenant.insert(ignore_permissions=True)
            except Exception:
                frappe.log_error(
                    title="Qalcuity: Failed to provision tenant for {0}".format(
                        customer.name
                    )
                )

        frappe.db.commit()

        # ── 10. Generate verification token & send email ───────────────
        token = _generate_verification_token(email)
        _store_verification_token(email, token)
        _send_verification_email(email, full_name, token)

        return {
            "success": True,
            "message": _(
                "Registrasi berhasil! Silakan cek email Anda ({0}) "
                "untuk verifikasi akun. Link verifikasi berlaku selama 24 jam."
            ).format(email),
            "email": email,
            "requires_verification": True,
        }

    except frappe.DuplicateEntryError:
        frappe.throw(
            _(
                "Email {0} sudah terdaftar. Silakan gunakan email lain atau login."
            ).format(email)
        )
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            title="Qalcuity: Registration failed for {0}".format(email)
        )
        frappe.throw(
            _("Terjadi kesalahan saat registrasi. Silakan coba lagi atau hubungi admin.")
        )


# =============================================================================
# Email Verification
# =============================================================================

@frappe.whitelist(allow_guest=True)
def verify_email(token, email):
    """
    Verify user email address using the verification token.

    Activates the user account if token is valid.

    Args:
        token: Verification token (with timestamp)
        email: User email address

    Returns:
        dict: Success or error message
    """
    email = (email or "").strip().lower()
    token = (token or "").strip()

    if not email or not token:
        frappe.throw(_("Token verifikasi tidak valid."))

    # Check if user exists
    user_name = frappe.db.get_value("User", {"email": email}, "name")
    if not user_name:
        frappe.throw(_("User dengan email {0} tidak ditemukan.").format(email))

    # Check if already verified (user is active)
    user_doc = frappe.get_doc("User", user_name)
    if not user_doc.disabled:
        return {
            "success": True,
            "message": _("Email Anda sudah terverifikasi. Silakan login."),
            "already_verified": True,
        }

    # Validate token
    if not _validate_verification_token(email, token):
        frappe.throw(
            _(
                "Token verifikasi tidak valid atau sudah kedaluwarsa. "
                "Silakan minta link verifikasi ulang."
            )
        )

    # Activate user
    user_doc.disabled = 0
    user_doc.save(ignore_permissions=True)

    # Invalidate token
    _invalidate_verification_token(email)

    frappe.db.commit()

    return {
        "success": True,
        "message": _(
            "Email berhasil diverifikasi! Akun Anda sekarang aktif. "
            "Silakan login untuk mulai menggunakan Qalcuity ERP."
        ),
    }


@frappe.whitelist(allow_guest=True)
def resend_verification_email(email):
    """
    Resend verification email to user.

    Rate limited to max 3 resends per hour per email.

    Args:
        email: User email address

    Returns:
        dict: Success message
    """
    email = (email or "").strip().lower()

    if not email:
        frappe.throw(_("Email wajib diisi."))

    # Validate email format (using centralized validation)
    if not validate_email(email):
        frappe.throw(_("Format email tidak valid."))

    # Check if user exists
    user_name = frappe.db.get_value("User", {"email": email}, "name")
    if not user_name:
        # Return success even if user not found (prevent email enumeration)
        return {
            "success": True,
            "message": _(
                "Jika email {0} terdaftar, link verifikasi telah dikirim."
            ).format(email),
        }

    # Check if already verified
    user_doc = frappe.get_doc("User", user_name)
    if not user_doc.disabled:
        return {
            "success": True,
            "message": _("Email Anda sudah terverifikasi. Silakan login."),
            "already_verified": True,
        }

    # Rate limiting
    _check_resend_rate_limit(email)

    # Generate new token and send
    token = _generate_verification_token(email)
    _store_verification_token(email, token)
    _send_verification_email(email, user_doc.full_name or email, token)

    return {
        "success": True,
        "message": _(
            "Link verifikasi baru telah dikirim ke {0}. "
            "Silakan cek inbox atau spam folder Anda."
        ).format(email),
    }
