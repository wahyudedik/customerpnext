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
app_include_css = [
    "/assets/qalcuity/css/qalcuity.css",
    "/assets/qalcuity/css/qalcuity-admin.css",
]
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
# Website Context — override ERPNext website branding defaults
# =============================================================================
website_context = {
    "favicon": "/assets/qalcuity/images/logo-dark.png",
    "splash_image": "/assets/qalcuity/images/logo-dark.png",
    "app_name": "Qalcuity ERP",
    "app_logo": "/assets/qalcuity/images/logo-dark.png",
}

# =============================================================================
# Website Script — inject JS/CSS into ALL website pages (including login)
# =============================================================================
website_script = "qalcuity.qalcuity.website_script.get_website_script"

# =============================================================================
# Doc Events — Audit Log & Lifecycle Hooks
# =============================================================================
doc_events = {
    "Customer": {
        "after_insert": "qalcuity.api.customer.after_customer_insert",
    },
    "Qalcuity Payment": {
        "on_update": "qalcuity.api.audit.on_payment_update",
    },
    "Qalcuity Subscription": {
        "on_update": "qalcuity.api.audit.on_subscription_update",
    },
    "User": {
        "before_insert": "qalcuity.enforcement.before_user_insert",
    },
}

# =============================================================================
# Permissions — has_permission (per-document access check)
# =============================================================================
has_permission = {
    "Qalcuity Plan": "qalcuity.qalcuity.doctype.qalcuity_plan.qalcuity_plan.has_permission",
    "Qalcuity Subscription": "qalcuity.qalcuity.doctype.qalcuity_subscription.qalcuity_subscription.has_permission",
    "Qalcuity Payment": "qalcuity.qalcuity.doctype.qalcuity_payment.qalcuity_payment.has_permission",
    "Qalcuity Tenant": "qalcuity.qalcuity.doctype.qalcuity_tenant.qalcuity_tenant.has_permission",
    "Qalcuity Notification": "qalcuity.qalcuity.doctype.qalcuity_notification.qalcuity_notification.has_permission",
    "Qalcuity Plan Change": "qalcuity.qalcuity.doctype.qalcuity_plan_change.qalcuity_plan_change.has_permission",
    # ERPNext DocTypes — tenant isolation
    "Customer": "qalcuity.qalcuity.erpnext_hooks.has_customer_permission",
    "Sales Order": "qalcuity.qalcuity.erpnext_hooks.has_sales_order_permission",
    "Sales Invoice": "qalcuity.qalcuity.erpnext_hooks.has_sales_invoice_permission",
}

# =============================================================================
# Permissions — get_permission_query_conditions (list view filtering)
# =============================================================================
get_permission_query_conditions = {
    # Qalcuity DocTypes — tenant isolation via customer field
    "Qalcuity Subscription": "qalcuity.qalcuity.isolation.get_permission_query_conditions",
    "Qalcuity Payment": "qalcuity.qalcuity.isolation.get_permission_query_conditions",
    "Qalcuity Tenant": "qalcuity.qalcuity.isolation.get_permission_query_conditions",
    "Qalcuity Plan Change": "qalcuity.qalcuity.isolation.get_permission_query_conditions",
    # ERPNext DocTypes — tenant isolation via customer field
    "Customer": "qalcuity.qalcuity.erpnext_hooks.get_customer_permission_query_conditions",
    "Sales Order": "qalcuity.qalcuity.erpnext_hooks.get_sales_order_permission_query_conditions",
    "Sales Invoice": "qalcuity.qalcuity.erpnext_hooks.get_sales_invoice_permission_query_conditions",
    "Quotation": "qalcuity.qalcuity.erpnext_hooks.get_quotation_permission_query_conditions",
}

# =============================================================================
# Website Route Rules
# =============================================================================
website_route_rules = [
    {
        "from_route": "/pricing",
        "to_route": "pricing",
    },
    {
        "from_route": "/register",
        "to_route": "register",
    },
    {
        "from_route": "/checkout",
        "to_route": "checkout",
    },
    {
        "from_route": "/my-payments",
        "to_route": "my-payments",
    },
    {
        "from_route": "/dashboard",
        "to_route": "dashboard",
    },
    {
        "from_route": "/admin-reviews",
        "to_route": "admin-reviews",
    },
    {
        "from_route": "/admin-dashboard",
        "to_route": "admin-dashboard",
    },
    {
        "from_route": "/profile",
        "to_route": "profile",
    },
    {
        "from_route": "/account-status",
        "to_route": "account-status",
    },
    {
        "from_route": "/subscription-history",
        "to_route": "subscription-history",
    },
    {
        "from_route": "/2fa-setup",
        "to_route": "2fa-setup",
    },
    {
        "from_route": "/2fa-verify",
        "to_route": "2fa-verify",
    },
    {
        "from_route": "/sessions",
        "to_route": "sessions",
    },
    {
        "from_route": "/admin-health",
        "to_route": "admin-health",
    },
    {
        "from_route": "/plan-change",
        "to_route": "plan-change",
    },
]

# =============================================================================
# Fixtures — exported data for seeding and property overrides
# =============================================================================
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            ["module", "=", "Qalcuity"],
            ["dt", "!=", "Qalcuity Notification"],
        ],
    },
    {
        "dt": "Property Setter",
        "filters": [
            ["name", "in", [
                "Website Settings-app_name",
                "Website Settings-app_logo",
                "Website Settings-favicon",
                "Website Settings-splash_image",
                "System Settings-setup_wizard_completed",
            ]],
        ],
    },
    {
        "dt": "Role",
        "filters": [["role_name", "in", ["Qalcuity Superadmin", "Qalcuity Admin", "Qalcuity ERP User"]]],
    },
    {
        "dt": "Workspace",
        "filters": [["name", "=", "Qalcuity ERP Customer"]],
    },
    {
        "dt": "Qalcuity Plan",
        "filters": [["is_active", "=", 1]],
    },
    {
        "dt": "Qalcuity Bank Account",
        "filters": [],
    },
    {
        "dt": "Qalcuity Settings",
        "filters": [],
    },
    {
        "dt": "Qalcuity Plan Module",
        "filters": [],
    },
]

# =============================================================================
# Scheduler
# =============================================================================
scheduler_events = {
    "daily": [
        "qalcuity.tasks.check_subscription_expiry",
        "qalcuity.tasks.run_scheduled_backup",
        "qalcuity.tasks.retry_failed_provisioning",
    ],
}

# =============================================================================
# Setup Wizard
# =============================================================================
setup_wizard_app_icon = "icon_qalcuity"
setup_wizard_theme = "#2490EF"
setup_wizard_roles = [{"role": "Qalcuity Superadmin"}]
