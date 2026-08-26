# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Session Management API for Qalcuity ERP.
Provides endpoints for viewing and managing active sessions.
"""

import frappe
from frappe import _
import re
import json


# =============================================================================
# User Agent Parser
# =============================================================================

def _parse_user_agent(user_agent):
    """Parse user agent string to extract device and browser info.

    Args:
        user_agent: Raw User-Agent string

    Returns:
        dict: Parsed device info with browser, os, device_type
    """
    if not user_agent:
        return {
            "browser": "Unknown",
            "os": "Unknown",
            "device_type": "Desktop",
            "display": "Unknown Browser on Unknown OS",
        }

    ua = user_agent

    # --- Browser Detection ---
    browser = "Unknown"
    if "Edg/" in ua:
        browser = "Microsoft Edge"
    elif "OPR/" in ua or "Opera/" in ua:
        browser = "Opera"
    elif "Chrome/" in ua and "Safari/" in ua:
        browser = "Chrome"
    elif "Firefox/" in ua:
        browser = "Firefox"
    elif "Safari/" in ua and "Chrome/" not in ua:
        browser = "Safari"
    elif "MSIE" in ua or "Trident/" in ua:
        browser = "Internet Explorer"

    # --- OS Detection ---
    os_name = "Unknown"
    if "Windows NT 10" in ua:
        os_name = "Windows 10/11"
    elif "Windows NT 6.3" in ua:
        os_name = "Windows 8.1"
    elif "Windows NT 6.2" in ua:
        os_name = "Windows 8"
    elif "Windows NT 6.1" in ua:
        os_name = "Windows 7"
    elif "Windows" in ua:
        os_name = "Windows"
    elif "Mac OS X" in ua:
        os_name = "macOS"
    elif "Linux" in ua and "Android" not in ua:
        os_name = "Linux"
    elif "Android" in ua:
        os_name = "Android"
    elif "iPhone" in ua or "iPad" in ua:
        os_name = "iOS"

    # --- Device Type ---
    device_type = "Desktop"
    if "Mobile" in ua or "Android" in ua and "Mobile" in ua:
        device_type = "Mobile"
    elif "iPad" in ua or "Tablet" in ua:
        device_type = "Tablet"
    elif "iPhone" in ua:
        device_type = "Mobile"

    display = f"{browser} on {os_name}"
    if device_type != "Desktop":
        display = f"{browser} on {device_type} ({os_name})"

    return {
        "browser": browser,
        "os": os_name,
        "device_type": device_type,
        "display": display,
    }


def _get_browser_icon(browser):
    """Get octicon icon name for browser.

    Args:
        browser: Browser name

    Returns:
        str: Octicon icon name
    """
    icons = {
        "Chrome": "octicon-device-desktop",
        "Firefox": "octicon-device-desktop",
        "Safari": "octicon-device-desktop",
        "Microsoft Edge": "octicon-device-desktop",
        "Opera": "octicon-device-desktop",
        "Internet Explorer": "octicon-device-desktop",
    }
    return icons.get(browser, "octicon-device-desktop")


# =============================================================================
# API: Get Active Sessions
# =============================================================================

@frappe.whitelist()
def get_active_sessions():
    """Get all active sessions for the currently logged-in user.

    Returns:
        dict: List of active sessions with device info
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Silakan login untuk melihat sesi aktif."))

    # Query sessions from tabSession
    sessions = frappe.db.sql(
        """
        SELECT name, user, lastupdate, sessiondata, ipaddress
        FROM tabSession
        WHERE user = %s
        ORDER BY lastupdate DESC
        """,
        (user,),
        as_dict=True,
    )

    current_sid = frappe.session.sid
    result = []

    for session in sessions:
        # Parse user agent from sessiondata
        session_data = {}
        if session.sessiondata:
            try:
                if isinstance(session.sessiondata, str):
                    session_data = json.loads(session.sessiondata)
                elif isinstance(session.sessiondata, dict):
                    session_data = session.sessiondata
            except (json.JSONDecodeError, TypeError):
                session_data = {}

        user_agent = session_data.get("user_agent", "")
        device_info = _parse_user_agent(user_agent)

        # Determine if this is the current session
        is_current = session.name == current_sid

        result.append({
            "session_id": session.name,
            "last_active": str(session.lastupdate) if session.lastupdate else None,
            "ip_address": session.ipaddress or "Unknown",
            "browser": device_info["browser"],
            "os": device_info["os"],
            "device_type": device_info["device_type"],
            "display": device_info["display"],
            "is_current": is_current,
            "icon": _get_browser_icon(device_info["browser"]),
        })

    return {
        "sessions": result,
        "total": len(result),
        "current_sid": current_sid,
    }


# =============================================================================
# API: Force Logout Session
# =============================================================================

@frappe.whitelist()
def force_logout_session(session_id):
    """Force logout a specific session.

    Args:
        session_id: Session ID to logout

    Returns:
        dict: Success status
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Silakan login untuk mengelola sesi."))

    if not session_id:
        frappe.throw(_("Session ID harus diisi."))

    # Verify the session belongs to the current user
    session_user = frappe.db.get_value("TabSession", session_id, "user")
    if session_user != user:
        frappe.throw(_("Sesi ini bukan milik Anda."))

    # Don't allow forcing own current session
    current_sid = frappe.session.sid
    if session_id == current_sid:
        frappe.throw(_("Tidak bisa logout sesi aktif saat ini. Gunakan tombol Keluar."))

    # Delete the session
    frappe.db.delete("TabSession", session_id)
    frappe.db.commit()

    return {
        "success": True,
        "message": _("Sesi berhasil dihapus."),
    }


# =============================================================================
# API: Force Logout All Sessions
# =============================================================================

@frappe.whitelist()
def force_logout_all_sessions():
    """Force logout all sessions except the current one.

    Returns:
        dict: Success status with count
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Silakan login untuk mengelola sesi."))

    current_sid = frappe.session.sid

    # Count sessions to delete
    count = frappe.db.sql(
        "SELECT COUNT(*) FROM tabSession WHERE user = %s AND name != %s",
        (user, current_sid),
    )[0][0]

    # Delete all sessions except current
    frappe.db.sql(
        "DELETE FROM tabSession WHERE user = %s AND name != %s",
        (user, current_sid),
    )
    frappe.db.commit()

    return {
        "success": True,
        "message": _("{0} sesi berhasil dihapus.").format(count),
        "deleted_count": count,
    }
