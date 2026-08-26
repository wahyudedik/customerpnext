# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity System Health API
============================
System health monitoring endpoints for superadmin dashboard.
Provides server status, database info, application versions,
activity metrics, and health checks.

Uses Python stdlib only (no psutil dependency).
Fallback methods for system stats when psutil is unavailable.
"""

import os
import platform
import time
import json

import frappe
from frappe import _
from frappe.utils import now_datetime, cint, flt


# =============================================================================
# Main Health Endpoint
# =============================================================================

@frappe.whitelist()
def get_system_health():
    """
    Get comprehensive system health data for admin monitoring.

    Returns:
        dict: System health data with server, application, activity, and health check info
    """
    user = frappe.session.user

    if user == "Guest":
        frappe.throw(_("Please login to access system health."))

    from qalcuity.isolation import is_admin_user
    if not is_admin_user():
        frappe.throw(_("You do not have permission to access system health."))

    data = {
        "system": _get_system_status(),
        "application": _get_application_status(),
        "activity": _get_activity_stats(),
        "health_checks": _get_health_checks(),
        "timestamp": str(now_datetime()),
    }

    return data


# =============================================================================
# System Status
# =============================================================================

def _get_system_status():
    """Get server system status: uptime, disk, memory, CPU."""
    return {
        "uptime": _get_uptime(),
        "disk_usage": _get_disk_usage(),
        "memory_usage": _get_memory_usage(),
        "cpu_load": _get_cpu_load(),
        "database_size": _get_database_size(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
    }


def _get_uptime():
    """Get server uptime from /proc/uptime (Linux) or fallback."""
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.read().split()[0])
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        return {
            "seconds": int(uptime_seconds),
            "formatted": "{0}d {1}h {2}m".format(days, hours, minutes),
        }
    except (FileNotFoundError, IOError, ValueError):
        # Fallback: try psutil or return unknown
        try:
            import psutil
            uptime_seconds = time.time() - psutil.boot_time()
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return {
                "seconds": int(uptime_seconds),
                "formatted": "{0}d {1}h {2}m".format(days, hours, minutes),
            }
        except ImportError:
            return {"seconds": 0, "formatted": "Unknown"}


def _get_disk_usage():
    """Get disk usage using os.statvfs (Linux/Mac) or fallback."""
    try:
        stat = os.statvfs("/")
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bavail * stat.f_frsize
        used = total - free
        usage_pct = round((used / total) * 100, 1) if total > 0 else 0

        return {
            "total_gb": round(total / (1024 ** 3), 2),
            "used_gb": round(used / (1024 ** 3), 2),
            "free_gb": round(free / (1024 ** 3), 2),
            "usage_percent": usage_pct,
        }
    except (OSError, AttributeError):
        try:
            import psutil
            disk = psutil.disk_usage("/")
            return {
                "total_gb": round(disk.total / (1024 ** 3), 2),
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "free_gb": round(disk.free / (1024 ** 3), 2),
                "usage_percent": disk.percent,
            }
        except ImportError:
            return {
                "total_gb": 0,
                "used_gb": 0,
                "free_gb": 0,
                "usage_percent": 0,
            }


def _get_memory_usage():
    """Get memory usage using /proc/meminfo (Linux) or fallback."""
    try:
        meminfo = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    meminfo[key] = int(parts[1])  # kB

        total = meminfo.get("MemTotal", 0)
        available = meminfo.get("MemAvailable", 0)
        used = total - available
        usage_pct = round((used / total) * 100, 1) if total > 0 else 0

        return {
            "total_gb": round(total / (1024 ** 2), 2),
            "used_gb": round(used / (1024 ** 2), 2),
            "available_gb": round(available / (1024 ** 2), 2),
            "usage_percent": usage_pct,
        }
    except (FileNotFoundError, IOError, ValueError):
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                "total_gb": round(mem.total / (1024 ** 3), 2),
                "used_gb": round(mem.used / (1024 ** 3), 2),
                "available_gb": round(mem.available / (1024 ** 3), 2),
                "usage_percent": mem.percent,
            }
        except ImportError:
            return {
                "total_gb": 0,
                "used_gb": 0,
                "available_gb": 0,
                "usage_percent": 0,
            }


def _get_cpu_load():
    """Get CPU load average using os.getloadavg (Linux/Mac) or fallback."""
    try:
        load1, load5, load15 = os.getloadavg()
        # Get CPU count for percentage
        cpu_count = os.cpu_count() or 1
        return {
            "load_1m": round(load1, 2),
            "load_5m": round(load5, 2),
            "load_15m": round(load15, 2),
            "cpu_count": cpu_count,
            "load_1m_percent": round((load1 / cpu_count) * 100, 1),
        }
    except (OSError, AttributeError):
        return {
            "load_1m": 0,
            "load_5m": 0,
            "load_15m": 0,
            "cpu_count": 1,
            "load_1m_percent": 0,
        }


def _get_database_size():
    """Get database size from MariaDB/MySQL."""
    try:
        db_name = frappe.conf.db_name
        if not db_name:
            return {"size_gb": 0, "size_mb": 0, "formatted": "Unknown"}

        result = frappe.db.sql(
            "SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024 / 1024, 2) AS size_gb "
            "FROM information_schema.tables WHERE table_schema = %s",
            (db_name,),
            as_dict=True,
        )

        size_gb = result[0].size_gb if result and result[0].size_gb else 0
        size_mb = round(size_gb * 1024, 2)

        return {
            "size_gb": size_gb,
            "size_mb": size_mb,
            "formatted": "{0} GB".format(size_gb) if size_gb >= 1 else "{0} MB".format(size_mb),
        }
    except Exception:
        return {"size_gb": 0, "size_mb": 0, "formatted": "Unknown"}


# =============================================================================
# Application Status
# =============================================================================

def _get_application_status():
    """Get application versions and status."""
    frappe_version = _get_app_version("frappe")
    erpnext_version = _get_app_version("erpnext")
    qalcuity_version = _get_app_version("qalcuity")

    return {
        "frappe_version": frappe_version,
        "erpnext_version": erpnext_version,
        "qalcuity_version": qalcuity_version,
        "site_name": frappe.conf.site_name or "Unknown",
        "last_migrate": _get_last_migrate_time(),
        "scheduler_status": _get_scheduler_status(),
    }


def _get_app_version(app_name):
    """Get installed app version."""
    try:
        version = frappe.get_attr(
            "{0}.__version__".format(app_name)
        )
        return str(version)
    except (AttributeError, ImportError):
        try:
            result = frappe.db.sql(
                "SELECT app_version FROM `tabModule Def` WHERE name = %s",
                (app_name.capitalize(),),
                as_dict=True,
            )
            if result:
                return result[0].app_version
        except Exception:
            pass
    return "Unknown"


def _get_last_migrate_time():
    """Get the last bench migrate timestamp."""
    try:
        result = frappe.db.sql(
            "SELECT MAX(modified) as last_modified FROM `tabSingles` "
            "WHERE doctype = 'System Settings'",
            as_dict=True,
        )
        if result and result[0].last_modified:
            return str(result[0].last_modified)
    except Exception:
        pass
    return "Unknown"


def _get_scheduler_status():
    """Check if scheduler is running by checking last scheduled task execution."""
    try:
        # Check if scheduler is active by looking at scheduled_items
        result = frappe.db.sql(
            "SELECT MAX(modified) as last_run FROM `tabScheduled Job Type` "
            "WHERE scheduled = 1",
            as_dict=True,
        )

        if result and result[0].last_run:
            last_run = result[0].last_run
            now = now_datetime()

            # Calculate time difference
            diff = (now - last_run).total_seconds()

            if diff < 3600:  # Less than 1 hour
                return {
                    "status": "Running",
                    "last_execution": str(last_run),
                    "seconds_ago": int(diff),
                }
            elif diff < 86400:  # Less than 1 day
                return {
                    "status": "Stale",
                    "last_execution": str(last_run),
                    "seconds_ago": int(diff),
                }
            else:
                return {
                    "status": "Not Running",
                    "last_execution": str(last_run),
                    "seconds_ago": int(diff),
                }

        return {"status": "Unknown", "last_execution": "N/A", "seconds_ago": 0}
    except Exception:
        return {"status": "Unknown", "last_execution": "N/A", "seconds_ago": 0}


# =============================================================================
# Activity Stats
# =============================================================================

def _get_activity_stats():
    """Get user activity and error statistics."""
    from frappe.utils import add_to_date, nowdate

    today = nowdate()
    yesterday = str(add_to_date(today, days=-1))

    return {
        "active_users_24h": _get_active_users_count(yesterday),
        "total_users": _get_total_users(),
        "total_sessions": _get_total_sessions(),
        "errors_today": _get_error_count(today),
        "errors_yesterday": _get_error_count(yesterday),
        "total_customers": _get_total_customers(),
        "total_subscriptions": _get_total_subscriptions(),
    }


def _get_active_users_count(since_date):
    """Get count of users active since a given date."""
    try:
        result = frappe.db.sql(
            "SELECT COUNT(DISTINCT name) as cnt FROM `tabUser` "
            "WHERE last_active >= %s AND name != 'Guest' AND name != 'Administrator'",
            (since_date,),
            as_dict=True,
        )
        return result[0].cnt if result else 0
    except Exception:
        return 0


def _get_total_users():
    """Get total non-guest users."""
    try:
        return frappe.db.count("User", {"name": ["not in", ["Guest", "Administrator", "All"]]})
    except Exception:
        return 0


def _get_total_sessions():
    """Get total active sessions."""
    try:
        # Frappe stores sessions in Redis, not directly in DB
        # We can estimate from User.last_active
        from frappe.utils import add_to_date, nowdate
        week_ago = str(add_to_date(nowdate(), days=-7))
        result = frappe.db.sql(
            "SELECT COUNT(*) as cnt FROM `tabUser` "
            "WHERE last_active >= %s AND name != 'Guest'",
            (week_ago,),
            as_dict=True,
        )
        return result[0].cnt if result else 0
    except Exception:
        return 0


def _get_error_count(date):
    """Get error log count for a specific date."""
    try:
        result = frappe.db.sql(
            "SELECT COUNT(*) as cnt FROM `tabError Log` "
            "WHERE creation >= %s AND creation < DATE_ADD(%s, INTERVAL 1 DAY)",
            (date, date),
            as_dict=True,
        )
        return result[0].cnt if result else 0
    except Exception:
        return 0


def _get_total_customers():
    """Get total customer count."""
    try:
        return frappe.db.count("Customer") or 0
    except Exception:
        return 0


def _get_total_subscriptions():
    """Get total active subscriptions."""
    try:
        return frappe.db.count(
            "Qalcuity Subscription",
            {"status": ["in", ["Active", "Grace Period"]]},
        ) or 0
    except Exception:
        return 0


# =============================================================================
# Health Checks
# =============================================================================

def _get_health_checks():
    """Run health checks on critical services."""
    return {
        "database": _check_database(),
        "redis": _check_redis(),
        "scheduler": _check_scheduler(),
    }


def _check_database():
    """Check database connectivity."""
    try:
        frappe.db.sql("SELECT 1")
        return {"status": "ok", "message": "Database connection successful"}
    except Exception as e:
        return {"status": "error", "message": "Database connection failed: {0}".format(str(e))}


def _check_redis():
    """Check Redis connectivity."""
    try:
        frappe.cache().set_value("_health_check", "ok", expires_in_sec=10)
        val = frappe.cache().get_value("_health_check")
        if val == "ok":
            return {"status": "ok", "message": "Redis connection successful"}
        return {"status": "error", "message": "Redis returned unexpected value"}
    except Exception as e:
        return {"status": "error", "message": "Redis connection failed: {0}".format(str(e))}


def _check_scheduler():
    """Check if scheduler is running."""
    try:
        result = frappe.db.sql(
            "SELECT MAX(modified) as last_run FROM `tabScheduled Job Type` "
            "WHERE scheduled = 1",
            as_dict=True,
        )

        if result and result[0].last_run:
            diff = (now_datetime() - result[0].last_run).total_seconds()
            if diff < 7200:  # Less than 2 hours
                return {"status": "ok", "message": "Scheduler is running"}
            else:
                return {
                    "status": "warning",
                    "message": "Scheduler may be stale (last run {0}s ago)".format(int(diff)),
                }

        return {"status": "warning", "message": "No scheduled jobs found"}
    except Exception as e:
        return {"status": "error", "message": "Scheduler check failed: {0}".format(str(e))}
