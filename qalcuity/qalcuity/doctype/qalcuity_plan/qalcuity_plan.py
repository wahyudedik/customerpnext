# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class QalcuityPlan(Document):
    """Paket langganan SaaS."""

    def validate(self):
        """Validasi plan."""
        if self.price < 0:
            frappe.throw(_("Price cannot be negative."))

        if self.max_users <= 0:
            frappe.throw(_("Max users must be greater than 0."))

        if self.max_storage_gb <= 0:
            frappe.throw(_("Max storage must be greater than 0."))

        # Validate features
        if self.features:
            feature_names = [f.feature_name for f in self.features]
            seen = set()
            for name in feature_names:
                if name in seen:
                    frappe.throw(
                        _("Duplicate feature name: {0}").format(name)
                    )
                seen.add(name)

    def before_save(self):
        """Sebelum simpan."""
        pass

    def on_update(self):
        """Setelah update - clear cache."""
        frappe.cache().delete_value("qalcuity_plans")

    def before_delete(self):
        """Sebelum hapus - cek apakah ada subscription aktif."""
        active_subscriptions = frappe.db.count(
            "Qalcuity Subscription",
            {
                "plan": self.name,
                "status": ["in", ["Active", "Pending Payment"]],
            },
        )
        if active_subscriptions:
            frappe.throw(
                _(
                    "Cannot delete plan '{0}' because it has {1} active/pending subscription(s). "
                    "Deactivate the plan instead."
                ).format(self.name, active_subscriptions)
            )

    @frappe.whitelist()
    def deactivate(self):
        """Nonaktifkan plan."""
        self.is_active = 0
        self.save()
        frappe.msgprint(
            _("Plan {0} has been deactivated.").format(self.name),
            indicator="orange",
        )


def has_permission(doc, ptype):
    """Permission check untuk Qalcuity Plan."""
    user = frappe.session.user

    # System Manager and Qalcuity Superadmin have full access
    if frappe.db.exists(
        "Has Role",
        {"parent": user, "role": ["in", ["System Manager", "Qalcuity Superadmin"]]},
    ):
        return True

    # Qalcuity Admin can read/write
    if frappe.db.exists(
        "Has Role",
        {"parent": user, "role": "Qalcuity Admin"},
    ):
        return True

    # Guest and Customer can only read
    if ptype == "read":
        return True

    return False
