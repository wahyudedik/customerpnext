# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Upload Security utilities for Qalcuity ERP.
Validates file type, size, and basic security checks for file uploads.
"""

import frappe
import os
import re


# =============================================================================
# Constants
# =============================================================================

# Allowed file types untuk payment proof
ALLOWED_PAYMENT_PROOF_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/webp": [".webp"],
    "application/pdf": [".pdf"],
}

# Max file sizes (MB)
MAX_FILE_SIZES = {
    "payment_proof": 5,  # dari Qalcuity Settings max_file_size_mb
    "profile_image": 2,
    "general": 5,
}

# Dangerous file extensions to block
DANGEROUS_EXTENSIONS = {
    ".php", ".php3", ".php4", ".php5", ".php7", ".phps", ".pht", ".phtml",
    ".cgi", ".pl", ".py", ".rb", ".sh", ".bash",
    ".exe", ".com", ".bat", ".cmd", ".msi", ".scr",
    ".jsp", ".jspx", ".asp", ".aspx", ".cer", ".cfm",
    ".svg",  # SVG bisa mengandung XSS/JavaScript
    ".js", ".vbs", ".vbe", ".wsf", ".wsh",
    ".htaccess", ".htpasswd",
}


# =============================================================================
# Core Validation
# =============================================================================

def validate_upload(file_name, file_size, file_content=None, upload_type="general"):
    """
    Validate uploaded file.

    Args:
        file_name: Original filename
        file_size: File size in bytes
        file_content: Raw file content bytes (optional, for content checks)
        upload_type: Type of upload (payment_proof, profile_image, general)

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if not file_name:
        return False, "File name is required."

    # 1. Normalize file size to integer
    try:
        file_size = int(file_size) if file_size else 0
    except (ValueError, TypeError):
        file_size = 0

    # 2. Check file extension
    _, ext = os.path.splitext(file_name)
    ext = ext.lower()

    if not ext:
        return False, "File must have an extension."

    # 3. Block dangerous extensions
    if ext in DANGEROUS_EXTENSIONS:
        return False, "File type is not allowed for security reasons."

    # 4. Check file size
    max_size_mb = MAX_FILE_SIZES.get(upload_type, 5)
    max_size_bytes = max_size_mb * 1024 * 1024

    if file_size > max_size_bytes:
        return False, "File too large. Maximum size is {0}MB.".format(max_size_mb)

    if file_size == 0:
        return False, "File is empty."

    # 5. Check file type for payment proof
    if upload_type == "payment_proof":
        allowed_extensions = []
        for exts in ALLOWED_PAYMENT_PROOF_TYPES.values():
            allowed_extensions.extend(exts)

        if ext not in allowed_extensions:
            return False, "File type not allowed. Allowed: {0}.".format(
                ", ".join(allowed_extensions)
            )

    # 6. Check for double extensions (security: image.php.jpg)
    name_without_ext = os.path.splitext(file_name)[0]
    if "." in name_without_ext:
        return False, "File name with multiple extensions is not allowed."

    # 7. Check for null bytes
    if file_content and b"\x00" in file_content:
        return False, "Invalid file content."

    # 8. Check filename length
    if len(file_name) > 255:
        return False, "File name is too long (maximum 255 characters)."

    return True, None


def sanitize_filename(filename):
    """
    Sanitize filename — remove dangerous characters.

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename
    """
    if not filename:
        return "unnamed_file"

    # Remove path components
    filename = os.path.basename(filename)

    # Remove special characters except ., -, _ and spaces
    filename = re.sub(r'[^\w\-_\. ]', '', filename)

    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")

    # If empty after sanitization
    if not filename:
        return "unnamed_file"

    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext

    return filename


def get_allowed_extensions(upload_type="general"):
    """
    Get list of allowed extensions for a given upload type.

    Args:
        upload_type: Type of upload

    Returns:
        list: Allowed file extensions
    """
    if upload_type == "payment_proof":
        allowed = []
        for exts in ALLOWED_PAYMENT_PROOF_TYPES.values():
            allowed.extend(exts)
        return allowed

    # Default: common safe types
    return [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".doc", ".docx"]


def get_max_file_size_mb(upload_type="general"):
    """
    Get max file size in MB for a given upload type.

    Args:
        upload_type: Type of upload

    Returns:
        int: Max file size in MB
    """
    return MAX_FILE_SIZES.get(upload_type, 5)


def is_valid_image_content(file_content):
    """
    Check if file content is a valid image by checking magic bytes.

    Args:
        file_content: Raw file content bytes

    Returns:
        bool: True if content appears to be a valid image
    """
    if not file_content or len(file_content) < 4:
        return False

    # Check magic bytes
    signatures = {
        b'\xff\xd8\xff': 'jpeg',
        b'\x89PNG': 'png',
        b'RIFF': 'webp',  # WebP starts with RIFF
    }

    for sig, fmt in signatures.items():
        if file_content[:len(sig)] == sig:
            return True

    # Check for PDF
    if file_content[:5] == b'%PDF-':
        return True

    return False
