# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, cint, getdate


class QalcuityTenant(Document):
    """Informasi tenant/isolasi data."""

    def validate(self):
        """Validasi tenant."""
        self.validate_tenant_id()
        self.validate_unique_tenant()
        self.validate_customer()

    def before_insert(self):
        """Sebelum insert."""
        self.set_provisioned_on()
        self.generate_tenant_id()

    def on_update(self):
        """Setelah update."""
        self.update_last_activity()

    def validate_tenant_id(self):
        """Validasi tenant_id."""
        if not self.tenant_id:
            frappe.throw(_("Tenant ID is required."))

    def validate_unique_tenant(self):
        """Validasi tenant_id unique."""
        if self.is_new():
            existing = frappe.db.exists(
                "Qalcuity Tenant",
                {"tenant_id": self.tenant_id, "name": ["!=", self.name]},
            )
            if existing:
                frappe.throw(
                    _("Tenant ID '{0}' already exists.").format(self.tenant_id)
                )

    def validate_customer(self):
        """Validasi customer."""
        if self.customer:
            # Check customer doesn't already have an active tenant
            existing = frappe.db.exists(
                "Qalcuity Tenant",
                {
                    "customer": self.customer,
                    "status": "Active",
                    "name": ["!=", self.name],
                },
            )
            if existing:
                frappe.throw(
                    _("Customer '{0}' already has an active tenant ({1}).").format(
                        self.customer, existing
                    )
                )

    def set_provisioned_on(self):
        """Set waktu provisioning."""
        if not self.provisioned_on:
            self.provisioned_on = now_datetime()

    def generate_tenant_id(self):
        """Generate tenant_id dengan format TENANT-{YYYYMMDD}-{####}."""
        if not self.tenant_id:
            from frappe.utils import today
            import re

            # Format tanggal: YYYYMMDD
            date_str = getdate(today()).strftime("%Y%m%d")

            # Hitung jumlah tenant yang dibuat hari ini
            prefix = f"TENANT-{date_str}-"
            count_today = frappe.db.count(
                "Qalcuity Tenant",
                {"tenant_id": ["like", f"{prefix}%"]},
            )
            sequence = count_today + 1

            self.tenant_id = f"{prefix}{sequence:04d}"

    def update_last_activity(self):
        """Update waktu aktivitas terakhir."""
        self.last_activity = now_datetime()

    # =========================================================================
    # ERP Provisioning Methods
    # =========================================================================

    @frappe.whitelist()
    def provision(self):
        """
        Provision ERP environment for this tenant.
        Creates Company, assigns roles, configures workspace.
        """
        from qalcuity.qalcuity.provisioning import provision_tenant

        return provision_tenant(self.name)

    @frappe.whitelist()
    def deprovision(self):
        """
        Deprovision ERP environment for this tenant.
        Removes ERP roles but preserves Company and data.
        """
        from qalcuity.qalcuity.provisioning import deprovision_tenant

        return deprovision_tenant(self.name)

    @frappe.whitelist()
    def retry_provisioning(self):
        """
        Retry provisioning for this tenant.
        Used when previous provisioning failed.
        """
        from qalcuity.qalcuity.provisioning import provision_tenant

        return provision_tenant(self.name)

    # =========================================================================
    # Existing Methods
    # =========================================================================

    @frappe.whitelist()
    def suspend(self):
        """Suspend tenant."""
        if self.status == "Suspended":
            frappe.throw(_("Tenant is already suspended."))

        self.status = "Suspended"
        self.save()
        frappe.msgprint(
            _("Tenant {0} has been suspended.").format(self.tenant_id),
            indicator="orange",
        )

    @frappe.whitelist()
    def reactivate(self):
        """Reaktifkan tenant."""
        if self.status == "Active":
            frappe.throw(_("Tenant is already active."))

        # Check subscription is still active
        if self.subscription:
            sub_status = frappe.db.get_value(
                "Qalcuity Subscription", self.subscription, "status"
            )
            if sub_status not in ["Active"]:
                frappe.throw(
                    _(
                        "Cannot reactivate tenant: subscription is {0}."
                    ).format(sub_status)
                )

        self.status = "Active"
        self.save()
        frappe.msgprint(
            _("Tenant {0} has been reactivated.").format(self.tenant_id),
            indicator="green",
        )

    @frappe.whitelist()
    def terminate(self):
        """Terminate tenant."""
        if self.status == "Terminated":
            frappe.throw(_("Tenant is already terminated."))

        frappe.confirm(
            _(
                "Are you sure you want to terminate tenant '{0}'? "
                "This action cannot be undone."
            ).format(self.tenant_id),
        )

        self.status = "Terminated"
        self.save()
        frappe.msgprint(
            _("Tenant {0} has been terminated.").format(self.tenant_id),
            indicator="red",
        )

    def update_storage_usage(self):
        """Update storage usage (placeholder untuk integrasi)."""
        # This would integrate with actual storage monitoring
        pass


def has_permission(doc, ptype):
    """Permission check untuk Qalcuity Tenant."""
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

    # Customer can only read their own tenant (ownership check)
    if ptype == "read" and "Customer" in frappe.get_roles(user):
        user_customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
        if user_customer and doc.customer == user_customer:
            return True
        return False

    return False
