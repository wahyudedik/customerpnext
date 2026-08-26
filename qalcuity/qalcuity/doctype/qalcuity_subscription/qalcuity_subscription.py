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
        """Setelah insert baru — log creation."""
        frappe.msgprint(
            _("Subscription {0} created for customer {1}.").format(
                self.name, self.customer
            ),
            indicator="green",
        )
        # Log subscription creation
        try:
            from qalcuity.api.subscription_history import create_subscription_log
            create_subscription_log(
                subscription_name=self.name,
                action="Created",
                new_status=self.status,
                new_plan=self.plan,
                notes="Subscription created.",
            )
        except Exception:
            pass

    def on_update(self):
        """Setelah update.

        Triggers:
        - Update tenant subscription link
        - Provision ERP when subscription becomes Active
        - Deprovision ERP when subscription expires/is cancelled
        """
        # Update tenant subscription link
        self.update_tenant_link()

        # ERP Provisioning triggers
        self._handle_provisioning()

    def _handle_provisioning(self):
        """Handle ERP provisioning based on subscription status changes.

        - Active → provision tenant (if not already provisioned)
        - Expired/Cancelled → deprovision tenant (if provisioned)
        - Suspended → deprovision tenant (if provisioned)
        - Reactivated → re-provision tenant

        Only triggers on status change (not on every save).
        Skipped if no tenant is linked.
        """
        # Only act on status changes (not new subscriptions)
        if self.is_new():
            return

        # Get the old status from DB
        old_status = frappe.db.get_value(
            "Qalcuity Subscription", self.name, "status"
        )

        # No change in status → no provisioning action needed
        if old_status == self.status:
            return

        # Find the tenant for this subscription
        tenant_name = self.tenant
        if not tenant_name:
            tenant_name = frappe.db.get_value(
                "Qalcuity Tenant",
                {"customer": self.customer},
                "name",
            )
        if not tenant_name:
            return

        try:
            tenant = frappe.get_doc("Qalcuity Tenant", tenant_name)
        except frappe.DoesNotExistError:
            return

        # Subscription became Active → provision
        if self.status == "Active" and old_status != "Active":
            if tenant.erp_provisioning_status not in ("Completed", "In Progress"):
                self._trigger_provision(tenant_name)
            elif tenant.erp_provisioning_status == "Completed":
                # Was provisioned before (reactivation) → re-assign roles
                self._trigger_reactivate(tenant_name)

        # Subscription expired / cancelled / suspended → deprovision
        elif self.status in ("Expired", "Cancelled", "Suspended"):
            if tenant.erp_provisioning_status == "Completed":
                self._trigger_deprovision(tenant_name)

    def _trigger_provision(self, tenant_name):
        """Trigger ERP provisioning for a tenant (async-safe)."""
        try:
            from qalcuity.provisioning import provision_tenant
            provision_tenant(tenant_name)
        except Exception as e:
            frappe.log_error(
                f"Provisioning failed for tenant {tenant_name}: {str(e)}",
                "Qalcuity Provisioning",
            )

    def _trigger_deprovision(self, tenant_name):
        """Trigger ERP deprovisioning for a tenant (async-safe)."""
        try:
            from qalcuity.provisioning import deprovision_tenant
            deprovision_tenant(tenant_name)
        except Exception as e:
            frappe.log_error(
                f"Deprovisioning failed for tenant {tenant_name}: {str(e)}",
                "Qalcuity Provisioning",
            )

    def _trigger_reactivate(self, tenant_name):
        """Trigger ERP reactivation for a tenant (async-safe)."""
        try:
            from qalcuity.provisioning import reactivate_tenant
            reactivate_tenant(tenant_name)
        except Exception as e:
            frappe.log_error(
                f"Reactivation failed for tenant {tenant_name}: {str(e)}",
                "Qalcuity Provisioning",
            )

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
                    "Active": ["Grace Period", "Suspended", "Expired", "Cancelled"],
                    "Grace Period": ["Active", "Expired", "Cancelled"],
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
        """Aktifkan subscription.

        Flow:
        1. Validasi status = "Pending Payment"
        2. Set status = "Active"
        3. Set start_date = today (jika belum ada)
        4. Set end_date = today + billing_period (jika belum ada)
        5. Save → on_update() akan update tenant link
        6. Update tenant status → "Active"
        7. Log activation
        """
        if self.status != "Pending Payment":
            frappe.throw(
                _("Only pending payment subscriptions can be activated.")
            )
        old_status = self.status
        self.status = "Active"
        if not self.start_date:
            self.start_date = nowdate()
        if not self.end_date:
            # Set end date based on billing period
            self.set_end_date_from_plan()
        self.save()

        # Update tenant status ke Active
        self._activate_tenant()

        # Log activation
        try:
            from qalcuity.api.subscription_history import create_subscription_log
            create_subscription_log(
                subscription_name=self.name,
                action="Activated",
                old_status=old_status,
                new_status="Active",
                notes="Subscription activated.",
            )
        except Exception:
            pass

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

        old_status = self.status
        self.status = "Active"
        self.save()

        # Log reactivation
        try:
            from qalcuity.api.subscription_history import create_subscription_log
            create_subscription_log(
                subscription_name=self.name,
                action="Reactivated",
                old_status=old_status,
                new_status="Active",
                notes="Subscription reactivated.",
            )
        except Exception:
            pass

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
        old_status = self.status
        self.status = "Suspended"
        self.save()
        # Suspend tenant
        self.suspend_tenant()

        # Log suspension
        try:
            from qalcuity.api.subscription_history import create_subscription_log
            create_subscription_log(
                subscription_name=self.name,
                action="Suspended",
                old_status=old_status,
                new_status="Suspended",
                notes="Subscription suspended.",
            )
        except Exception:
            pass

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
        old_status = self.status
        self.status = "Cancelled"
        self.save()

        # Log cancellation
        try:
            from qalcuity.api.subscription_history import create_subscription_log
            create_subscription_log(
                subscription_name=self.name,
                action="Cancelled",
                old_status=old_status,
                new_status="Cancelled",
                notes="Subscription cancelled.",
            )
        except Exception:
            pass

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

    def _activate_tenant(self):
        """Update tenant status ke Active setelah subscription aktif."""
        tenant = frappe.db.get_value(
            "Qalcuity Tenant",
            {"customer": self.customer},
            "name",
        )
        if tenant:
            tenant_status = frappe.db.get_value("Qalcuity Tenant", tenant, "status")
            if tenant_status != "Active":
                frappe.db.set_value("Qalcuity Tenant", tenant, "status", "Active")

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
        """Cek apakah subscription sudah expired.

        Handles both "Active" and "Grace Period" statuses.
        - Active + past end_date → transition to Grace Period (handled by scheduler)
        - Grace Period + past grace_end_date → transition to Expired
        """
        if self.status == "Active" and self.end_date:
            if getdate(nowdate()) > getdate(self.end_date):
                # Don't immediately expire — let the scheduler handle grace period
                # Only expire if explicitly called with force
                pass

        if self.status == "Grace Period" and self.end_date:
            from qalcuity.tasks import GRACE_PERIOD_DAYS
            grace_end_date = add_days(getdate(self.end_date), GRACE_PERIOD_DAYS)
            if getdate(nowdate()) > grace_end_date:
                old_status = self.status
                self.status = "Expired"
                self.save(ignore_permissions=True)
                self.suspend_tenant()

                # Log expiry
                try:
                    from qalcuity.api.subscription_history import create_subscription_log
                    create_subscription_log(
                        subscription_name=self.name,
                        action="Expired",
                        old_status=old_status,
                        new_status="Expired",
                        notes="Subscription expired (auto-detected by scheduler).",
                    )
                except Exception:
                    pass


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
        customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
        if customer and doc.customer == customer:
            return True
        return False

    return False
