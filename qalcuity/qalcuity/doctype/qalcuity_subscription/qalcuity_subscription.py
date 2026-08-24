# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, add_days, add_months


class QalcuitySubscription(Document):
    """Status langganan customer."""

    def validate(self):
        """Validasi subscription."""
        self.validate_dates()
        self.validate_plan_active()
        self.validate_status_transitions()

    def before_save(self):
        """Sebelum simpan."""
        if self.is_new():
            self.set_initial_status()

    def after_insert(self):
        """Setelah insert baru."""
        frappe.msgprint(
            _("Subscription {0} created for customer {1}.").format(
                self.name, self.customer
            ),
            indicator="green",
        )

    def on_update(self):
        """Setelah update."""
        # Update tenant subscription link
        self.update_tenant_link()

    def validate_dates(self):
        """Validasi tanggal."""
        if self.start_date and self.end_date:
            if getdate(self.end_date) < getdate(self.start_date):
                frappe.throw(
                    _("End date cannot be before start date.")
                )

    def validate_plan_active(self):
        """Validasi plan masih aktif."""
        if self.plan:
            plan = frappe.get_doc("Qalcuity Plan", self.plan)
            if not plan.is_active:
                frappe.throw(
                    _("Plan '{0}' is not active.").format(self.plan)
                )

    def validate_status_transitions(self):
        """Validasi transisi status yang valid."""
        if self._action == "save" and not self.is_new():
            old_status = frappe.db.get_value(
                "Qalcuity Subscription", self.name, "status"
            )
            if old_status and old_status != self.status:
                valid_transitions = {
                    "Draft": ["Pending Payment", "Cancelled"],
                    "Pending Payment": ["Active", "Cancelled"],
                    "Active": ["Suspended", "Expired", "Cancelled"],
                    "Suspended": ["Active", "Cancelled", "Expired"],
                    "Expired": ["Pending Payment", "Cancelled"],
                    "Cancelled": [],
                }
                if self.status not in valid_transitions.get(old_status, []):
                    frappe.throw(
                        _("Cannot transition from '{0}' to '{1}'.").format(
                            old_status, self.status
                        )
                    )

    def set_initial_status(self):
        """Set status awal."""
        if not self.status or self.status == "Draft":
            if self.is_trial:
                self.status = "Active"
                self.set_trial_dates()
            else:
                self.status = "Draft"

    def set_trial_dates(self):
        """Set tanggal trial."""
        settings = frappe.get_single("Qalcuity Settings")
        if not self.start_date:
            self.start_date = nowdate()
        trial_days = settings.trial_period_days or 14
        self.end_date = add_days(getdate(self.start_date), trial_days)

    @frappe.whitelist()
    def activate(self):
        """Aktifkan subscription."""
        if self.status != "Pending Payment":
            frappe.throw(
                _("Only pending payment subscriptions can be activated.")
            )
        self.status = "Active"
        if not self.start_date:
            self.start_date = nowdate()
        if not self.end_date:
            # Set end date based on billing period
            self.set_end_date_from_plan()
        self.save()
        frappe.msgprint(
            _("Subscription {0} activated.").format(self.name),
            indicator="green",
        )

    @frappe.whitelist()
    def reactivate(self):
        """Reactivate a suspended subscription."""
        if self.status != "Suspended":
            frappe.throw(_("Can only reactivate a Suspended subscription."))

        if self.end_date and getdate(self.end_date) < getdate():
            frappe.throw(
                _("Cannot reactivate an expired subscription. Please create a new one.")
            )

        self.status = "Active"
        self.save()
        frappe.msgprint(
            _("Subscription {0} reactivated successfully.").format(self.name),
            indicator="green",
        )

    @frappe.whitelist()
    def suspend(self):
        """Suspend subscription."""
        if self.status != "Active":
            frappe.throw(
                _("Only active subscriptions can be suspended.")
            )
        self.status = "Suspended"
        self.save()
        # Suspend tenant
        self.suspend_tenant()
        frappe.msgprint(
            _("Subscription {0} suspended.").format(self.name),
            indicator="orange",
        )

    @frappe.whitelist()
    def cancel(self):
        """Batalkan subscription."""
        if self.status in ["Cancelled"]:
            frappe.throw(
                _("Subscription is already cancelled.")
            )
        self.status = "Cancelled"
        self.save()
        frappe.msgprint(
            _("Subscription {0} cancelled.").format(self.name),
            indicator="red",
        )

    def set_end_date_from_plan(self):
        """Set end date berdasarkan billing period plan."""
        plan = frappe.get_doc("Qalcuity Plan", self.plan)
        if plan.billing_period == "Monthly":
            self.end_date = add_months(getdate(self.start_date), 1)
        elif plan.billing_period == "Quarterly":
            self.end_date = add_months(getdate(self.start_date), 3)
        elif plan.billing_period == "Annual":
            self.end_date = add_months(getdate(self.start_date), 12)

    def update_tenant_link(self):
        """Update tenant subscription link."""
        tenant = frappe.db.get_value(
            "Qalcuity Tenant",
            {"customer": self.customer},
            "name",
        )
        if tenant:
            frappe.db.set_value("Qalcuity Tenant", tenant, "subscription", self.name)

    def suspend_tenant(self):
        """Suspend tenant terkait."""
        tenant = frappe.db.get_value(
            "Qalcuity Tenant",
            {"customer": self.customer},
            "name",
        )
        if tenant:
            frappe.db.set_value("Qalcuity Tenant", tenant, "status", "Suspended")

    def check_expiry(self):
        """Cek apakah subscription sudah expired."""
        if self.status == "Active" and self.end_date:
            if getdate(nowdate()) > getdate(self.end_date):
                self.status = "Expired"
                self.save(ignore_permissions=True)
                self.suspend_tenant()


def has_permission(doc, ptype):
    """Permission check untuk Qalcuity Subscription."""
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

    # Customer can only read/create their own subscriptions (ownership check)
    if "Customer" in frappe.get_roles(user) and ptype in ("read", "create"):
        customer = frappe.db.get_value("User", user, "customer_name")
        if customer and doc.customer == customer:
            return True
        return False

    return False
