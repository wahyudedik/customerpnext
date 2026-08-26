# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Two-Factor Authentication (2FA) API for Qalcuity ERP.
Implements TOTP-based 2FA using Python hmac + hashlib (no external dependencies).

Flow:
  1. User enables 2FA from profile → /2fa-setup page
  2. Backend generates TOTP secret + QR code URL
  3. User verifies with authenticator app → 2FA activated
  4. On login, if 2FA enabled → redirect to /2fa-verify
  5. User enters 6-digit code → session created
"""

import frappe
from frappe import _
import hmac
import hashlib
import struct
import time
import base64
import os
import json
import re


# =============================================================================
# TOTP Implementation (RFC 6238) using hmac + hashlib only
# =============================================================================

def _generate_secret(length=20):
    """Generate a random secret for TOTP.

    Args:
        length: Number of random bytes (default 20 = 160 bits)

    Returns:
        str: Base32-encoded secret
    """
    random_bytes = os.urandom(length)
    return base64.b32encode(random_bytes).decode("utf-8").rstrip("=")


def _secret_to_bytes(secret):
    """Convert base32 secret to bytes.

    Args:
        secret: Base32-encoded string

    Returns:
        bytes: Decoded secret bytes
    """
    # Add padding if needed
    padding = 8 - (len(secret) % 8) if len(secret) % 8 != 0 else 0
    secret_padded = secret + "=" * padding
    return base64.b32decode(secret_padded, casefold=True)


def _generate_hotp(secret_bytes, counter):
    """Generate HMAC-based One-Time Password (HOTP) code.

    Implements RFC 4226 with HMAC-SHA1 and 6-digit output.

    Args:
        secret_bytes: Secret as bytes
        counter: 8-byte counter value (big-endian)

    Returns:
        str: 6-digit HOTP code
    """
    # Convert counter to 8-byte big-endian
    counter_bytes = struct.pack(">Q", counter)

    # Compute HMAC-SHA1
    hmac_hash = hmac.new(secret_bytes, counter_bytes, hashlib.sha1).digest()

    # Dynamic truncation (RFC 4226 Section 5.4)
    offset = hmac_hash[-1] & 0x0F
    truncated = struct.unpack(
        ">I", hmac_hash[offset : offset + 4]
    )[0]
    truncated = truncated & 0x7FFFFFFF

    # Generate 6-digit code
    code = truncated % 1000000
    return str(code).zfill(6)


def _generate_totp(secret, time_step=None, time_period=30):
    """Generate Time-based One-Time Password (TOTP) code.

    Implements RFC 6238 using HMAC-SHA1.

    Args:
        secret: Base32-encoded secret
        time_step: Unix timestamp (default: current time)
        time_period: Time step in seconds (default: 30)

    Returns:
        str: 6-digit TOTP code
    """
    if time_step is None:
        time_step = int(time.time())

    # Calculate time counter
    counter = time_step // time_period

    # Convert secret to bytes
    secret_bytes = _secret_to_bytes(secret)

    return _generate_hotp(secret_bytes, counter)


def _verify_totp(secret, code, time_period=30, tolerance=1):
    """Verify a TOTP code with tolerance window.

    Args:
        secret: Base32-encoded secret
        code: 6-digit code to verify
        time_period: Time step in seconds (default: 30)
        tolerance: Number of time steps to check each side (default: 1 = ±30s)

    Returns:
        bool: True if code is valid
    """
    if not code or not isinstance(code, str):
        return False

    # Normalize code
    code = code.strip()
    if not re.match(r"^\d{6}$", code):
        return False

    current_step = int(time.time())

    for i in range(-tolerance, tolerance + 1):
        expected = _generate_totp(
            secret, current_step + (i * time_period), time_period
        )
        if hmac.compare_digest(expected, code):
            return True

    return False


# =============================================================================
# Backup Codes
# =============================================================================

def _generate_backup_codes(count=8):
    """Generate backup codes for 2FA recovery.

    Each code is 8 characters (4 groups of 2 alphanumeric).

    Args:
        count: Number of backup codes to generate (default: 8)

    Returns:
        list: List of plain-text backup codes
    """
    codes = []
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # Exclude confusing chars (0,O,1,I)
    for _ in range(count):
        code = ""
        for group in range(4):
            if group > 0:
                code += "-"
            code += "".join(chars[i] for i in [
                int.from_bytes(os.urandom(1), "big") % len(chars)
                for _ in range(2)
            ])
        codes.append(code)
    return codes


def _hash_backup_code(code):
    """Hash a backup code using SHA-256.

    Args:
        code: Plain-text backup code

    Returns:
        str: Hex-encoded SHA-256 hash
    """
    normalized = code.strip().upper().replace("-", "")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _get_backup_codes_file(user):
    """Get the file path for storing backup codes.

    Args:
        user: User email/name

    Returns:
        str: File path in site private files
    """
    user_hash = hashlib.md5(user.encode("utf-8")).hexdigest()[:12]
    site_path = frappe.get_site_path("private", "files")
    return os.path.join(site_path, f"2fa_backup_{user_hash}.json")


def _save_backup_codes(user, codes_plain, codes_hashed):
    """Save backup codes to file.

    Args:
        user: User email/name
        codes_plain: List of plain-text codes (for display)
        codes_hashed: List of hashed codes (for storage)
    """
    filepath = _get_backup_codes_file(user)
    data = {
        "user": user,
        "codes": codes_hashed,
        "created": int(time.time()),
    }

    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w") as f:
        json.dump(data, f)


def _load_backup_codes_data(user):
    """Load backup codes data from file.

    Args:
        user: User email/name

    Returns:
        dict: Backup codes data, or empty dict if not found
    """
    filepath = _get_backup_codes_file(user)
    if not os.path.exists(filepath):
        return {}

    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_backup_codes_data(user, data):
    """Save backup codes data to file.

    Args:
        user: User email/name
        data: Data to save
    """
    filepath = _get_backup_codes_file(user)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f)


def _verify_backup_code(user, code):
    """Verify a backup code and mark it as used.

    Args:
        user: User email/name
        code: Backup code to verify

    Returns:
        bool: True if backup code is valid and was not already used
    """
    data = _load_backup_codes_data(user)
    if not data or "codes" not in data:
        return False

    code_hashed = _hash_backup_code(code)

    if code_hashed in data["codes"]:
        # Remove the used code
        data["codes"].remove(code_hashed)
        _save_backup_codes_data(user, data)
        return True

    return False


def _clear_backup_codes(user):
    """Clear all backup codes for a user.

    Args:
        user: User email/name
    """
    filepath = _get_backup_codes_file(user)
    if os.path.exists(filepath):
        os.remove(filepath)


# =============================================================================
# QR Code URL Generation
# =============================================================================

def _get_otpauth_uri(secret, user_email, issuer="Qalcuity ERP"):
    """Generate otpauth:// URI for authenticator apps.

    Args:
        secret: Base32-encoded secret
        user_email: User's email address
        issuer: Issuer name

    Returns:
        str: otpauth:// URI
    """
    import urllib.parse
    encoded_issuer = urllib.parse.quote(issuer)
    encoded_user = urllib.parse.quote(user_email)
    return f"otpauth://totp/{encoded_issuer}:{encoded_user}?secret={secret}&issuer={encoded_issuer}&algorithm=SHA1&digits=6&period=30"


def _get_qr_code_url(uri):
    """Generate QR code image URL using Google Charts API.

    Args:
        uri: otpauth:// URI

    Returns:
        str: Google Charts QR code URL
    """
    import urllib.parse
    encoded = urllib.parse.quote(uri)
    return f"https://chart.googleapis.com/cht=qr&chs=250x250&choe=UTF-8&chl={encoded}"


# =============================================================================
# API: 2FA Status
# =============================================================================

@frappe.whitelist()
def get_2fa_status():
    """Get 2FA status for the currently logged-in user.

    Returns:
        dict: 2FA status information
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Silakan login untuk mengakses pengaturan 2FA."))

    user_doc = frappe.get_doc("User", user)
    secret = user_doc.get("secret")
    two_factor_enabled = user_doc.get("two_factor_enabled")

    has_secret = bool(secret)
    is_enabled = bool(two_factor_enabled)

    # Check if 2FA is allowed globally
    settings = frappe.get_single("Qalcuity Settings")
    global_enabled = bool(settings.get("enable_2fa"))

    # Count remaining backup codes
    backup_data = _load_backup_codes_data(user)
    remaining_backups = len(backup_data.get("codes", []))

    return {
        "enabled": is_enabled,
        "has_secret": has_secret,
        "global_allowed": global_enabled,
        "backup_codes_remaining": remaining_backups,
    }


# =============================================================================
# API: Setup 2FA (generate secret + QR)
# =============================================================================

@frappe.whitelist()
def setup_2fa():
    """Start 2FA setup — generate secret and QR code URL.

    Returns:
        dict: Secret, QR code URL, and manual entry key
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Silakan login untuk mengatur 2FA."))

    # Check if 2FA is allowed globally
    settings = frappe.get_single("Qalcuity Settings")
    if not settings.get("enable_2fa"):
        frappe.throw(_("Two-Factor Authentication belum diaktifkan oleh administrator."))

    # Check if already enabled
    user_doc = frappe.get_doc("User", user)
    if user_doc.get("two_factor_enabled"):
        frappe.throw(_("2FA sudah diaktifkan untuk akun ini."))

    # Generate new secret
    secret = _generate_secret()

    # Store secret temporarily in cache (pending verification)
    frappe.cache().set_value(
        f"qalcuity_2fa_setup:{user}",
        {"secret": secret},
        expires_in=300,  # 5 minutes
    )

    # Generate QR code URL
    otp_uri = _get_otpauth_uri(secret, user)
    qr_url = _get_qr_code_url(otp_uri)

    # Format secret for manual entry (groups of 4)
    formatted_secret = "-".join(
        [secret[i : i + 4] for i in range(0, len(secret), 4)]
    )

    return {
        "secret": secret,
        "secret_formatted": formatted_secret,
        "qr_url": qr_url,
        "otp_uri": otp_uri,
    }


# =============================================================================
# API: Enable 2FA (verify code + activate)
# =============================================================================

@frappe.whitelist()
def enable_2fa(code):
    """Enable 2FA after verifying the TOTP code.

    Args:
        code: 6-digit TOTP code from authenticator app

    Returns:
        dict: Backup codes for the user to save
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Silakan login untuk mengaktifkan 2FA."))

    # Get pending secret from cache
    pending = frappe.cache().get_value(f"qalcuity_2fa_setup:{user}")
    if not pending or not pending.get("secret"):
        frappe.throw(_("Sesi pengaturan 2FA telah kedaluwarsa. Silakan mulai ulang."))

    secret = pending["secret"]

    # Verify the code
    if not _verify_totp(secret, code):
        frappe.throw(_("Kode verifikasi tidak valid. Pastikan waktu di perangkat Anda sudah benar."))

    # Save secret to User document
    frappe.db.set_value("User", user, "secret", secret)
    frappe.db.set_value("User", user, "two_factor_enabled", 1)
    frappe.db.commit()

    # Clear pending setup from cache
    frappe.cache().delete_value(f"qalcuity_2fa_setup:{user}")

    # Generate backup codes
    codes_plain = _generate_backup_codes(8)
    codes_hashed = [_hash_backup_code(c) for c in codes_plain]
    _save_backup_codes(user, codes_plain, codes_hashed)

    # Log audit
    _create_audit_log(user, "2FA Enabled", f"User {user} enabled Two-Factor Authentication")

    return {
        "success": True,
        "message": _("2FA berhasil diaktifkan."),
        "backup_codes": codes_plain,
    }


# =============================================================================
# API: Disable 2FA
# =============================================================================

@frappe.whitelist()
def disable_2fa(password):
    """Disable 2FA after password confirmation.

    Args:
        password: Current password for verification

    Returns:
        dict: Success status
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Silakan login untuk menonaktifkan 2FA."))

    if not password:
        frappe.throw(_("Password harus diisi untuk menonaktifkan 2FA."))

    # Verify password
    from frappe.utils.password import check_password
    try:
        check_password(user, password)
    except frappe.AuthenticationError:
        frappe.throw(_("Password tidak sesuai."))

    # Check if 2FA is actually enabled
    user_doc = frappe.get_doc("User", user)
    if not user_doc.get("two_factor_enabled"):
        frappe.throw(_("2FA belum diaktifkan untuk akun ini."))

    # Disable 2FA
    frappe.db.set_value("User", user, "two_factor_enabled", 0)
    frappe.db.set_value("User", user, "secret", "")
    frappe.db.commit()

    # Clear backup codes
    _clear_backup_codes(user)

    # Clear any pending 2FA cache
    frappe.cache().delete_value(f"qalcuity_2fa_setup:{user}")
    frappe.cache().delete_value(f"qalcuity_2fa_pending:{user}")

    # Log audit
    _create_audit_log(user, "2FA Disabled", f"User {user} disabled Two-Factor Authentication")

    return {
        "success": True,
        "message": _("2FA berhasil dinonaktifkan."),
    }


# =============================================================================
# API: Regenerate Backup Codes
# =============================================================================

@frappe.whitelist()
def regenerate_backup_codes(password):
    """Regenerate backup codes after password confirmation.

    Args:
        password: Current password for verification

    Returns:
        dict: New backup codes
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Silakan login untuk memperbarui backup codes."))

    if not password:
        frappe.throw(_("Password harus diisi."))

    # Verify password
    from frappe.utils.password import check_password
    try:
        check_password(user, password)
    except frappe.AuthenticationError:
        frappe.throw(_("Password tidak sesuai."))

    # Check if 2FA is enabled
    user_doc = frappe.get_doc("User", user)
    if not user_doc.get("two_factor_enabled"):
        frappe.throw(_("2FA belum diaktifkan."))

    # Generate new backup codes
    codes_plain = _generate_backup_codes(8)
    codes_hashed = [_hash_backup_code(c) for c in codes_plain]
    _save_backup_codes(user, codes_plain, codes_hashed)

    return {
        "success": True,
        "message": _("Backup codes berhasil diperbarui."),
        "backup_codes": codes_plain,
    }


# =============================================================================
# Login Flow: Pre-login check (validate password + check 2FA)
# =============================================================================

@frappe.whitelist(allow_guest=True)
def pre_login_check(user, password):
    """Validate password and check if 2FA is required.

    Called by the login page JavaScript before standard login.
    If 2FA is needed, returns a temporary token for the verification flow.

    Args:
        user: Username/email
        password: Password

    Returns:
        dict: Login status and next action
    """
    if not user or not password:
        frappe.throw(_("Email dan password harus diisi."))

    # Resolve user
    user_email = user
    if not frappe.db.exists("User", user_email):
        # Try matching by email
        user_email = frappe.db.get_value("User", {"email": user}, "name")
        if not user_email:
            frappe.throw(_("Akun tidak ditemukan."))

    # Check if user is enabled
    user_doc = frappe.get_doc("User", user_email)
    if user_doc.disabled:
        frappe.throw(_("Akun telah dinonaktifkan. Silakan hubungi administrator."))

    # Validate password
    from frappe.utils.password import check_password
    try:
        check_password(user_email, password)
    except frappe.AuthenticationError:
        frappe.throw(_("Password tidak sesuai."))

    # Check if 2FA is enabled
    if user_doc.get("two_factor_enabled"):
        # Generate temporary token for 2FA flow
        token = hashlib.sha256(os.urandom(32)).hexdigest()[:32]
        frappe.cache().set_value(
            f"qalcuity_2fa_pending:{token}",
            {
                "user": user_email,
                "password_hash": hashlib.sha256(password.encode()).hexdigest(),
                "created": int(time.time()),
            },
            expires_in=300,  # 5 minutes
        )

        return {
            "status": "2fa_required",
            "token": token,
            "message": _("Autentikasi dua faktor diperlukan."),
        }

    # No 2FA — proceed with normal login
    return {
        "status": "ok",
        "message": _("Login berhasil."),
    }


# =============================================================================
# Login Flow: Verify 2FA code and complete login
# =============================================================================

@frappe.whitelist(allow_guest=True)
def verify_2fa_login(token, code):
    """Verify 2FA code during login and create session.

    Args:
        token: Temporary token from pre_login_check
        code: 6-digit TOTP code or backup code

    Returns:
        dict: Login status
    """
    if not token or not code:
        frappe.throw(_("Token dan kode harus diisi."))

    # Get pending login data
    pending = frappe.cache().get_value(f"qalcuity_2fa_pending:{token}")
    if not pending:
        frappe.throw(_("Sesi verifikasi 2FA telah kedaluwarsa. Silakan login kembali."))

    user = pending.get("user")
    if not user:
        frappe.throw(_("Data sesi tidak valid."))

    # Get user secret
    secret = frappe.db.get_value("User", user, "secret")
    if not secret:
        frappe.throw(_("2FA tidak dikonfigurasi untuk akun ini."))

    # Verify TOTP code first
    code_valid = _verify_totp(secret, code)

    # If TOTP failed, try backup code
    if not code_valid:
        code_valid = _verify_backup_code(user, code)

    if not code_valid:
        frappe.throw(_("Kode verifikasi tidak valid."))

    # Clear the pending token
    frappe.cache().delete_value(f"qalcuity_2fa_pending:{token}")

    # Create session using Frappe's LoginManager
    from frappe.auth import LoginManager

    frappe.local.login_manager = LoginManager()
    frappe.local.login_manager.user = user
    frappe.local.login_manager.make_session()

    frappe.db.commit()

    # Log audit
    _create_audit_log(user, "2FA Login", f"User {user} completed 2FA login")

    return {
        "status": "ok",
        "message": _("Login berhasil."),
        "redirect": "/app",
    }


# =============================================================================
# API: Check if user needs 2FA (for profile page)
# =============================================================================

@frappe.whitelist()
def get_2fa_qr_for_profile():
    """Get QR code data for 2FA setup from profile page.

    Returns:
        dict: QR code URL and secret
    """
    return setup_2fa()


# =============================================================================
# Helper: Create Audit Log
# =============================================================================

def _create_audit_log(user, action, details):
    """Create an audit log entry for 2FA actions.

    Args:
        user: User email/name
        action: Action description
        details: Additional details
    """
    try:
        frappe.get_doc({
            "doctype": "Qalcuity Audit Log",
            "user": user,
            "action": action,
            "details": details,
            "ip_address": frappe.local.request_ip if hasattr(frappe.local, "request_ip") else "",
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        pass  # Don't fail if audit log creation fails
