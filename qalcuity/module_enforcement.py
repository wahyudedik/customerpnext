# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity ERP Module Enforcement Module
========================================
Enforce modul ERPNext berdasarkan subscription plan.

Setiap plan bisa dikonfigurasi ERPNext modules apa saja yang diakses.
Jika plan tidak mengaktifkan suatu module, customer akan diblokir aksesnya.

Module Mapping:
- Accounting → Sales Invoice, Purchase Invoice, Journal Entry, GL Entry, dll.
- CRM → Lead, Opportunity, Communication
- Sales → Sales Order, Quotation, Sales Invoice
- Purchasing → Purchase Order, Purchase Invoice, Supplier
- Inventory → Stock Entry, Stock Ledger, Item, Warehouse
- Projects → Project, Task, Timesheet
- HR → Employee, Attendance, Leave, Payroll
- Manufacturing → BOM, Work Order, Job Card
- Support → Issue, Activity Type
- Assets → Asset, Asset Movement, Asset Depreciation
"""

import frappe
from frappe import _

# =============================================================================
# ERPNext Module to DocType Mapping
# =============================================================================
# Mapping dari module name (yang ada di Qalcuity Plan Module) ke
# daftar ERPNext DocTypes yang termasuk dalam module tersebut.
# Digunakan untuk block akses ke DocType tertentu berdasarkan plan.

MODULE_DOCTYPE_MAP = {
    "Accounting": [
        "Journal Entry",
        "GL Entry",
        "Payment Entry",
        "Payment Reconciliation",
        "Cost Center",
        "Budget",
        "Fiscal Year",
        "Account",
        "Mode of Payment",
    ],
    "CRM": [
        "Lead",
        "Opportunity",
        "CRM Note",
        "Communication",
    ],
    "Sales": [
        "Sales Order",
        "Sales Invoice",
        "Quotation",
        "Customer",
        "Sales Partner",
        "Sales Analytics",
    ],
    "Purchasing": [
        "Purchase Order",
        "Purchase Invoice",
        "Purchase Receipt",
        "Supplier",
        "Purchase Analytics",
    ],
    "Inventory": [
        "Item",
        "Item Group",
        "Warehouse",
        "Stock Entry",
        "Stock Ledger Entry",
        "Stock Reconciliation",
        "Delivery Note",
        "Purchase Receipt",
        "Batch",
        "Serial No",
    ],
    "Projects": [
        "Project",
        "Task",
        "Timesheet",
        "Activity Type",
        "Project Type",
    ],
    "HR": [
        "Employee",
        "Attendance",
        "Leave Application",
        "Leave Allocation",
        "Payroll Entry",
        "Salary Slip",
        "Department",
        "Designation",
    ],
    "Manufacturing": [
        "BOM",
        "Work Order",
        "Job Card",
        "Production Plan",
        "Manufacturing Settings",
    ],
    "Support": [
        "Issue",
        "Activity Type",
    ],
    "Assets": [
        "Asset",
        "Asset Category",
        "Asset Movement",
        "Asset Depreciation Schedule",
    ],
}

# Reverse mapping: DocType → Module name
_DOCTYPE_MODULE_MAP = None


def _get_doctype_module_map():
    """Build reverse mapping: DocType → Module name."""
    global _DOCTYPE_MODULE_MAP
    if _DOCTYPE_MODULE_MAP is None:
        _DOCTYPE_MODULE_MAP = {}
        for module_name, doctypes in MODULE_DOCTYPE_MAP.items():
            for dt in doctypes:
                _DOCTYPE_MODULE_MAP[dt] = module_name
    return _DOCTYPE_MODULE_MAP


def get_user_enabled_modules(user=None):
    """
    Get list of enabled module names for a user based on their subscription plan.

    Args:
        user: User email/name. Default: frappe.session.user

    Returns:
        list: List of enabled module names, or None if all modules are enabled.
              None means no restriction (admin user or no plan limitation).
    """
    if not user:
        user = frappe.session.user

    if not user or user == "Guest":
        return None

    # Admin users bypass module restrictions
    from qalcuity.isolation import is_admin_user
    if is_admin_user(user):
        return None

    # Only enforce for Customer role
    if "Customer" not in frappe.get_roles(user):
        return None

    from qalcuity.isolation import get_customer_for_user
    customer = get_customer_for_user(user)
    if not customer:
        return None

    # Get latest active subscription
    sub = frappe.get_all(
        "Qalcuity Subscription",
        filters={"customer": customer},
        fields=["name", "plan", "status"],
        order_by="creation desc",
        limit_page_length=1,
    )

    if not sub:
        return None

    latest_sub = sub[0]
    if latest_sub.status not in ("Active", "Grace Period", "Pending Payment", "Draft"):
        return None

    if not latest_sub.plan:
        return None

    # Get enabled modules from plan
    plan_doc = frappe.get_doc("Qalcuity Plan", latest_sub.plan)
    if not plan_doc.enabled_modules or len(plan_doc.enabled_modules) == 0:
        # No modules configured → all modules enabled
        return None

    return [row.module_name for row in plan_doc.enabled_modules]


def is_module_enabled_for_user(module_name, user=None):
    """
    Check if a specific ERPNext module is enabled for a user's plan.

    Args:
        module_name: Module name (e.g., "Accounting", "Sales", "CRM")
        user: User email/name. Default: frappe.session.user

    Returns:
        bool: True if module is enabled (or no restriction), False if blocked
    """
    enabled_modules = get_user_enabled_modules(user)
    if enabled_modules is None:
        return True  # No restriction

    return module_name in enabled_modules


def is_doctype_enabled_for_user(doctype_name, user=None):
    """
    Check if a specific ERPNext DocType is enabled for a user's plan.

    Args:
        doctype_name: ERPNext DocType name
        user: User email/name. Default: frappe.session.user

    Returns:
        bool: True if DocType is enabled (or no restriction), False if blocked
    """
    enabled_modules = get_user_enabled_modules(user)
    if enabled_modules is None:
        return True  # No restriction

    # Map DocType to module
    doctype_module_map = _get_doctype_module_map()
    module_name = doctype_module_map.get(doctype_name)

    if not module_name:
        # DocType not in our mapping → allow access (unknown DocType)
        return True

    return module_name in enabled_modules


def get_module_block_message(doctype_name, user=None):
    """
    Get a user-friendly message explaining why access is blocked due to plan restrictions.

    Args:
        doctype_name: ERPNext DocType name
        user: User email/name. Default: frappe.session.user

    Returns:
        str: Block message with upgrade suggestion
    """
    doctype_module_map = _get_doctype_module_map()
    module_name = doctype_module_map.get(doctype_name, "this module")

    return _(
        "The {0} module is not available in your current subscription plan. "
        "Please upgrade your plan to access this feature. "
        "Visit {1}/pricing to view available plans."
    ).format(module_name, frappe.utils.get_url())


def get_enabled_modules_for_plan(plan_name):
    """
    Get enabled modules list for a specific plan.

    Args:
        plan_name: Qalcuity Plan name

    Returns:
        list: List of enabled module names, or empty list if all modules enabled
    """
    plan_doc = frappe.get_doc("Qalcuity Plan", plan_name)
    if not plan_doc.enabled_modules or len(plan_doc.enabled_modules) == 0:
        return []  # Empty = all modules enabled

    return [row.module_name for row in plan_doc.enabled_modules]
