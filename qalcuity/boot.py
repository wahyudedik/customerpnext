"""
Qalcuity ERP — Boot Session Override

Injects Qalcuity branding into every desk session load.
This replaces the default Frappe/ERPNext app name, logo, and color
in the navbar and sidebar without modifying core files.
"""

import frappe


def boot_session(boot_obj):
    """Override boot session to set Qalcuity branding."""
    boot_obj.app_name = "Qalcuity ERP"
    boot_obj.app_slogan = "SaaS ERP Platform"

    # Logo paths — served from qalcuity public/images/
    boot_obj.app_logo = "/assets/qalcuity/images/logo-dark.png"
    boot_obj.app_logo_light = "/assets/qalcuity/images/logo-light.png"

    # App icon and color for navbar
    boot_obj.app_icon = "octicon octicon-zap"
    boot_obj.app_color = "#2490EF"

    return boot_obj
