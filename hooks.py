from frappe import _

# =============================================================================
# Qalcuity ERP — App Branding
# =============================================================================
app_name = "qalcuity"
app_title = "Qalcuity ERP"
app_publisher = "Qalcuity"
app_description = "Qalcuity ERP - SaaS ERP Platform"
app_version = "0.0.1"
app_color = "#2490EF"
app_icon = "octicon octicon-zap"
app_email = "info@qalcuity.com"
app_license = "MIT"

# =============================================================================
# Includes — CSS & JS for branding and custom styles
# =============================================================================
app_include_css = "/assets/qalcuity/css/qalcuity.css"
app_include_js = "/assets/qalcuity/js/qalcuity.js"
app_include_brand_html = True

# =============================================================================
# Boot Session Override — set Qalcuity branding on every desk load
# =============================================================================
override_boot_session = "qalcuity.qalcuity.boot.boot_session"

# =============================================================================
# Login Page Override — custom login page branding
# =============================================================================
override_website_page_render_context = {
    "login": "qalcuity.qalcuity.login.login",
}

# =============================================================================
# Doc Events
# =============================================================================
doc_events = {
    "Customer": {
        "after_insert": "qalcuity.api.customer.after_customer_insert",
    },
}

# =============================================================================
# Permissions
# =============================================================================
has_permission = {
    "Qalcuity Plan": "qalcuity.qalcuity.doctype.qalcuity_plan.qalcuity_plan.has_permission",
    "Qalcuity Subscription": "qalcuity.qalcuity.doctype.qalcuity_subscription.qalcuity_subscription.has_permission",
    "Qalcuity Payment": "qalcuity.qalcuity.doctype.qalcuity_payment.qalcuity_payment.has_permission",
    "Qalcuity Tenant": "qalcuity.qalcuity.doctype.qalcuity_tenant.qalcuity_tenant.has_permission",
}

# =============================================================================
# Website Route Rules
# =============================================================================
website_route_rules = [
    {
        "from_route": "/pricing",
        "to_route": "pricing",
    },
]

# =============================================================================
# Fixtures — exported data for seeding and property overrides
# =============================================================================
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [["module", "=", "Qalcuity"]],
    },
    {
        "dt": "Property Setter",
        "filters": [
            ["name", "in", [
                "Website Settings-app_name",
                "Website Settings-app_logo",
                "System Settings-setup_wizard_completed",
            ]],
        ],
    },
    {
        "dt": "Role",
        "filters": [["role_name", "in", ["Qalcuity Superadmin", "Qalcuity Admin"]]],
    },
    {
        "dt": "Qalcuity Plan",
        "filters": [["is_active", "=", 1]],
    },
    {
        "dt": "Qalcuity Settings",
        "filters": [],
    },
]

# =============================================================================
# Scheduler
# =============================================================================
scheduler_events = {
    "daily": [
        "qalcuity.tasks.check_subscription_expiry",
    ],
}

# =============================================================================
# Override Whitelisted Methods
# =============================================================================
override_whitelisted_methods = {
    "qalcuity.api.payment.submit_payment": "qalcuity.api.payment.submit_payment",
    "qalcuity.api.payment.approve_payment": "qalcuity.api.payment.approve_payment",
    "qalcuity.api.payment.reject_payment": "qalcuity.api.payment.reject_payment",
}

# =============================================================================
# Setup Wizard
# =============================================================================
setup_wizard_app_icon = "icon_qalcuity"
setup_wizard_theme = "#2490EF"
setup_wizard_roles = [{"role": "Qalcuity Superadmin"}]
