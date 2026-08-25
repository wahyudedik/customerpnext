# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity Backup API
====================
API endpoints untuk backup operations.

Endpoints:
- trigger_backup() — Manual trigger backup (admin only)
- get_backup_status() — Get latest backup status
- get_backup_list() — List backups with pagination
- download_backup() — Download backup file (admin only)
- delete_backup() — Delete specific backup (admin only)
- get_backup_stats() — Get backup statistics
"""

import frappe
from frappe import _
import json


# =============================================================================
# Admin Check Helper
# =============================================================================

def _require_admin():
    """Cek apakah user adalah admin/superadmin."""
    try:
        from qalcuity.qalcuity.isolation import is_admin_user
        if not is_admin_user():
            frappe.throw(_("Access denied. Admin privileges required."))
    except ImportError:
        # Fallback: check roles directly
        user_roles = frappe.get_roles(frappe.session.user)
        admin_roles = ["System Manager", "Qalcuity Superadmin", "Qalcuity Admin"]
        if not any(role in user_roles for role in admin_roles):
            frappe.throw(_("Access denied. Admin privileges required."))


# =============================================================================
# API Endpoints
# =============================================================================

@frappe.whitelist()
def trigger_backup(backup_type="Full"):
    """
    Manual trigger backup — admin only.

    Args:
        backup_type: "Full", "Database", atau "Files"

    Returns:
        dict: {backup_name, status, message}
    """
    _require_admin()

    # Validate backup type
    valid_types = ["Full", "Database", "Files"]
    if backup_type not in valid_types:
        frappe.throw(
            _("Invalid backup type: {0}. Must be one of: {1}").format(
                backup_type, ", ".join(valid_types)
            )
        )

    try:
        from qalcuity.qalcuity.backup import run_backup

        result = run_backup(
            backup_type=backup_type,
            performed_by=frappe.session.user,
            notes="Manual trigger by {0}".format(frappe.session.user),
        )

        return {
            "backup_name": result.get("backup_name"),
            "status": result.get("status"),
            "file_size": result.get("file_size"),
            "message": _("Backup completed successfully."),
        }

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Backup API: trigger_backup failed",
            message=str(e),
        )
        frappe.throw(
            _("Backup failed: {0}").format(str(e))
        )


@frappe.whitelist()
def get_backup_status():
    """
    Get latest backup status.

    Returns:
        dict: Backup status information
    """
    try:
        from qalcuity.qalcuity.backup import get_backup_status as _get_backup_status
        return _get_backup_status()

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Backup API: get_backup_status failed",
            message=str(e),
        )
        frappe.throw(
            _("Failed to get backup status: {0}").format(str(e))
        )


@frappe.whitelist()
def get_backup_list(page=1, limit=20, filters=None):
    """
    List backups with pagination.

    Args:
        page: Halaman (1-based, default: 1)
        limit: Items per page (default: 20, max: 100)
        filters: JSON string atau dict dengan keys: status, backup_type, from_date, to_date

    Returns:
        dict: {data, total, page, total_pages, limit}
    """
    _require_admin()

    try:
        from qalcuity.qalcuity.backup import get_backup_list as _get_backup_list

        # Parse filters
        if filters and isinstance(filters, str):
            try:
                filters = json.loads(filters)
            except (json.JSONDecodeError, TypeError):
                filters = {}

        return _get_backup_list(
            filters=filters,
            page=int(page),
            limit=int(limit),
        )

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Backup API: get_backup_list failed",
            message=str(e),
        )
        frappe.throw(
            _("Failed to get backup list: {0}").format(str(e))
        )


@frappe.whitelist()
def download_backup(backup_name):
    """
    Download backup file — admin only.

    Args:
        backup_name: Name dari Qalcuity Backup doc

    Returns:
        dict: {file_path, file_name, file_size}
    """
    _require_admin()

    try:
        from qalcuity.qalcuity.backup import download_backup as _download_backup
        return _download_backup(backup_name)

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Backup API: download_backup failed",
            message=str(e),
        )
        frappe.throw(
            _("Failed to download backup: {0}").format(str(e))
        )


@frappe.whitelist()
def delete_backup(backup_name):
    """
    Delete specific backup — admin only.

    Args:
        backup_name: Name dari Qalcuity Backup doc

    Returns:
        dict: {deleted: True, name: backup_name}
    """
    _require_admin()

    try:
        from qalcuity.qalcuity.backup import delete_backup as _delete_backup
        return _delete_backup(backup_name)

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Backup API: delete_backup failed",
            message=str(e),
        )
        frappe.throw(
            _("Failed to delete backup: {0}").format(str(e))
        )


@frappe.whitelist()
def get_backup_stats():
    """
    Get backup statistics.

    Returns:
        dict: Backup statistics
    """
    _require_admin()

    try:
        from qalcuity.qalcuity.backup import get_backup_stats as _get_backup_stats
        return _get_backup_stats()

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Backup API: get_backup_stats failed",
            message=str(e),
        )
        frappe.throw(
            _("Failed to get backup statistics: {0}").format(str(e))
        )


@frappe.whitelist()
def trigger_cleanup():
    """
    Manual trigger cleanup old backups — admin only.

    Returns:
        dict: {deleted_count, freed_bytes, message}
    """
    _require_admin()

    try:
        from qalcuity.qalcuity.backup import cleanup_old_backups
        result = cleanup_old_backups()

        return {
            "deleted_count": result.get("deleted_count", 0),
            "freed_bytes": result.get("freed_bytes", 0),
            "message": _("Cleanup completed. Deleted {0} backups.").format(
                result.get("deleted_count", 0)
            ),
        }

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Backup API: trigger_cleanup failed",
            message=str(e),
        )
        frappe.throw(
            _("Failed to run cleanup: {0}").format(str(e))
        )
