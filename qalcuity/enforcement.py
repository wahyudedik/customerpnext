# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity Plan Limits Enforcement Module
==========================================
Enforce batasan plan pada tenant/customer.

Functions:
- check_user_limit(tenant) — cek apakah tenant masih dalam batas max_users
- check_storage_limit(tenant) — cek apakah tenant masih dalam batas max_storage_gb
- enforce_limits() — callable dari hooks untuk memblokir operasi yang melampaui batas
"""

import frappe
from frappe import _


def check_user_limit(tenant_name):
    """
    Cek apakah tenant masih dalam batas max_users dari plan.

    Args:
        tenant_name: Nama/ID Qalcuity Tenant

    Returns:
        dict: {
            "allowed": bool,
            "current": int,
            "max": int,
            "message": str
        }
    """
    tenant = frappe.get_doc("Qalcuity Tenant", tenant_name)
    customer = tenant.customer

    # Dapatkan plan dari subscription
    subscription_name = frappe.db.get_value(
        "Qalcuity Subscription",
        {"customer": customer, "status": ["in", ["Active", "Grace Period", "Pending Payment"]]},
        "name",
    )

    if not subscription_name:
        # Tidak ada subscription aktif — izinkan (default)
        return {
            "allowed": True,
            "current": 0,
            "max": 0,
            "message": "No active subscription found.",
        }

    plan_name = frappe.db.get_value("Qalcuity Subscription", subscription_name, "plan")
    if not plan_name:
        return {
            "allowed": True,
            "current": 0,
            "max": 0,
            "message": "No plan linked to subscription.",
        }

    plan = frappe.get_doc("Qalcuity Plan", plan_name)
    max_users = plan.max_users or 0

    if max_users <= 0:
        # Unlimited
        return {
            "allowed": True,
            "current": 0,
            "max": 0,
            "message": "Unlimited users.",
        }

    # Hitung jumlah user aktif untuk customer ini
    # User dihitung dari Portal User yang terkait dengan Customer
    current_users = frappe.db.sql(
        """
        SELECT COUNT(*)
        FROM `tabPortal User` pu
        WHERE pu.parenttype = 'Customer'
          AND pu.parent = %s
        """,
        (customer,),
    )[0][0]

    allowed = current_users < max_users

    message = ""
    if not allowed:
        message = _(
            "User limit reached. Your {0} plan allows maximum {1} users. "
            "Current users: {2}. Please upgrade your plan to add more users."
        ).format(plan_name, max_users, current_users)

    return {
        "allowed": allowed,
        "current": current_users,
        "max": max_users,
        "message": message,
    }


def check_storage_limit(tenant_name):
    """
    Cek apakah tenant masih dalam batas max_storage_gb dari plan.

    Args:
        tenant_name: Nama/ID Qalcuity Tenant

    Returns:
        dict: {
            "allowed": bool,
            "current": float,
            "max": int,
            "message": str
        }
    """
    tenant = frappe.get_doc("Qalcuity Tenant", tenant_name)
    customer = tenant.customer

    subscription_name = frappe.db.get_value(
        "Qalcuity Subscription",
        {"customer": customer, "status": ["in", ["Active", "Grace Period"]]},
        "name",
    )

    if not subscription_name:
        return {
            "allowed": True,
            "current": 0.0,
            "max": 0,
            "message": "No active subscription found.",
        }

    plan_name = frappe.db.get_value("Qalcuity Subscription", subscription_name, "plan")
    if not plan_name:
        return {
            "allowed": True,
            "current": 0.0,
            "max": 0,
            "message": "No plan linked to subscription.",
        }

    plan = frappe.get_doc("Qalcuity Plan", plan_name)
    max_storage_gb = plan.max_storage_gb or 0

    if max_storage_gb <= 0:
        return {
            "allowed": True,
            "current": 0.0,
            "max": 0,
            "message": "Unlimited storage.",
        }

    current_storage = tenant.storage_used_gb or 0.0
    allowed = current_storage < max_storage_gb

    message = ""
    if not allowed:
        message = _(
            "Storage limit reached. Your {0} plan allows maximum {1} GB. "
            "Current usage: {2} GB. Please upgrade your plan or free up storage."
        ).format(plan_name, max_storage_gb, current_storage)

    return {
        "allowed": allowed,
        "current": current_storage,
        "max": max_storage_gb,
        "message": message,
    }


def enforce_user_limit_for_customer(customer_name):
    """
    Enforce user limit saat user baru akan ditambahkan ke customer.

    Args:
        customer_name: Nama Customer

    Returns:
        bool: True jika allowed, frappe.throw jika tidak
    """
    tenant_name = frappe.db.get_value(
        "Qalcuity Tenant",
        {"customer": customer_name},
        "name",
    )

    if not tenant_name:
        # Tidak ada tenant — izinkan (registration flow)
        return True

    result = check_user_limit(tenant_name)

    if not result["allowed"]:
        frappe.throw(result["message"])

    return True


def before_user_insert(doc, method):
    """
    Hook: User before_insert.
    Cek user limit sebelum user baru dibuat.
    Dipanggil dari hooks.py doc_events.
    """
    # Skip untuk Administrator atau system-initiated user creation
    if frappe.session.user == "Administrator":
        return

    # Cari customer yang terkait dengan user yang sedang login
    from qalcuity.qalcuity.isolation import get_current_customer

    customer = get_current_customer()
    if not customer:
        # Bukan customer — skip enforcement
        return

    enforce_user_limit_for_customer(customer)


def enforce_limits():
    """
    Callable dari hooks untuk memblokir operasi yang melampaui batas.
    Dipanggil sebelum user baru ditambahkan.
    """
    # Ini adalah wrapper untuk hook integration
    # Actual enforcement dilakukan di enforce_user_limit_for_customer
    pass
