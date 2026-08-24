# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


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

    def before_save(self):
        """Sebelum simpan."""
        pass

    def on_update(self):
        """Setelah update - clear cache settings."""
        frappe.cache().delete_value("qalcuity_settings")


@frappe.whitelist()
def get_settings():
    """Ambil Qalcuity Settings (dengan caching)."""
    settings = frappe.cache().get_value("qalcuity_settings")
    if not settings:
        settings = frappe.get_single("Qalcuity Settings")
        frappe.cache().set_value("qalcuity_settings", settings)
    return settings
