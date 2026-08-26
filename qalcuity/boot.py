"""
Qalcuity ERP — Boot Session Override

Injects Qalcuity branding into every desk session load.
This replaces the default Frappe/ERPNext app name, logo, and color
in the navbar and sidebar without modifying core files.
"""

import frappe


def boot_session(boot_obj):
    """Override boot session to set Qalcuity branding."""
    try:
        boot_obj.app_name = "Qalcuity ERP"
        boot_obj.app_slogan = "SaaS ERP Platform"

        # Logo paths — served from qalcuity public/images/
        boot_obj.app_logo = "/assets/qalcuity/images/logo-dark.png"
        boot_obj.app_logo_light = "/assets/qalcuity/images/logo-light.png"

        # App icon and color for navbar
        boot_obj.app_icon = "octicon octicon-zap"
        boot_obj.app_color = "#2490EF"

        # Inject unread notification count for bell icon
        try:
            from qalcuity.api.notification import get_unread_count
            boot_obj.qalcuity_unread_notifications = get_unread_count().get("count", 0)
        except ImportError:
            frappe.logger().warning(
                "Qalcuity: notification module not available during boot"
            )
            boot_obj.qalcuity_unread_notifications = 0
        except Exception:
            boot_obj.qalcuity_unread_notifications = 0

    except Exception:
        # Critical: boot session must NEVER crash the desk.
        # If anything fails, just set minimal defaults.
        try:
            boot_obj.app_name = "Qalcuity ERP"
        except Exception:
            pass
        frappe.logger().error(
            "Qalcuity: boot_session failed — desk will load with defaults"
        )

    return boot_obj
