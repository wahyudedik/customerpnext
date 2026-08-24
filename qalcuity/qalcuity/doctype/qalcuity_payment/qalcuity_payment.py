# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class QalcuityPayment(Document):
    """Bukti pembayaran manual."""

    def validate(self):
        """Validasi payment."""
        self.validate_subscription()
        self.validate_proof_of_payment()
        self.validate_status_transitions()
        self.validate_review_fields()

    def before_save(self):
        """Sebelum simpan."""
        if self.is_new() and not self.status:
            self.status = "Pending"

    def after_insert(self):
        """Setelah insert."""
        frappe.msgprint(
            _("Payment {0} submitted. Awaiting review.").format(self.name),
            indicator="orange",
        )

    def on_update(self):
        """Setelah update."""
        if self.status == "Approved":
            self.activate_subscription()
        elif self.status == "Rejected":
            self.notify_rejection()

    def validate_subscription(self):
        """Validasi subscription terkait."""
        if self.subscription:
            sub_status = frappe.db.get_value(
                "Qalcuity Subscription", self.subscription, "status"
            )
            if sub_status in ["Cancelled", "Expired"]:
                frappe.throw(
                    _("Cannot submit payment for a {0} subscription.").format(
                        sub_status
                    )
                )

    def validate_proof_of_payment(self):
        """Validasi bukti pembayaran."""
        if self.is_new() and not self.proof_of_payment:
            frappe.throw(
                _("Proof of payment is required.")
            )

    def validate_status_transitions(self):
        """Validasi transisi status."""
        if self._action == "save" and not self.is_new():
            old_status = frappe.db.get_value(
                "Qalcuity Payment", self.name, "status"
            )
            if old_status and old_status != self.status:
                valid_transitions = {
                    "Pending": ["Approved", "Rejected"],
                    "Approved": [],
                    "Rejected": ["Pending"],
                }
                if self.status not in valid_transitions.get(old_status, []):
                    frappe.throw(
                        _("Cannot transition from '{0}' to '{1}'.").format(
                            old_status, self.status
                        )
                    )

    def validate_review_fields(self):
        """Validasi field review."""
        if self.status in ["Approved", "Rejected"]:
            if not self.reviewed_by:
                self.reviewed_by = frappe.session.user
            if not self.review_date:
                self.review_date = now_datetime()

        if self.status == "Rejected" and not self.rejection_reason:
            frappe.throw(
                _("Rejection reason is required when rejecting a payment.")
            )

    def activate_subscription(self):
        """Aktifkan subscription setelah payment approved."""
        if self.subscription:
            sub = frappe.get_doc("Qalcuity Subscription", self.subscription)
            if sub.status == "Pending Payment":
                sub.activate()

    def notify_rejection(self):
        """Notifikasi penolakan payment."""
        frappe.msgprint(
            _("Payment {0} has been rejected.").format(self.name),
            indicator="red",
        )

    @frappe.whitelist()
    def approve(self):
        """Approve payment."""
        if self.status != "Pending":
            frappe.throw(_("Only pending payments can be approved."))

        self.status = "Approved"
        self.reviewed_by = frappe.session.user
        self.review_date = now_datetime()
        self.save()

        frappe.msgprint(
            _("Payment {0} approved successfully.").format(self.name),
            indicator="green",
        )

    @frappe.whitelist()
    def reject(self, reason=None):
        """Reject payment."""
        if self.status != "Pending":
            frappe.throw(_("Only pending payments can be rejected."))

        if not reason:
            frappe.throw(_("Rejection reason is required."))

        self.status = "Rejected"
        self.reviewed_by = frappe.session.user
        self.review_date = now_datetime()
        self.rejection_reason = reason
        self.save()

        frappe.msgprint(
            _("Payment {0} rejected.").format(self.name),
            indicator="red",
        )


def has_permission(doc, ptype):
    """Permission check untuk Qalcuity Payment."""
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

    # Customer can only read/create their own payments (ownership check via subscription)
    if "Customer" in frappe.get_roles(user) and ptype in ("read", "create"):
        if doc.subscription:
            customer = frappe.db.get_value(
                "Qalcuity Subscription", doc.subscription, "customer"
            )
            user_customer = frappe.db.get_value("User", user, "customer_name")
            if customer and user_customer and customer == user_customer:
                return True
        return False

    return False
