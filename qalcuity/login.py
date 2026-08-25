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
