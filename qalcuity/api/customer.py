# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Customer API hooks for Qalcuity ERP.
Handles customer-related events.
"""

import frappe
from frappe import _


def after_customer_insert(doc, method):
    """
    Hook: After a new Customer is created in ERPNext.
    Automatically create a Qalcuity Tenant for the new customer.

    Tenant provisioning dilakukan SETIAP kali Customer baru dibuat,
    tidak hanya saat trial period aktif. Tenant adalah unit isolasi
    dasar dalam arsitektur multi-tenancy Qalcuity.

    Args:
        doc: Customer document
        method: Event method name
    """
    try:
        # Check if Qalcuity Settings exists
        if not frappe.db.exists("Qalcuity Settings"):
            return

        # Check if tenant already exists untuk customer ini
        if frappe.db.exists("Qalcuity Tenant", {"customer": doc.name}):
            return

        # Create tenant — selalu provisioning untuk setiap customer baru
        tenant = frappe.get_doc(
            {
                "doctype": "Qalcuity Tenant",
                "customer": doc.name,
                "status": "Active",
            }
        )
        tenant.insert(ignore_permissions=True)

        frappe.msgprint(
            _("Tenant provisioned for customer {0}.").format(doc.customer_name),
            indicator="green",
            alert=True,
        )

        # Clear isolation cache untuk user yang terkait customer ini
        _clear_customer_user_cache(doc.name)

    except Exception:
        frappe.log_error(
            title="Qalcuity: Failed to provision tenant for customer {0}".format(
                doc.name
            )
        )


def _clear_customer_user_cache(customer_name):
    """
    Clear isolation cache untuk user yang terkait dengan customer.

    Dipanggil setelah tenant di-provision untuk memastikan
    isolation hooks menggunakan data terbaru.

    Args:
        customer_name: Nama Customer
    """
    try:
        from qalcuity.isolation import clear_isolation_cache

        # Cari Portal User yang terkait customer ini
        portal_users = frappe.get_all(
            "Portal User",
            filters={"parent": customer_name, "parenttype": "Customer"},
            fields=["user"],
        )

        for pu in portal_users:
            clear_isolation_cache(pu.user)
    except Exception:
        # Cache clearing adalah best-effort, tidak boleh gagal flow utama
        pass
