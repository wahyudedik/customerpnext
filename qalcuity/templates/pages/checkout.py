# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Checkout page context for Qalcuity ERP.
Provides page metadata, bank transfer details, and WhatsApp confirmation
for the checkout form.
"""

import frappe
from urllib.parse import quote

no_cache = True


def get_context(context):
    """Set page context for checkout page."""
    context.title = "Checkout - Qalcuity ERP"
    context.no_header = True
    context.no_breadcrumbs = True
    context.page_content_class = "qalcuity-checkout-page"

    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect=" + frappe.utils.cint(
            frappe.form_dict.get("next", "/checkout")
        )
        raise frappe.Redirect

    # Get settings from Qalcuity Settings (with bank accounts, whatsapp, etc.)
    try:
        settings = frappe.get_single("Qalcuity Settings")
        context.currency = getattr(settings, "currency", "IDR") or "IDR"

        # Multiple bank accounts (from child table)
        bank_accounts = []
        if hasattr(settings, "bank_accounts") and settings.bank_accounts:
            for ba in settings.bank_accounts:
                bank_accounts.append({
                    "bank_name": ba.bank_name or "",
                    "account_name": ba.account_name or "",
                    "account_number": ba.account_number or "",
                    "bank_branch": ba.bank_branch or "",
                })
        context.bank_accounts = bank_accounts

        # Legacy single bank fields (fallback for backward compatibility)
        context.bank_name = getattr(settings, "bank_name", "") or ""
        context.bank_account_name = getattr(settings, "bank_account_name", "") or ""
        context.bank_account_number = getattr(settings, "bank_account_number", "") or ""

        # Payment mode
        context.payment_mode = getattr(settings, "payment_mode", "Manual Transfer") or "Manual Transfer"

        # WhatsApp settings
        context.whatsapp_enabled = bool(getattr(settings, "whatsapp_enabled", False))
        context.whatsapp_phone_number = getattr(settings, "whatsapp_phone_number", "") or ""
    except Exception:
        context.currency = "IDR"
        context.bank_accounts = []
        context.bank_name = ""
        context.bank_account_name = ""
        context.bank_account_number = ""
        context.payment_mode = "Manual Transfer"
        context.whatsapp_enabled = False
        context.whatsapp_phone_number = ""

    # Get plan name from query parameter
    plan_name = frappe.form_dict.get("plan", "")
    context.plan_name = plan_name

    # Get plan details if provided
    if plan_name:
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
            ],
        )
        if plan:
            context.plan = plan[0]
        else:
            context.plan = None
            frappe.msgprint(
                frappe._("Paket tidak ditemukan atau tidak aktif."),
                indicator="red",
            )
    else:
        context.plan = None

    # Build WhatsApp URL for post-payment confirmation
    context.whatsapp_url = ""
    if context.whatsapp_enabled and context.whatsapp_phone_number:
        plan_display = ""
        amount_display = ""
        if context.plan:
            plan_display = context.plan.get("plan_name", "")
            price_val = context.plan.get("price", 0)
            if price_val and price_val > 0:
                amount_display = "Rp {:,.0f}".format(price_val).replace(",", ".")
            else:
                amount_display = "Gratis"

        message = (
            "Halo Qalcuity, saya ingin mengonfirmasi pembayaran "
            "untuk paket {plan} sebesar {amount}. "
            "Bukti transfer sudah diupload. Terima kasih."
        ).format(plan=plan_display, amount=amount_display)

        phone = context.whatsapp_phone_number.replace("+", "").replace(" ", "").replace("-", "")
        context.whatsapp_url = "https://wa.me/{phone}?text={text}".format(
            phone=phone, text=quote(message)
        )

    # Get customer info
    user = frappe.session.user
    customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
    context.customer_name = customer or ""
