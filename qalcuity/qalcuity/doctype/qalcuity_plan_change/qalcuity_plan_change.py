# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity Plan Change — Plan upgrade/downgrade with prorated billing.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, date_diff, today, add_months


class QalcuityPlanChange(Document):
    """Permintaan perubahan plan (upgrade/downgrade) dengan prorated billing."""

    def validate(self):
        """Validasi plan change."""
        self.validate_subscription_active()
        self.validate_different_plan()
        self.determine_change_type()
        self.calculate_prorated_credit()

    def validate_subscription_active(self):
        """Subscription harus Active atau Grace Period."""
        sub = frappe.get_doc("Qalcuity Subscription", self.subscription)
        if sub.status not in ("Active", "Grace Period"):
            frappe.throw(_("Only active subscriptions can change plans."))
        # Pastikan subscription milik customer
        if sub.customer != self.customer:
            frappe.throw(_("Subscription does not belong to this customer."))
        self.current_plan = sub.plan

    def validate_different_plan(self):
        """Plan baru harus beda dari plan lama."""
        if self.current_plan == self.new_plan:
            frappe.throw(_("New plan must be different from current plan."))
        # Pastikan plan baru aktif
        if not frappe.db.get_value("Qalcuity Plan", self.new_plan, "is_active"):
            frappe.throw(_("Selected plan is not active."))

    def determine_change_type(self):
        """Tentukan upgrade atau downgrade berdasarkan harga."""
        current_price = frappe.db.get_value("Qalcuity Plan", self.current_plan, "price") or 0
        new_price = frappe.db.get_value("Qalcuity Plan", self.new_plan, "price") or 0
        self.current_plan_price = current_price
        self.new_plan_price = new_price
        self.change_type = "Upgrade" if new_price > current_price else "Downgrade"

    def calculate_prorated_credit(self):
        """Hitung kredit prorated dari plan lama."""
        sub = frappe.get_doc("Qalcuity Subscription", self.subscription)
        if not sub.start_date or not sub.end_date:
            self.prorated_credit = 0
            self.amount_to_pay = self.new_plan_price
            return

        end_date = getdate(sub.end_date)
        start_date = getdate(sub.start_date)
        effective = getdate(self.effective_date) if self.effective_date else getdate(today())

        total_days = date_diff(end_date, start_date)
        remaining_days = date_diff(end_date, effective)

        if total_days <= 0 or remaining_days <= 0:
            self.prorated_credit = 0
        else:
            # Kredit = (sisa hari / total hari) × harga plan lama
            self.prorated_credit = round((remaining_days / total_days) * self.current_plan_price)

        # Amount to pay = harga plan baru - prorated credit (untuk upgrade)
        # Untuk downgrade, customer mendapat kredit (tidak refund, tapi dikurangkan dari billing berikutnya)
        self.amount_to_pay = max(0, self.new_plan_price - self.prorated_credit)

    def on_submit(self):
        """Saat disetujui, proses perubahan plan."""
        self.process_plan_change()

    def process_plan_change(self):
        """Proses perubahan plan pada subscription."""
        sub = frappe.get_doc("Qalcuity Subscription", self.subscription)

        # Update plan
        old_plan = sub.plan
        sub.plan = self.new_plan

        # Recalculate end_date berdasarkan plan baru
        # Mulai dari effective_date, durasi = billing_period plan baru
        sub.start_date = self.effective_date or today()
        billing = frappe.db.get_value("Qalcuity Plan", self.new_plan, "billing_period") or "Monthly"

        start = getdate(sub.start_date)
        if billing == "Monthly":
            sub.end_date = add_months(start, 1)
        elif billing == "Quarterly":
            sub.end_date = add_months(start, 3)
        elif billing == "Annual":
            sub.end_date = add_months(start, 12)

        sub.save(ignore_permissions=True)

        # Log perubahan
        self.create_change_log(sub, old_plan)

        self.status = "Completed"
        self.reviewed_by = frappe.session.user
        self.review_date = frappe.utils.now_datetime()
        self.save(ignore_permissions=True)

        frappe.db.commit()

    def create_change_log(self, subscription, old_plan):
        """Buat subscription log untuk perubahan plan."""
        frappe.get_doc({
            "doctype": "Qalcuity Subscription Log",
            "subscription": subscription.name,
            "action": "Plan Changed",
            "old_status": subscription.status,
            "new_status": subscription.status,
            "old_plan": old_plan,
            "new_plan": self.new_plan,
            "notes": "Plan changed from {0} to {1} ({2}). Prorated credit: {3}".format(
                old_plan, self.new_plan, self.change_type, self.prorated_credit
            ),
        }).insert(ignore_permissions=True)

    def on_cancel(self):
        """Cancel plan change."""
        self.status = "Cancelled"
        self.save(ignore_permissions=True)


def has_permission(doc, ptype):
    """Permission check — customer hanya bisa lihat milik sendiri."""
    user = frappe.session.user
    if user == "Administrator":
        return True
    roles = frappe.get_roles(user)
    if "System Manager" in roles or "Qalcuity Superadmin" in roles or "Qalcuity Admin" in roles:
        return True
    # Customer — check Portal User → Customer mapping
    customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
    if customer and doc.customer == customer:
        if ptype in ("read", "create"):
            return True
    return False
