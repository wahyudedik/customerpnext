# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Plans API endpoints for Qalcuity ERP.
Provides whitelisted methods for plan listing and checkout flow.
"""

import frappe
from frappe import _
from frappe.utils import nowdate


@frappe.whitelisted(allow_guest=True)
def get_active_plans():
    """
    Get all active plans with features for pricing page.

    Returns:
        list: List of active plans with their features
    """
    plans = frappe.get_all(
        "Qalcuity Plan",
        filters={"is_active": 1},
        fields=[
            "name",
            "plan_name",
            "description",
            "price",
            "currency",
            "billing_period",
            "is_trial",
            "max_users",
            "max_storage_gb",
            "sort_order",
        ],
        order_by="sort_order asc, creation asc",
    )

    for plan in plans:
        features = frappe.get_all(
            "Qalcuity Plan Feature",
            filters={"parent": plan.name},
            fields=["feature_name"],
        )
        plan.features = [f.feature_name for f in features]

        # Format price for display
        if plan.is_trial:
            plan.price_display = "Gratis"
        elif plan.price == 0:
            plan.price_display = "Gratis"
        else:
            plan.price_display = "Rp {:,.0f}".format(plan.price).replace(",", ".")

        # Format billing period for display
        period_map = {
            "Monthly": "/bulan",
            "Quarterly": "/kuartal",
            "Annual": "/tahun",
        }
        plan.period_display = period_map.get(plan.billing_period, "/bulan")

    return plans


@frappe.whitelisted()
def submit_payment_with_subscription(plan_name, amount, payment_method, payment_date, proof_of_payment=None, reference_number=None):
    """
    Submit payment with automatic subscription creation.
    Used by the checkout page.

    Args:
        plan_name: Name of Qalcuity Plan
        amount: Payment amount
        payment_method: Bank Transfer, E-Wallet, or Virtual Account
        payment_date: Date of payment
        proof_of_payment: Attached file URL
        reference_number: Bank reference number

    Returns:
        dict: Created payment and subscription documents
    """
    user = frappe.session.user

    # Get customer linked to user
    customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
    if not customer:
        frappe.throw(_("Akun pelanggan tidak ditemukan untuk pengguna saat ini."))

    # Validate plan exists and is active
    if not frappe.db.exists("Qalcuity Plan", plan_name):
        frappe.throw(_("Paket {0} tidak ditemukan.").format(plan_name))

    plan_active = frappe.db.get_value("Qalcuity Plan", plan_name, "is_active")
    if not plan_active:
        frappe.throw(_("Paket {0} tidak aktif.").format(plan_name))

    # Validate amount
    amount = frappe.utils.flt(amount)
    if amount <= 0:
        frappe.throw(_("Jumlah pembayaran harus lebih dari 0."))

    # Get plan price for validation
    plan_price = frappe.db.get_value("Qalcuity Plan", plan_name, "price")
    if not frappe.db.get_value("Qalcuity Plan", plan_name, "is_trial") and amount < plan_price:
        frappe.msgprint(
            _("Peringatan: Jumlah pembayaran ({0}) kurang dari harga paket ({1}).").format(
                amount, plan_price
            ),
            indicator="orange",
        )

    # Get tenant for this customer (if exists)
    tenant = frappe.db.get_value(
        "Qalcuity Tenant",
        {"customer": customer},
        "name",
    )

    # Create Qalcuity Subscription
    subscription = frappe.get_doc(
        {
            "doctype": "Qalcuity Subscription",
            "customer": customer,
            "plan": plan_name,
            "status": "Pending Payment",
            "notes": "Dibuat otomatis dari halaman checkout.",
        }
    )
    # Set tenant link if tenant exists
    if tenant:
        subscription.tenant = tenant

    subscription.insert(ignore_permissions=True)

    # Create Qalcuity Payment
    payment = frappe.get_doc(
        {
            "doctype": "Qalcuity Payment",
            "subscription": subscription.name,
            "amount": amount,
            "currency": frappe.db.get_value("Qalcuity Plan", plan_name, "currency") or "IDR",
            "payment_method": payment_method,
            "payment_date": payment_date,
            "proof_of_payment": proof_of_payment,
            "reference_number": reference_number,
            "status": "Pending",
        }
    )
    payment.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "subscription": subscription.as_dict(),
        "payment": payment.as_dict(),
        "message": _("Pembayaran berhasil diajukan. Menunggu verifikasi oleh admin."),
    }


@frappe.whitelisted()
def get_plan_by_name(plan_name):
    """
    Get a specific plan by name with features.

    Args:
        plan_name: Plan name

    Returns:
        dict: Plan details with features
    """
    plan = frappe.get_all(
        "Qalcuity Plan",
        filters={"name": plan_name, "is_active": 1},
        fields=[
            "name",
            "plan_name",
            "description",
            "price",
            "currency",
            "billing_period",
            "is_trial",
            "max_users",
            "max_storage_gb",
        ],
    )

    if not plan:
        frappe.throw(_("Paket {0} tidak ditemukan atau tidak aktif.").format(plan_name))

    plan = plan[0]

    features = frappe.get_all(
        "Qalcuity Plan Feature",
        filters={"parent": plan.name},
        fields=["feature_name"],
    )
    plan.features = [f.feature_name for f in features]

    # Format price for display
    if plan.is_trial:
        plan.price_display = "Gratis"
    elif plan.price == 0:
        plan.price_display = "Gratis"
    else:
        plan.price_display = "Rp {:,.0f}".format(plan.price).replace(",", ".")

    period_map = {
        "Monthly": "/bulan",
        "Quarterly": "/kuartal",
        "Annual": "/tahun",
    }
    plan.period_display = period_map.get(plan.billing_period, "/bulan")

    return plan
