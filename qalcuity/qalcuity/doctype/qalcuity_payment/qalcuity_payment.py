# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, get_url, nowdate, add_days, getdate, add_months


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
        """Setelah insert — kirim notifikasi ke superadmin."""
        frappe.msgprint(
            _("Payment {0} submitted. Awaiting review.").format(self.name),
            indicator="orange",
        )

        # Email notifikasi ke superadmin
        self.notify_superadmin_new_payment()

        # In-app notification ke superadmin
        self._notify_superadmin_in_app()

    def on_update(self):
        """Setelah update."""
        if self.status == "Approved":
            self.activate_subscription()
            self._notify_customer_in_app(
                "Payment Disetujui",
                f"Pembayaran {self.name} sebesar {self.currency or 'IDR'} {self.amount} telah disetujui.",
                "/my-payments",
            )
        elif self.status == "Rejected":
            self.notify_rejection()
            self._notify_customer_in_app(
                "Payment Ditolak",
                f"Pembayaran {self.name} telah ditolak. Alasan: {self.rejection_reason or 'Tidak disebutkan'}",
                "/my-payments",
            )

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
        """Aktifkan subscription setelah payment approved.

        Flow:
        1. Jika subscription ada dan status = "Pending Payment" → activate
        2. Setelah activate → update tenant status ke "Active"
        """
        if not self.subscription:
            frappe.log_error(
                message=f"Payment {self.name} approved but no subscription linked.",
                title="Qalcuity Payment - No Subscription",
            )
            return

        sub = frappe.get_doc("Qalcuity Subscription", self.subscription)
        if sub.status == "Pending Payment":
            # activate() akan set status=Active, start_date, end_date, dan update tenant link
            sub.activate()
        elif sub.status == "Active":
            # Sudah aktif, pastikan tenant ter-update
            self._activate_tenant()
        else:
            frappe.log_error(
                message=f"Payment {self.name} approved but subscription {sub.name} has unexpected status: {sub.status}",
                title="Qalcuity Payment - Subscription Status Mismatch",
            )

    def _activate_tenant(self):
        """Update tenant status ke Active setelah subscription aktif."""
        if not self.subscription:
            return

        customer = frappe.db.get_value(
            "Qalcuity Subscription", self.subscription, "customer"
        )
        if not customer:
            return

        tenant = frappe.db.get_value(
            "Qalcuity Tenant",
            {"customer": customer},
            "name",
        )
        if tenant:
            tenant_status = frappe.db.get_value("Qalcuity Tenant", tenant, "status")
            if tenant_status != "Active":
                frappe.db.set_value("Qalcuity Tenant", tenant, "status", "Active")
                frappe.log_error(
                    message=f"Tenant {tenant} activated via payment {self.name} approval.",
                    title="Qalcuity Tenant Activated",
                )

    def get_customer_email(self):
        """Ambil email customer dari subscription."""
        if self.subscription:
            customer = frappe.db.get_value(
                "Qalcuity Subscription", self.subscription, "customer"
            )
            if customer:
                customer_doc = frappe.get_doc("Customer", customer)
                # Ambil email dari customer email list atau field email
                if customer_doc.email_id:
                    return customer_doc.email_id
                # Fallback: cari di Customer Email
                email = frappe.db.get_value(
                    "Customer Email",
                    {"parent": customer, "email_id": ["is", "set"]},
                    "email_id",
                )
                if email:
                    return email
                # Fallback: cari user yang terkait customer
                portal_user = frappe.db.get_value(
                    "Portal User",
                    {"parent": customer, "parenttype": "Customer"},
                    "user",
                )
                if portal_user:
                    user_email = frappe.db.get_value("User", portal_user, "email")
                    if user_email:
                        return user_email
        return None

    def send_rejection_email(self, recipient_email):
        """Kirim email notifikasi penolakan payment."""
        subject = _("Penolakan Pembayaran {0} - Qalcuity ERP").format(self.name)

        message = frappe.render_template(
            """<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color: #f44336; color: white; padding: 20px; text-align: center;">
        <h2 style="margin: 0;">Qalcuity ERP</h2>
        <p style="margin: 5px 0 0 0;">Notifikasi Penolakan Pembayaran</p>
    </div>
    <div style="padding: 20px; background-color: #ffffff; border: 1px solid #e0e0e0;">
        <p>Halo,</p>
        <p>Pembayaran Anda dengan detail berikut telah <strong style="color: #f44336;">DITOLAK</strong>:</p>
        <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">ID Pembayaran</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{{ payment_name }}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Subscription</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{{ subscription }}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Jumlah</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{{ currency }} {{ amount }}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Tanggal Pembayaran</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{{ payment_date }}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Alasan Penolakan</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee; color: #f44336;">{{ rejection_reason }}</td>
            </tr>
        </table>
        <p>Silakan periksa kembali data pembayaran Anda dan ajukan ulang jika diperlukan.</p>
        <p>Untuk bantuan, silakan hubungi tim support kami.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px; text-align: center;">
            Email ini dikirim otomatis oleh sistem Qalcuity ERP.
        </p>
    </div>
</div>""",
            {
                "payment_name": self.name,
                "subscription": self.subscription,
                "amount": self.amount,
                "currency": self.currency or "IDR",
                "payment_date": self.payment_date,
                "rejection_reason": self.rejection_reason,
            },
        )

        frappe.sendmail(
            recipients=[recipient_email],
            subject=subject,
            message=message,
        )

    def send_approval_email(self, recipient_email):
        """Kirim email notifikasi persetujuan payment."""
        subject = _("Pembayaran {0} Disetujui - Qalcuity ERP").format(self.name)

        message = frappe.render_template(
            """<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color: #4caf50; color: white; padding: 20px; text-align: center;">
        <h2 style="margin: 0;">Qalcuity ERP</h2>
        <p style="margin: 5px 0 0 0;">Notifikasi Persetujuan Pembayaran</p>
    </div>
    <div style="padding: 20px; background-color: #ffffff; border: 1px solid #e0e0e0;">
        <p>Halo,</p>
        <p>Pembayaran Anda dengan detail berikut telah <strong style="color: #4caf50;">DISETUJUI</strong>:</p>
        <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">ID Pembayaran</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{{ payment_name }}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Subscription</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{{ subscription }}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Jumlah</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{{ currency }} {{ amount }}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Tanggal Pembayaran</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{{ payment_date }}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Metode Pembayaran</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{{ payment_method }}</td>
            </tr>
        </table>
        <p>Subscription Anda akan segera diaktifkan. Anda akan menerima email konfirmasi terpisah setelah aktivasi selesai.</p>
        <p>Terima kasih telah melakukan pembayaran.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px; text-align: center;">
            Email ini dikirim otomatis oleh sistem Qalcuity ERP.
        </p>
    </div>
</div>""",
            {
                "payment_name": self.name,
                "subscription": self.subscription,
                "amount": self.amount,
                "currency": self.currency or "IDR",
                "payment_date": self.payment_date,
                "payment_method": self.payment_method or "Bank Transfer",
            },
        )

        frappe.sendmail(
            recipients=[recipient_email],
            subject=subject,
            message=message,
        )

    def notify_rejection(self):
        """Notifikasi penolakan payment — kirim email ke customer."""
        frappe.msgprint(
            _("Payment {0} has been rejected.").format(self.name),
            indicator="red",
        )

        # Kirim email notifikasi ke customer
        customer_email = self.get_customer_email()
        if customer_email:
            try:
                self.send_rejection_email(customer_email)
            except Exception as e:
                frappe.log_error(
                    message=f"Gagal mengirim email penolakan untuk {self.name}: {str(e)}",
                    title="Qalcuity Payment Rejection Email Error",
                )

    def notify_superadmin_new_payment(self):
        """Kirim email notifikasi ke superadmin saat ada payment baru."""
        try:
            superadmin_email = _get_superadmin_email()
            if not superadmin_email:
                return

            # Ambil nama customer
            customer_name = "Unknown"
            if self.subscription:
                customer_name = frappe.db.get_value(
                    "Qalcuity Subscription", self.subscription, "customer"
                ) or "Unknown"

            site_url = get_url()
            review_url = f"{site_url}/admin-reviews"

            subject = _(
                "Pembayaran Baru — {0} — {1} {2}"
            ).format(
                customer_name, self.currency or "IDR", self.amount
            )

            message = frappe.render_template(
                """<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color: #2490EF; color: white; padding: 20px; text-align: center;">
        <h2 style="margin: 0;">Qalcuity ERP</h2>
        <p style="margin: 5px 0 0 0;">Notifikasi Pembayaran Baru</p>
    </div>
    <div style="padding: 20px; background-color: #ffffff; border: 1px solid #e0e0e0;">
        <p>Halo Admin,</p>
        <p>Seorang customer telah mengirimkan bukti pembayaran baru yang perlu direview:</p>
        <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">ID Pembayaran</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{{ payment_name }}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Customer</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{{ customer_name }}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Subscription</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{{ subscription }}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Jumlah</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{{ currency }} {{ amount }}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Metode Pembayaran</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{{ payment_method }}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Tanggal Pembayaran</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{{ payment_date }}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Nomor Referensi</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{{ reference_number or "-" }}</td>
            </tr>
        </table>
        <div style="text-align: center; margin: 25px 0;">
            <a href="{{ review_url }}" style="background-color: #2490EF; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">Review Sekarang</a>
        </div>
        <p>Silakan login ke dashboard admin untuk melakukan review dan verifikasi pembayaran.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px; text-align: center;">
            Email ini dikirim otomatis oleh sistem Qalcuity ERP.
        </p>
    </div>
</div>""",
                {
                    "payment_name": self.name,
                    "customer_name": customer_name,
                    "subscription": self.subscription or "-",
                    "amount": self.amount,
                    "currency": self.currency or "IDR",
                    "payment_method": self.payment_method or "Bank Transfer",
                    "payment_date": self.payment_date,
                    "reference_number": self.reference_number,
                    "review_url": review_url,
                },
            )

            frappe.sendmail(
                recipients=[superadmin_email],
                subject=subject,
                message=message,
            )
        except Exception as e:
            frappe.log_error(
                message=f"Gagal mengirim email notifikasi superadmin untuk payment {self.name}: {str(e)}",
                title="Qalcuity - Superadmin Notification Email Error",
            )

    def _notify_superadmin_in_app(self):
        """Buat in-app notification ke superadmin users."""
        try:
            from qalcuity.api.notification import create_notification

            # Ambil semua superadmin users
            superadmin_users = frappe.get_all(
                "Has Role",
                filters={
                    "parenttype": "User",
                    "role": "Qalcuity Superadmin",
                },
                fields=["parent"],
            )

            customer_name = "Unknown"
            if self.subscription:
                customer_name = frappe.db.get_value(
                    "Qalcuity Subscription", self.subscription, "customer"
                ) or "Unknown"

            title = f"Pembayaran Baru — {customer_name}"
            message = (
                f"Payment {self.name} sebesar {self.currency or 'IDR'} {self.amount} "
                f"dari {customer_name} menunggu review."
            )

            for user_role in superadmin_users:
                create_notification(
                    recipient=user_role.parent,
                    notification_type="Payment",
                    title=title,
                    message=message,
                    link="/admin-reviews",
                    reference_doctype="Qalcuity Payment",
                    reference_name=self.name,
                )
        except Exception as e:
            frappe.log_error(
                message=f"Gagal membuat in-app notifikasi superadmin untuk payment {self.name}: {str(e)}",
                title="Qalcuity - Superadmin In-App Notification Error",
            )

    def _notify_customer_in_app(self, title, message, link=None):
        """Buat in-app notification ke customer."""
        try:
            from qalcuity.api.notification import create_notification

            # Ambil customer user
            customer_email = self.get_customer_email()
            if not customer_email:
                return

            # Resolve ke user name
            user = frappe.db.get_value("User", {"email": customer_email}, "name")
            if not user:
                return

            status_type = "Payment"
            if "Ditolak" in title:
                notification_type = "Payment"
            elif "Disetujui" in title:
                notification_type = "Payment"
            else:
                notification_type = "System"

            create_notification(
                recipient=user,
                notification_type=notification_type,
                title=title,
                message=message,
                link=link,
                reference_doctype="Qalcuity Payment",
                reference_name=self.name,
            )
        except Exception as e:
            frappe.log_error(
                message=f"Gagal membuat in-app notifikasi customer untuk payment {self.name}: {str(e)}",
                title="Qalcuity - Customer In-App Notification Error",
            )

    @frappe.whitelist()
    def approve(self):
        """Approve payment.

        Flow:
        1. Set status → Approved
        2. Set reviewed_by & review_date
        3. Save (triggers on_update → activate_subscription)
        4. Kirim approval email
        """
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

        # Kirim email notifikasi persetujuan ke customer
        customer_email = self.get_customer_email()
        if customer_email:
            try:
                self.send_approval_email(customer_email)
            except Exception as e:
                frappe.log_error(
                    message=f"Gagal mengirim email persetujuan untuk {self.name}: {str(e)}",
                    title="Qalcuity Payment Approval Email Error",
                )

    @frappe.whitelist()
    def reject(self, reason=None):
        """Reject payment.

        Flow:
        1. Set status → Rejected
        2. Set rejection_reason
        3. Save (triggers on_update → notify_rejection)
        4. Subscription TIDAK diubah — tetap "Pending Payment"
        5. Customer bisa submit payment baru
        """
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


def _get_superadmin_email():
    """Get superadmin notification email from settings.

    Returns:
        str: Email address superadmin atau fallback.
    """
    try:
        settings = frappe.get_single("Qalcuity Settings")
        if settings.notify_superadmin_on_payment and settings.superadmin_notification_email:
            return settings.superadmin_notification_email
    except Exception:
        pass
    return (
        frappe.db.get_single_value("System Settings", "email_footer_address")
        or "info@qalcuity.com"
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
            user_customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
            if customer and user_customer and customer == user_customer:
                return True
        return False

    return False
