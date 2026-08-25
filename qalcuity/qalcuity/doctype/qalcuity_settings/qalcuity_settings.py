# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


PAYMENT_MODE_DESCRIPTIONS = {
    "Manual Transfer": (
        "<b>Manual Transfer:</b> Customer upload bukti transfer bank. "
        "Superadmin review & approve manual."
    ),
    "Xendit": (
        "<b>Xendit:</b> Payment gateway online. Customer bayar langsung "
        "via Xendit (QRIS, VA, kartu kredit, dll)."
    ),
    "Hybrid": (
        "<b>Hybrid:</b> Keduanya tersedia. Customer bisa pilih "
        "Manual Transfer atau Xendit saat checkout."
    ),
}


class QalcuitySettings(Document):
    """Pengaturan global Qalcuity ERP."""

    def validate(self):
        """Validasi pengaturan."""
        if self.enable_trial_period and self.trial_period_days <= 0:
            frappe.throw(
                frappe._("Trial period days must be greater than 0 when trial is enabled.")
            )

        if self.max_file_size_mb <= 0:
            frappe.throw(
                frappe._("Max file size must be greater than 0.")
            )

        if self.subscription_expiry_warning_days <= 0:
            frappe.throw(
                frappe._("Subscription expiry warning days must be greater than 0.")
            )

        # Payment mode validation
        self._validate_payment_mode()

    def _validate_payment_mode(self):
        """Validasi berdasarkan payment mode yang dipilih."""
        mode = self.payment_mode or "Manual Transfer"

        if mode in ("Xendit", "Hybrid"):
            if not self.xendit_api_key:
                frappe.throw(
                    frappe._(
                        "Xendit API Key is required when Payment Mode is '{0}'.",
                        format(mode),
                    )
                )

        if mode in ("Manual Transfer", "Hybrid"):
            if not self.bank_accounts or len(self.bank_accounts) == 0:
                frappe.throw(
                    frappe._(
                        "At least one Bank Account is required when Payment Mode is '{0}'.",
                        format(mode),
                    )
                )

    def before_save(self):
        """Sebelum simpan — set payment mode description."""
        self.payment_mode_description = PAYMENT_MODE_DESCRIPTIONS.get(
            self.payment_mode, ""
        )

    def on_update(self):
        """Setelah update - clear cache settings."""
        frappe.cache().delete_value("qalcuity_settings")


@frappe.whitelist()
def get_settings():
    """Ambil Qalcuity Settings (dengan caching, mengembalikan dict).

    Returns:
        dict: Semua fields dari Qalcuity Settings termasuk list bank_accounts.
    """
    cached = frappe.cache().get_value("qalcuity_settings")
    if not cached:
        doc = frappe.get_single("Qalcuity Settings")
        cached = doc.as_dict()

        # Attach bank_accounts as list of dicts
        if hasattr(doc, "bank_accounts") and doc.bank_accounts:
            cached["bank_accounts"] = [
                {
                    "bank_name": ba.bank_name,
                    "account_name": ba.account_name,
                    "account_number": ba.account_number,
                    "bank_branch": ba.bank_branch,
                }
                for ba in doc.bank_accounts
            ]
        else:
            cached["bank_accounts"] = []

        # Mask sensitive fields — never expose raw API keys
        for field in ("xendit_api_key", "xendit_callback_token"):
            if cached.get(field):
                val = str(cached[field])
                if len(val) > 8:
                    cached[field + "_masked"] = val[:4] + "****" + val[-4:]
                else:
                    cached[field + "_masked"] = "****"
                cached[field] = ""  # clear raw value

        frappe.cache().set_value("qalcuity_settings", cached)
    return cached
