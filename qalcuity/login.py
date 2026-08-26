"""
Qalcuity ERP — Login Page Override

Customizes the login page to show Qalcuity branding
instead of the default Frappe/ERPNext branding.
"""

import frappe
from frappe import _


def login(context):
    """Custom login page context for Qalcuity branding."""
    context.brand_html = (
        '<div class="qalcuity-login-brand">'
        '<img src="/assets/qalcuity/images/logo-dark.png" '
        'class="qalcuity-login-logo-light" '
        'alt="Qalcuity ERP" '
        'style="height: 40px;">'
        '<img src="/assets/qalcuity/images/logo-light.png" '
        'class="qalcuity-login-logo-dark" '
        'alt="Qalcuity ERP" '
        'style="height: 40px; display: none;">'
        '</div>'
        '<script>'
        '(function() {'
        '  var theme = document.documentElement.getAttribute("data-theme")'
        '    || localStorage.getItem("frappe_theme")'
        '    || "light";'
        '  if (theme === "dark") {'
        '    document.querySelector(".qalcuity-login-logo-light").style.display = "none";'
        '    document.querySelector(".qalcuity-login-logo-dark").style.display = "block";'
        '  }'
        '})();'
        '</script>'
        '<style>'
        '  [data-theme="dark"] .qalcuity-login-logo-light { display: none !important; }'
        '  [data-theme="dark"] .qalcuity-login-logo-dark { display: block !important; }'
        '</style>'
        # Register & forgot password links — injected via JS after login form loads
        '<script>'
        '(function() {'
        '  function addLoginLinks() {'
        '    var pageCard = document.querySelector(".page-card");'
        '    if (!pageCard) return false;'
        '    var existing = document.querySelector(".qalcuity-login-links");'
        '    if (existing) return true;'
        '    var linkDiv = document.createElement("div");'
        '    linkDiv.className = "qalcuity-login-links";'
        '    linkDiv.innerHTML = '
        '      \'<div class="qalcuity-login-forgot-link">\''
        '      + \'<a href="/forgot-password" class="qalcuity-register-cta">Lupa password?</a>\''
        '      + \'</div>\''
        '      + \'<div class="qalcuity-login-register-link">\''
        '      + "<p>Belum punya akun? "'
        '      + \'<a href="/register" class="qalcuity-register-cta">Daftar di sini</a>\''
        '      + "</p>"'
        '      + \'</div>\';'
        '    pageCard.appendChild(linkDiv);'
        '    return true;'
        '  }'
        '  if (!addLoginLinks()) {'
        '    var observer = new MutationObserver(function() {'
        '      if (addLoginLinks()) observer.disconnect();'
        '    });'
        '    observer.observe(document.body, { childList: true, subtree: true });'
        '  }'
        '})();'
        '</script>'
    )
    context.title = "Qalcuity ERP - Login"
    context.no_header = True
    context.no_breadcrumbs = True


def log_login_attempt(user, status, ip_address=None, user_agent=None, login_method="Password", failure_reason=None):
    """Log login attempt ke Qalcuity Login Log.

    Args:
        user: Username yang mencoba login
        status: Success | Failed | Blocked
        ip_address: IP address client
        user_agent: Browser/OS info
        login_method: Password | 2FA | Backup Code | API Key
        failure_reason: Alasan kegagalan (jika gagal)
    """
    try:
        # Get customer via Portal User
        customer = frappe.db.get_value("Portal User", {"user": user}, "parent")

        # Get IP from request if not provided
        if not ip_address:
            ip_address = frappe.local.request_ip if hasattr(frappe.local, "request_ip") else None
        if not ip_address:
            try:
                ip_address = frappe.get_request_header("X-Forwarded-For") or frappe.get_request_header("Remote-Addr")
            except Exception:
                ip_address = None

        # Get user agent from request if not provided
        if not user_agent:
            try:
                user_agent = frappe.get_request_header("User-Agent")
            except Exception:
                user_agent = None

        # Get session ID if login was successful
        session_id = None
        if status == "Success":
            try:
                session_id = frappe.session.sid
            except Exception:
                pass

        frappe.get_doc({
            "doctype": "Qalcuity Login Log",
            "user": user,
            "customer": customer or None,
            "status": status,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "login_method": login_method,
            "failure_reason": failure_reason,
            "session_id": session_id,
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        pass  # Jangan crash jika logging gagal


def on_login_complete(login_manager):
    """Hook setelah login selesai — log login attempt.

    Registered via hooks.py: login_manager_complete
    """
    user = login_manager.user
    status = "Success" if login_manager.user != "Guest" else "Failed"
    log_login_attempt(
        user=user,
        status=status,
        login_method="Password",
    )
