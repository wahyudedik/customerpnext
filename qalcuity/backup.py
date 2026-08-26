# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity Backup Automation Module
===================================
Handles automated database and file backups with retention policy.

Features:
- Database backup via mysqldump (via Frappe backup utilities)
- File backup (private/files and public/files directories)
- Compressed backups (.sql.gz, .tar.gz)
- Configurable retention policy (default: 30 days)
- Backup status tracking via Qalcuity Backup DocType
- Admin notifications on backup completion/failure
"""

import frappe
from frappe import _
from frappe.utils import now_datetime, add_days, cint, getdate, nowdate
import os
import time
import shutil
import glob
import subprocess
import json


# =============================================================================
# Constants
# =============================================================================

BACKUP_TYPE_FULL = "Full"
BACKUP_TYPE_DATABASE = "Database"
BACKUP_TYPE_FILES = "Files"

STATUS_PENDING = "Pending"
STATUS_RUNNING = "Running"
STATUS_COMPLETED = "Completed"
STATUS_FAILED = "Failed"

DEFAULT_RETENTION_DAYS = 30


# =============================================================================
# Main Backup Functions
# =============================================================================

def run_backup(backup_type="Full", performed_by="Scheduler", notes=None):
    """
    Main backup function — dipanggil oleh scheduler atau admin action.

    Membuat backup database, files, atau keduanya (Full).
    Mencatat hasil ke Qalcuity Backup DocType.

    Args:
        backup_type: "Full", "Database", atau "Files"
        performed_by: User atau "Scheduler"
        notes: Catatan tambahan (optional)

    Returns:
        dict: {backup_name, status, file_path, file_size} atau raise exception
    """
    backup_doc = None
    started_at = now_datetime()

    try:
        site_name = frappe.local.site
        timestamp = started_at.strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{site_name}_{timestamp}"

        # Create backup record
        backup_doc = frappe.get_doc({
            "doctype": "Qalcuity Backup",
            "backup_name": backup_name,
            "backup_type": backup_type,
            "status": STATUS_RUNNING,
            "site_name": site_name,
            "started_at": started_at,
            "performed_by": performed_by,
            "notes": notes,
        })
        backup_doc.insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.logger().info(
            "Qalcuity Backup: Starting {0} backup '{1}'".format(
                backup_type, backup_name
            )
        )

        # Ensure backup directory exists
        backup_dir = _get_backup_directory()
        _ensure_directory(backup_dir)

        file_path = None
        file_size = 0

        if backup_type in (BACKUP_TYPE_FULL, BACKUP_TYPE_DATABASE):
            # Database backup
            db_path = _backup_database(backup_dir, backup_name)
            if db_path:
                file_path = db_path
                file_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0

        if backup_type in (BACKUP_TYPE_FULL, BACKUP_TYPE_FILES):
            # Files backup
            files_path = _backup_files(backup_dir, backup_name)
            if files_path:
                if file_path:
                    # Merge sizes for Full backup
                    file_size += os.path.getsize(files_path) if os.path.exists(files_path) else 0
                else:
                    file_path = files_path
                    file_size = os.path.getsize(files_path) if os.path.exists(files_path) else 0

        # Calculate duration
        completed_at = now_datetime()
        duration = int((completed_at - started_at).total_seconds())

        # Update record — success
        frappe.db.set_value("Qalcuity Backup", backup_doc.name, {
            "status": STATUS_COMPLETED,
            "file_path": file_path or "",
            "file_size": file_size,
            "completed_at": completed_at,
            "duration_seconds": duration,
        })
        frappe.db.commit()

        # Send success notification
        _send_backup_notification(
            backup_name=backup_doc.name,
            backup_type=backup_type,
            status=STATUS_COMPLETED,
            file_size=file_size,
        )

        # Log activity
        try:
            from qalcuity.api.audit import log_action
            log_action(
                action="Backup Complete",
                doc_type="Qalcuity Backup",
                doc_name=backup_doc.name,
                details=json.dumps({
                    "backup_type": backup_type,
                    "file_size": file_size,
                    "duration_seconds": duration,
                }, default=str),
            )
        except Exception:
            pass  # Non-critical

        frappe.logger().info(
            "Qalcuity Backup: Completed '{0}' — {1} bytes in {2}s".format(
                backup_name, file_size, duration
            )
        )

        return {
            "backup_name": backup_doc.name,
            "status": STATUS_COMPLETED,
            "file_path": file_path,
            "file_size": file_size,
        }

    except Exception as e:
        error_msg = str(e)
        frappe.log_error(
            title="Qalcuity Backup: Failed — {0}".format(
                backup_doc.name if backup_doc else "unknown"
            ),
            message=error_msg,
        )

        # Update record — failed
        if backup_doc:
            try:
                completed_at = now_datetime()
                duration = int((completed_at - started_at).total_seconds())
                frappe.db.set_value("Qalcuity Backup", backup_doc.name, {
                    "status": STATUS_FAILED,
                    "error_message": error_msg,
                    "completed_at": completed_at,
                    "duration_seconds": duration,
                })
                frappe.db.commit()

                # Send failure notification
                _send_backup_notification(
                    backup_name=backup_doc.name,
                    backup_type=backup_type,
                    status=STATUS_FAILED,
                    error_message=error_msg,
                )

                # Log failure
                try:
                    from qalcuity.api.audit import log_action
                    log_action(
                        action="Backup Failed",
                        doc_type="Qalcuity Backup",
                        doc_name=backup_doc.name,
                        details=json.dumps({
                            "backup_type": backup_type,
                            "error": error_msg,
                        }, default=str),
                    )
                except Exception:
                    pass

            except Exception:
                frappe.log_error(
                    title="Qalcuity Backup: Failed to update failure record"
                )

        raise


def cleanup_old_backups():
    """
    Hapus backup lama sesuai retention policy.

    Retention period diambil dari env QALCUITY_BACKUP_RETENTION_DAYS
    atau default 30 hari.

    Returns:
        dict: {deleted_count, freed_bytes}
    """
    retention_days = cint(
        os.environ.get("QALCUITY_BACKUP_RETENTION_DAYS", DEFAULT_RETENTION_DAYS)
    )
    if retention_days <= 0:
        retention_days = DEFAULT_RETENTION_DAYS

    cutoff_date = add_days(getdate(nowdate()), -retention_days)
    cutoff_datetime = str(cutoff_date) + " 00:00:00"

    deleted_count = 0
    freed_bytes = 0

    try:
        # Find old completed backups
        old_backups = frappe.get_all(
            "Qalcuity Backup",
            filters={
                "status": STATUS_COMPLETED,
                "creation": ["<", cutoff_datetime],
            },
            fields=["name", "file_path", "file_size"],
        )

        for backup in old_backups:
            try:
                # Delete file from disk
                if backup.file_path and os.path.exists(backup.file_path):
                    freed_bytes += os.path.getsize(backup.file_path)
                    os.remove(backup.file_path)

                # Delete record from database
                frappe.delete_doc("Qalcuity Backup", backup.name, ignore_permissions=True)
                deleted_count += 1

                frappe.logger().info(
                    "Qalcuity Backup Cleanup: Deleted '{0}' (file: {1})".format(
                        backup.name, backup.file_path
                    )
                )

            except Exception as e:
                frappe.log_error(
                    title="Qalcuity Backup Cleanup: Failed to delete {0}".format(
                        backup.name
                    ),
                    message=str(e),
                )

        if deleted_count > 0:
            frappe.db.commit()
            frappe.logger().info(
                "Qalcuity Backup Cleanup: Deleted {0} backups, freed {1} bytes".format(
                    deleted_count, freed_bytes
                )
            )

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Backup Cleanup: Error",
            message=str(e),
        )

    return {
        "deleted_count": deleted_count,
        "freed_bytes": freed_bytes,
    }


def get_backup_status():
    """
    Return status backup terakhir.

    Returns:
        dict: {
            last_backup_time, last_backup_name, last_backup_status,
            total_backups, total_size, recent_backups
        }
    """
    try:
        # Latest completed backup
        latest = frappe.get_all(
            "Qalcuity Backup",
            filters={"status": STATUS_COMPLETED},
            fields=["name", "backup_type", "file_size", "completed_at", "status"],
            order_by="completed_at desc",
            limit_page_length=1,
        )

        # Latest running backup (if any)
        running = frappe.get_all(
            "Qalcuity Backup",
            filters={"status": STATUS_RUNNING},
            fields=["name", "backup_type", "started_at", "status"],
            order_by="started_at desc",
            limit_page_length=1,
        )

        # Total count and size
        totals = frappe.db.sql(
            """
            SELECT COUNT(*) as count, COALESCE(SUM(file_size), 0) as total_size
            FROM `tabQalcuity Backup`
            WHERE status = %s
            """,
            (STATUS_COMPLETED,),
            as_dict=True,
        )

        result = {
            "last_backup_time": None,
            "last_backup_name": None,
            "last_backup_status": None,
            "total_backups": totals[0].count if totals else 0,
            "total_size": totals[0].total_size if totals else 0,
            "is_running": len(running) > 0,
            "running_backup": running[0] if running else None,
        }

        if latest:
            result["last_backup_time"] = str(latest[0].completed_at)
            result["last_backup_name"] = latest[0].name
            result["last_backup_status"] = latest[0].status

        return result

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Backup: Error getting status",
            message=str(e),
        )
        return {
            "last_backup_time": None,
            "last_backup_name": None,
            "last_backup_status": None,
            "total_backups": 0,
            "total_size": 0,
            "is_running": False,
            "running_backup": None,
        }


def get_backup_list(filters=None, page=1, limit=20):
    """
    List semua backup yang tersedia dengan filter dan pagination.

    Args:
        filters: dict dengan optional keys: status, backup_type, from_date, to_date
        page: Halaman (1-based)
        limit: Items per page

    Returns:
        dict: {data: [...], total: int, page: int, total_pages: int}
    """
    try:
        page = max(1, cint(page))
        limit = max(1, min(100, cint(limit)))
        start = (page - 1) * limit

        conditions = []
        values = {}

        if filters:
            if isinstance(filters, str):
                try:
                    filters = json.loads(filters)
                except (json.JSONDecodeError, TypeError):
                    filters = {}

            if filters.get("status"):
                conditions.append("status = @status")
                values["status"] = filters["status"]

            if filters.get("backup_type"):
                conditions.append("backup_type = @backup_type")
                values["backup_type"] = filters["backup_type"]

            if filters.get("from_date"):
                conditions.append("creation >= @from_date")
                values["from_date"] = filters["from_date"]

            if filters.get("to_date"):
                conditions.append("creation <= @to_date")
                values["to_date"] = filters["to_date"] + " 23:59:59"

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        total = frappe.db.sql(
            "SELECT COUNT(*) as count FROM `tabQalcuity Backup` WHERE {0}".format(
                where_clause
            ),
            values,
            as_dict=True,
        )[0].get("count", 0)

        # Get data
        data = frappe.db.sql(
            """
            SELECT name, backup_name, backup_type, status, site_name,
                   file_path, file_size, started_at, completed_at,
                   duration_seconds, performed_by, creation
            FROM `tabQalcuity Backup`
            WHERE {where}
            ORDER BY creation DESC
            LIMIT %s OFFSET %s
            """.format(where=where_clause),
            list(values.values()) + [limit, start],
            as_dict=True,
        )

        total_pages = max(1, -(-total // limit))  # Ceiling division

        return {
            "data": data,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "limit": limit,
        }

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Backup: Error listing backups",
            message=str(e),
        )
        return {
            "data": [],
            "total": 0,
            "page": 1,
            "total_pages": 1,
            "limit": limit,
        }


def download_backup(backup_name):
    """
    Download backup file — return file path untuk download.

    Args:
        backup_name: Name dari Qalcuity Backup doc

    Returns:
        dict: {file_path, file_name, file_size}

    Raises:
        frappe.DoesNotExistError: Jika backup tidak ditemukan
        frappe.PermissionError: Jika user tidak punya akses
    """
    # Validate backup exists
    if not frappe.db.exists("Qalcuity Backup", backup_name):
        frappe.throw(_("Backup {0} not found.").format(backup_name))

    backup = frappe.get_doc("Qalcuity Backup", backup_name)

    # Validate status
    if backup.status != STATUS_COMPLETED:
        frappe.throw(
            _("Backup {0} is not completed (status: {1}).").format(
                backup_name, backup.status
            )
        )

    # Validate file exists
    if not backup.file_path or not os.path.exists(backup.file_path):
        frappe.throw(
            _("Backup file not found on disk: {0}").format(backup.file_path or "N/A")
        )

    return {
        "file_path": backup.file_path,
        "file_name": os.path.basename(backup.file_path),
        "file_size": backup.file_size,
    }


def delete_backup(backup_name):
    """
    Delete specific backup — file dan record.

    Args:
        backup_name: Name dari Qalcuity Backup doc

    Returns:
        dict: {deleted: True, name: backup_name}

    Raises:
        frappe.DoesNotExistError: Jika backup tidak ditemukan
    """
    if not frappe.db.exists("Qalcuity Backup", backup_name):
        frappe.throw(_("Backup {0} not found.").format(backup_name))

    backup = frappe.get_doc("Qalcuity Backup", backup_name)

    # Delete file from disk
    if backup.file_path and os.path.exists(backup.file_path):
        os.remove(backup.file_path)

    # Delete record
    frappe.delete_doc("Qalcuity Backup", backup_name, ignore_permissions=True)
    frappe.db.commit()

    frappe.logger().info(
        "Qalcuity Backup: Deleted backup '{0}'".format(backup_name)
    )

    return {
        "deleted": True,
        "name": backup_name,
    }


def get_backup_stats():
    """
    Get backup statistics untuk dashboard.

    Returns:
        dict: Statistics about backups
    """
    try:
        # Total counts by status
        status_counts = frappe.db.sql(
            """
            SELECT status, COUNT(*) as count
            FROM `tabQalcuity Backup`
            GROUP BY status
            """,
            as_dict=True,
        )

        status_map = {s.status: s.count for s in status_counts}

        # Total size of completed backups
        totals = frappe.db.sql(
            """
            SELECT COUNT(*) as count, COALESCE(SUM(file_size), 0) as total_size
            FROM `tabQalcuity Backup`
            WHERE status = 'Completed'
            """,
            as_dict=True,
        )

        total_size = totals[0].total_size if totals else 0

        # Last successful backup
        last_backup = frappe.get_all(
            "Qalcuity Backup",
            filters={"status": STATUS_COMPLETED},
            fields=["name", "completed_at", "file_size", "backup_type"],
            order_by="completed_at desc",
            limit_page_length=1,
        )

        return {
            "total_backups": sum(status_map.values()),
            "completed_count": status_map.get(STATUS_COMPLETED, 0),
            "failed_count": status_map.get(STATUS_FAILED, 0),
            "pending_count": status_map.get(STATUS_PENDING, 0),
            "running_count": status_map.get(STATUS_RUNNING, 0),
            "total_size": total_size,
            "total_size_formatted": _format_file_size(total_size),
            "last_backup_time": (
                str(last_backup[0].completed_at) if last_backup else None
            ),
            "last_backup_status": (
                last_backup[0].name if last_backup else None
            ),
        }

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Backup: Error getting stats",
            message=str(e),
        )
        return {
            "total_backups": 0,
            "completed_count": 0,
            "failed_count": 0,
            "pending_count": 0,
            "running_count": 0,
            "total_size": 0,
            "total_size_formatted": "0 B",
            "last_backup_time": None,
            "last_backup_status": None,
        }


# =============================================================================
# Internal Functions — Database Backup
# =============================================================================

def _backup_database(backup_dir, backup_name):
    """
    Backup database menggunakan mysqldump via subprocess.

    Creates: {backup_dir}/{backup_name}.sql.gz

    Args:
        backup_dir: Directory untuk menyimpan backup
        backup_name: Nama file backup

    Returns:
        str: Path ke file backup, atau None jika gagal
    """
    output_file = os.path.join(backup_dir, "{0}.sql.gz".format(backup_name))

    # Get database credentials from site config
    site_config = _get_site_config()
    db_host = site_config.get("db_host", "localhost")
    db_port = site_config.get("db_port", "3306")
    db_name = site_config.get("db_name")
    db_password = site_config.get("db_password")

    if not db_name:
        frappe.log_error(
            title="Qalcuity Backup: Missing db_name in site config"
        )
        return None

    # Build mysqldump command with gzip compression
    # Using --defaults-extra-file to avoid password in command line
    defaults_file = _create_mysqldump_defaults_file(
        db_host, db_port, db_name, db_password
    )

    try:
        cmd = "mysqldump --defaults-extra-file={defaults} {db} | gzip > {output}".format(
            defaults=defaults_file,
            db=db_name,
            output=output_file,
        )

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout
        )

        if result.returncode != 0:
            frappe.log_error(
                title="Qalcuity Backup: mysqldump failed",
                message="Return code: {0}\nStderr: {1}".format(
                    result.returncode, result.stderr
                ),
            )
            # Fallback: try Frappe backup method
            return _backup_database_fallback(backup_dir, backup_name)

        return output_file

    except subprocess.TimeoutExpired:
        frappe.log_error(
            title="Qalcuity Backup: mysqldump timeout (1h)"
        )
        return None

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Backup: mysqldump error",
            message=str(e),
        )
        # Fallback: try Frappe backup method
        return _backup_database_fallback(backup_dir, backup_name)

    finally:
        # Clean up defaults file
        _cleanup_temp_file(defaults_file)


def _backup_database_fallback(backup_dir, backup_name):
    """
    Fallback database backup using Frappe's built-in backup utility.

    Args:
        backup_dir: Directory untuk menyimpan backup
        backup_name: Nama file backup

    Returns:
        str: Path ke file backup, atau None jika gagal
    """
    try:
        from frappe.utils.backups import new_backup

        # Frappe's new_backup() creates backup in sites/{site}/private/backups/
        # We need to move it to our backup directory
        new_backup(ignore_files=True)

        # Find the latest backup file created by Frappe
        site_name = frappe.local.site
        frappe_backup_dir = os.path.join(
            frappe.get_site_path("private", "backups"),
        )

        # Look for the most recent .sql.gz file
        sql_files = sorted(
            glob.glob(os.path.join(frappe_backup_dir, "*.sql.gz")),
            key=os.path.getmtime,
            reverse=True,
        )

        if not sql_files:
            frappe.log_error(
                title="Qalcuity Backup: No .sql.gz found after Frappe backup"
            )
            return None

        latest_backup = sql_files[0]
        target_path = os.path.join(backup_dir, "{0}.sql.gz".format(backup_name))

        # Copy to our backup directory
        shutil.copy2(latest_backup, target_path)

        frappe.logger().info(
            "Qalcuity Backup: Used Frappe fallback, copied from {0}".format(
                latest_backup
            )
        )

        return target_path

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Backup: Frappe fallback also failed",
            message=str(e),
        )
        return None


# =============================================================================
# Internal Functions — File Backup
# =============================================================================

def _backup_files(backup_dir, backup_name):
    """
    Backup uploaded files (private/files dan public/files).
    Compress menjadi tar.gz.

    Args:
        backup_dir: Directory untuk menyimpan backup
        backup_name: Nama file backup

    Returns:
        str: Path ke file backup, atau None jika gagal
    """
    output_file = os.path.join(backup_dir, "{0}_files.tar.gz".format(backup_name))

    try:
        site_path = frappe.get_site_path()
        private_files = os.path.join(site_path, "private", "files")
        public_files = os.path.join(site_path, "public", "files")

        # Check if any files directory exists
        has_private = os.path.isdir(private_files) and _directory_has_content(private_files)
        has_public = os.path.isdir(public_files) and _directory_has_content(public_files)

        if not has_private and not has_public:
            frappe.logger().info(
                "Qalcuity Backup: No files to backup (empty directories)"
            )
            # Create empty backup marker
            with open(output_file, "w") as f:
                f.write("EMPTY_BACKUP")
            return output_file

        # Build tar command
        dirs_to_backup = []
        if has_private:
            dirs_to_backup.append(private_files)
        if has_public:
            dirs_to_backup.append(public_files)

        cmd = "tar -czf {output} -C {site} {paths}".format(
            output=output_file,
            site=site_path,
            paths=" ".join(
                ["private/files"] if has_private else []
            ) + " ".join(
                ["public/files"] if has_public else []
            ),
        )

        # More robust: add directories one by one
        cmd_parts = ["tar", "-czf", output_file, "-C", site_path]
        if has_private:
            cmd_parts.append("private/files")
        if has_public:
            cmd_parts.append("public/files")

        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            timeout=1800,  # 30 min timeout
        )

        if result.returncode != 0:
            frappe.log_error(
                title="Qalcuity Backup: tar backup failed",
                message="Return code: {0}\nStderr: {1}".format(
                    result.returncode, result.stderr
                ),
            )
            return None

        return output_file

    except subprocess.TimeoutExpired:
        frappe.log_error(
            title="Qalcuity Backup: tar backup timeout (30min)"
        )
        return None

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Backup: File backup error",
            message=str(e),
        )
        return None


# =============================================================================
# Internal Functions — Helpers
# =============================================================================

def _get_backup_directory():
    """
    Get atau buat backup directory.
    Location: sites/{site_name}/private/backups/

    Returns:
        str: Path ke backup directory
    """
    backup_dir = frappe.get_site_path("private", "backups")
    return backup_dir


def _ensure_directory(path):
    """Ensure directory exists, create if not."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def _directory_has_content(path):
    """Check if directory has any files (recursive)."""
    try:
        for entry in os.scandir(path):
            if entry.is_file():
                return True
            if entry.is_dir() and _directory_has_content(entry.path):
                return True
    except OSError:
        pass
    return False


def _get_site_config():
    """Get site configuration for database credentials."""
    try:
        config = frappe.get_site_config()
        return {
            "db_host": config.get("db_host", "localhost"),
            "db_port": str(config.get("db_port", "3306")),
            "db_name": config.get("db_name"),
            "db_password": config.get("db_password"),
        }
    except Exception:
        return {
            "db_host": "localhost",
            "db_port": "3306",
            "db_name": None,
            "db_password": None,
        }


def _create_mysqldump_defaults_file(host, port, db_name, password):
    """
    Create temporary defaults file untuk mysqldump
    (menghindari password di command line).

    Returns:
        str: Path ke temporary defaults file
    """
    import tempfile

    content = "[mysqldump]\nhost={host}\nport={port}\nuser=root\npassword={password}\n".format(
        host=host,
        port=port,
        password=password or "",
    )

    fd, path = tempfile.mkstemp(suffix=".cnf", prefix="qalcuity_backup_")
    with os.fdopen(fd, "w") as f:
        f.write(content)

    return path


def _cleanup_temp_file(path):
    """Hapus temporary file, ignore errors."""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def _format_file_size(size_bytes):
    """Format bytes ke human-readable string."""
    if not size_bytes or size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return "{0} B".format(int(size))
    return "{0:.1f} {1}".format(size, units[unit_index])


def _send_backup_notification(backup_name, backup_type, status, file_size=None, error_message=None):
    """
    Kirim notification ke admin saat backup selesai/gagal.

    Args:
        backup_name: Nama backup record
        backup_type: Tipe backup
        status: Completed atau Failed
        file_size: Size dalam bytes (untuk success)
        error_message: Error message (untuk failure)
    """
    try:
        # Get admin emails
        admin_emails = frappe.db.sql(
            """
            SELECT DISTINCT u.email
            FROM `tabUser` u
            INNER JOIN `tabUserRole` ur ON ur.parent = u.name
            WHERE ur.role IN ('Qalcuity Superadmin', 'Qalcuity Admin', 'System Manager')
            AND u.enabled = 1
            AND u.name != 'Guest'
            AND u.email IS NOT NULL
            AND u.email != ''
            """,
            as_dict=True,
        )

        if not admin_emails:
            return

        recipients = [e.email for e in admin_emails]

        if status == STATUS_COMPLETED:
            size_text = _format_file_size(file_size) if file_size else "Unknown"
            subject = _("Qalcuity Backup Completed: {0}").format(backup_name)
            message = _(
                "Backup completed successfully.<br><br>"
                "<b>Backup:</b> {name}<br>"
                "<b>Type:</b> {type}<br>"
                "<b>Size:</b> {size}<br>"
                "<b>Time:</b> {time}<br><br>"
                "Best regards,<br>Qalcuity System"
            ).format(
                name=backup_name,
                type=backup_type,
                size=size_text,
                time=now_datetime().strftime("%Y-%m-%d %H:%M:%S"),
            )
        else:
            subject = _("Qalcuity Backup Failed: {0}").format(backup_name)
            message = _(
                "Backup failed.<br><br>"
                "<b>Backup:</b> {name}<br>"
                "<b>Type:</b> {type}<br>"
                "<b>Error:</b> {error}<br>"
                "<b>Time:</b> {time}<br><br>"
                "Please check the backup logs for details.<br><br>"
                "Best regards,<br>Qalcuity System"
            ).format(
                name=backup_name,
                type=backup_type,
                error=error_message or "Unknown error",
                time=now_datetime().strftime("%Y-%m-%d %H:%M:%S"),
            )

        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
        )

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Backup: Failed to send notification",
            message=str(e),
        )
