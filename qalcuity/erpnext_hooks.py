# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
ERPNext Tenant Isolation & Subscription Enforcement Hooks
==========================================================
Permission hooks untuk ERPNext DocTypes (Customer, Sales Invoice, dll).

1. Tenant Isolation: Customer portal user hanya bisa mengakses data miliknya sendiri.
2. Subscription Enforcement: Customer dengan subscription Expired/Suspended diblokir
   akses ke ERPNext features. Superadmin/Admin tetap bisa akses.

Digunakan oleh hooks.py sebagai get_permission_query_conditions dan has_permission
untuk ERPNext DocTypes.
"""

import frappe
from frappe import _

from qalcuity.qalcuity.isolation import (
    is_admin_user,
    get_customer_for_user,
    get_current_customer,
    get_current_tenant,
)


def _get_tenant_company(user):
    """
    Get the ERP Company name for the tenant linked to this user.

    Used for Company-based isolation layer on ERPNext DocTypes.
    Returns None if user has no tenant or tenant has no company.

    Args:
        user: User email/name

    Returns:
        str or None: Company name (erp_company field on Qalcuity Tenant)
    """
    if not user or user == "Guest":
        return None

    # Get customer for user
    customer = get_customer_for_user(user)
    if not customer:
        return None

    # Get tenant with erp_company
    company = frappe.db.get_value(
        "Qalcuity Tenant",
        {"customer": customer, "status": "Active"},
        "erp_company",
    )

    return company


# =============================================================================
# Subscription Enforcement Helper
# =============================================================================

def _has_active_subscription(user):
    """
    Cek apakah user memiliki subscription aktif atau dalam grace period.

    Rules:
    - Superadmin/Admin selalu diizinkan (bypass check)
    - Customer tanpa subscription → diblokir
    - Customer dengan subscription "Active" → diizinkan
    - Customer dengan subscription "Pending Payment" → diizinkan (masih dalam proses)
    - Customer dengan subscription "Expired" → diblokir
    - Customer dengan subscription "Suspended" → diblokir

    Args:
        user: User email/name

    Returns:
        bool: True jika user diizinkan mengakses ERPNext features
    """
    if not user or user == "Guest":
        return False

    # Admin bypass
    if is_admin_user(user):
        return True

    # Only enforce for Customer role
    if "Customer" not in frappe.get_roles(user):
        return True

    customer = get_customer_for_user(user)
    if not customer:
        return False

    # Get latest subscription for this customer
    sub = frappe.get_all(
        "Qalcuity Subscription",
        filters={"customer": customer},
        fields=["name", "status", "end_date"],
        order_by="creation desc",
        limit_page_length=1,
    )

    if not sub:
        # No subscription → blocked
        return False

    latest_sub = sub[0]

    # Active subscriptions are always allowed
    if latest_sub.status == "Active":
        return True

    # Pending Payment is allowed (customer is in the process of paying)
    if latest_sub.status == "Pending Payment":
        return True

    # Draft is allowed (subscription being set up)
    if latest_sub.status == "Draft":
        return True

    # Expired or Suspended → blocked
    if latest_sub.status in ("Expired", "Suspended"):
        return False

    return True


def _get_subscription_block_message(user):
    """
    Get a user-friendly message explaining why access is blocked.

    Args:
        user: User email/name

    Returns:
        str: Block message
    """
    customer = get_customer_for_user(user)
    if not customer:
        return _("No customer account found. Please contact administrator.")

    sub = frappe.get_all(
        "Qalcuity Subscription",
        filters={"customer": customer},
        fields=["name", "status", "end_date"],
        order_by="creation desc",
        limit_page_length=1,
    )

    if not sub:
        return _(
            "You don't have an active subscription. "
            "Please visit {0}/pricing to choose a plan."
        ).format(frappe.utils.get_url())

    latest_sub = sub[0]

    if latest_sub.status == "Expired":
        return _(
            "Your subscription has expired on {0}. "
            "Please renew your subscription to continue. "
            "Visit {1}/pricing to choose a plan."
        ).format(latest_sub.end_date, frappe.utils.get_url())

    if latest_sub.status == "Suspended":
        return _(
            "Your subscription has been suspended. "
            "Please contact administrator or renew your subscription."
        )

    return _("Access restricted. Please check your subscription status.")


# =============================================================================
# ERPNext DocType Permission Query Conditions
# =============================================================================

def get_customer_permission_query_conditions(user, doctype):
    """
    Permission query conditions untuk Customer DocType.

    Customer portal user hanya bisa melihat Customer record miliknya sendiri.
    Blocked jika subscription expired/suspended.

    Args:
        user: User yang sedang mengakses
        doctype: Nama DocType (selalu "Customer")

    Returns:
        str: SQL WHERE clause
    """
    if is_admin_user(user):
        return ""

    if not user or user == "Guest":
        return "1=0"

    if "Customer" not in frappe.get_roles(user):
        return ""

    # Subscription enforcement
    if not _has_active_subscription(user):
        return "1=0"

    customer = get_customer_for_user(user)
    if not customer:
        return "1=0"

    return f"(`tabCustomer`.name = {frappe.db.escape(customer)})"


def get_sales_order_permission_query_conditions(user, doctype):
    """
    Permission query conditions untuk Sales Order DocType.

    Customer portal user hanya bisa melihat Sales Order miliknya sendiri.
    Blocked jika subscription expired/suspended.
    Company-based filtering untuk ERPNext isolation layer.

    Args:
        user: User yang sedang mengakses
        doctype: Nama DocType (selalu "Sales Order")

    Returns:
        str: SQL WHERE clause
    """
    if is_admin_user(user):
        return ""

    if not user or user == "Guest":
        return "1=0"

    if "Customer" not in frappe.get_roles(user):
        return ""

    # Subscription enforcement
    if not _has_active_subscription(user):
        return "1=0"

    customer = get_customer_for_user(user)
    if not customer:
        return "1=0"

    # Build conditions: customer filter + optional company filter
    conditions = [f"`tabSales Order`.customer = {frappe.db.escape(customer)}"]

    company = _get_tenant_company(user)
    if company:
        conditions.append(f"`tabSales Order`.company = {frappe.db.escape(company)}")

    return "(" + " AND ".join(conditions) + ")"


def get_sales_invoice_permission_query_conditions(user, doctype):
    """
    Permission query conditions untuk Sales Invoice DocType.

    Customer portal user hanya bisa melihat Sales Invoice miliknya sendiri.
    Blocked jika subscription expired/suspended.
    Company-based filtering untuk ERPNext isolation layer.

    Args:
        user: User yang sedang mengakses
        doctype: Nama DocType (selalu "Sales Invoice")

    Returns:
        str: SQL WHERE clause
    """
    if is_admin_user(user):
        return ""

    if not user or user == "Guest":
        return "1=0"

    if "Customer" not in frappe.get_roles(user):
        return ""

    # Subscription enforcement
    if not _has_active_subscription(user):
        return "1=0"

    customer = get_customer_for_user(user)
    if not customer:
        return "1=0"

    # Build conditions: customer filter + optional company filter
    conditions = [f"`tabSales Invoice`.customer = {frappe.db.escape(customer)}"]

    company = _get_tenant_company(user)
    if company:
        conditions.append(f"`tabSales Invoice`.company = {frappe.db.escape(company)}")

    return "(" + " AND ".join(conditions) + ")"


def get_quotation_permission_query_conditions(user, doctype):
    """
    Permission query conditions untuk Quotation DocType.

    Customer portal user hanya bisa melihat Quotation miliknya sendiri.
    Blocked jika subscription expired/suspended.
    Company-based filtering untuk ERPNext isolation layer.

    Args:
        user: User yang sedang mengakses
        doctype: Nama DocType (selalu "Quotation")

    Returns:
        str: SQL WHERE clause
    """
    if is_admin_user(user):
        return ""

    if not user or user == "Guest":
        return "1=0"

    if "Customer" not in frappe.get_roles(user):
        return ""

    # Subscription enforcement
    if not _has_active_subscription(user):
        return "1=0"

    customer = get_customer_for_user(user)
    if not customer:
        return "1=0"

    # Build conditions: customer filter + optional company filter
    conditions = [f"`tabQuotation`.customer = {frappe.db.escape(customer)}"]

    company = _get_tenant_company(user)
    if company:
        conditions.append(f"`tabQuotation`.company = {frappe.db.escape(company)}")

    return "(" + " AND ".join(conditions) + ")"


def get_purchase_order_permission_query_conditions(user, doctype):
    """
    Permission query conditions untuk Purchase Order DocType.

    Customer portal user hanya bisa melihat Purchase Order miliknya sendiri.
    Blocked jika subscription expired/suspended.
    Company-based filtering untuk ERPNext isolation layer.

    Args:
        user: User yang sedang mengakses
        doctype: Nama DocType (selalu "Purchase Order")

    Returns:
        str: SQL WHERE clause
    """
    if is_admin_user(user):
        return ""

    if not user or user == "Guest":
        return "1=0"

    if "Customer" not in frappe.get_roles(user):
        return ""

    # Subscription enforcement
    if not _has_active_subscription(user):
        return "1=0"

    customer = get_customer_for_user(user)
    if not customer:
        return "1=0"

    # Build conditions: customer filter + optional company filter
    conditions = [f"`tabPurchase Order`.party_name = {frappe.db.escape(customer)}"]

    company = _get_tenant_company(user)
    if company:
        conditions.append(f"`tabPurchase Order`.company = {frappe.db.escape(company)}")

    return "(" + " AND ".join(conditions) + ")"


def get_purchase_invoice_permission_query_conditions(user, doctype):
    """
    Permission query conditions untuk Purchase Invoice DocType.

    Customer portal user hanya bisa melihat Purchase Invoice miliknya sendiri.
    Blocked jika subscription expired/suspended.
    Company-based filtering untuk ERPNext isolation layer.

    Args:
        user: User yang sedang mengakses
        doctype: Nama DocType (selalu "Purchase Invoice")

    Returns:
        str: SQL WHERE clause
    """
    if is_admin_user(user):
        return ""

    if not user or user == "Guest":
        return "1=0"

    if "Customer" not in frappe.get_roles(user):
        return ""

    # Subscription enforcement
    if not _has_active_subscription(user):
        return "1=0"

    customer = get_customer_for_user(user)
    if not customer:
        return "1=0"

    # Build conditions: customer filter + optional company filter
    conditions = [f"`tabPurchase Invoice`.party_name = {frappe.db.escape(customer)}"]

    company = _get_tenant_company(user)
    if company:
        conditions.append(f"`tabPurchase Invoice`.company = {frappe.db.escape(company)}")

    return "(" + " AND ".join(conditions) + ")"


# =============================================================================
# ERPNext DocType Has Permission (per-document check)
# =============================================================================

def has_customer_permission(doc, ptype, user=None):
    """
    Permission check untuk ERPNext Customer document.

    Customer portal user hanya bisa read Customer miliknya sendiri.
    Blocked jika subscription expired/suspended.

    Args:
        doc: Customer document
        ptype: Permission type
        user: User yang meminta akses

    Returns:
        bool: True jika diizinkan
    """
    if not user:
        user = frappe.session.user

    if is_admin_user(user):
        return True

    if not user or user == "Guest":
        return False

    if "Customer" not in frappe.get_roles(user):
        return True  # Bukan Customer role → biarkan Frappe handle

    # Subscription enforcement
    if not _has_active_subscription(user):
        return False

    customer = get_customer_for_user(user)
    if not customer:
        return False

    if ptype == "read":
        return doc.name == customer

    return False


def has_sales_order_permission(doc, ptype, user=None):
    """
    Permission check untuk ERPNext Sales Order document.

    Customer portal user hanya bisa read Sales Order miliknya sendiri.
    Blocked jika subscription expired/suspended.
    Company-based filtering untuk ERPNext isolation layer.

    Args:
        doc: Sales Order document
        ptype: Permission type
        user: User yang meminta akses

    Returns:
        bool: True jika diizinkan
    """
    if not user:
        user = frappe.session.user

    if is_admin_user(user):
        return True

    if not user or user == "Guest":
        return False

    if "Customer" not in frappe.get_roles(user):
        return True  # Bukan Customer role → biarkan Frappe handle

    # Subscription enforcement
    if not _has_active_subscription(user):
        return False

    customer = get_customer_for_user(user)
    if not customer:
        return False

    if ptype in ("read", "write"):
        # Check customer ownership
        if doc.customer != customer:
            return False

        # Check company ownership (second isolation layer)
        company = _get_tenant_company(user)
        if company and hasattr(doc, "company") and doc.company:
            return doc.company == company

        return True

    return False


def has_sales_invoice_permission(doc, ptype, user=None):
    """
    Permission check untuk ERPNext Sales Invoice document.

    Customer portal user hanya bisa read Sales Invoice miliknya sendiri.
    Blocked jika subscription expired/suspended.
    Company-based filtering untuk ERPNext isolation layer.

    Args:
        doc: Sales Invoice document
        ptype: Permission type
        user: User yang meminta akses

    Returns:
        bool: True jika diizinkan
    """
    if not user:
        user = frappe.session.user

    if is_admin_user(user):
        return True

    if not user or user == "Guest":
        return False

    if "Customer" not in frappe.get_roles(user):
        return True  # Bukan Customer role → biarkan Frappe handle

    # Subscription enforcement
    if not _has_active_subscription(user):
        return False

    customer = get_customer_for_user(user)
    if not customer:
        return False

    if ptype in ("read", "write"):
        # Check customer ownership
        if doc.customer != customer:
            return False

        # Check company ownership (second isolation layer)
        company = _get_tenant_company(user)
        if company and hasattr(doc, "company") and doc.company:
            return doc.company == company

        return True

    return False
