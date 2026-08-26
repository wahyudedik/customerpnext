# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Scheduled tasks for Qalcuity ERP.
Handles background jobs like subscription expiry checks with grace period.
"""

import frappe
from frappe import _
from frappe.utils import getdate, nowdate, add_days, get_datetime


# Grace period: subscription tetap "Active" selama 7 hari setelah end_date
GRACE_PERIOD_DAYS = 7


def check_subscription_expiry():
    """
    Daily task: Check for subscriptions that are about to expire or have expired.
    - Grace period: subscription tetap "Active" selama 7 hari setelah end_date
    - Mark expired subscriptions (setelah grace period)
    - Suspend tenant untuk subscription expired
    - Send warning notifications before expiry
    - Kirim email notifikasi expired ke customer
    """
    settings = frappe.get_single("Qalcuity Settings")
    warning_days = settings.subscription_expiry_warning_days or 7

    # Get active + grace period subscriptions that have an end_date
    active_subs = frappe.get_all(
        "Qalcuity Subscription",
        filters={
            "status": ["in", ["Active", "Grace Period"]],
            "end_date": ["is", "set"],
        },
        fields=["name", "customer", "plan", "end_date", "is_trial", "tenant"],
    )

    today = getdate(nowdate())

    for sub in active_subs:
        end_date = getdate(sub.end_date)
        grace_end_date = add_days(end_date, GRACE_PERIOD_DAYS)

        # Check if past grace period → expire
        if grace_end_date < today:
            _expire_subscription(sub)
            continue

        # Check if past end_date but within grace period → set "Grace Period" status + warn
        if end_date < today:
            days_in_grace = (today - end_date).days
            remaining_grace = GRACE_PERIOD_DAYS - days_in_grace

            # Set status to "Grace Period" if not already
            current_status = frappe.db.get_value(
                "Qalcuity Subscription", sub.name, "status"
            )
            if current_status != "Grace Period":
                frappe.db.set_value(
                    "Qalcuity Subscription",
                    sub.name,
                    {"status": "Grace Period"},
                )
                frappe.db.commit()
                frappe.logger().info(
                    "Qalcuity: Subscription {0} entered grace period ({1} days remaining)".format(
                        sub.name, remaining_grace
                    )
                )

            _send_grace_period_warning(sub, remaining_grace)
            continue

        # Check if warning needed (before end_date)
        days_remaining = (end_date - today).days
        if days_remaining <= warning_days:
            _send_expiry_warning(sub, days_remaining)


def _expire_subscription(sub):
    """
    Mark a subscription as expired and suspend its tenant.
    Triggers ERP deprovisioning if tenant was provisioned.
    Sends expiry notification email to customer.

    Args:
        sub: Subscription dict with name, customer, plan, tenant fields
    """
    try:
        frappe.db.set_value(
            "Qalcuity Subscription",
            sub.name,
            {
                "status": "Expired",
            },
        )

        # Suspend tenant
        tenant_name = sub.get("tenant")
        if not tenant_name:
            tenant_name = frappe.db.get_value(
                "Qalcuity Tenant",
                {"customer": sub.customer, "status": "Active"},
                "name",
            )

        if tenant_name:
            frappe.db.set_value("Qalcuity Tenant", tenant_name, "status", "Suspended")

            # Trigger ERP deprovisioning (remove ERP roles)
            _trigger_deprovision_on_expiry(tenant_name)

        frappe.db.commit()

        frappe.logger().info(
            "Qalcuity: Subscription {0} expired for customer {1}".format(
                sub.name, sub.customer
            )
        )

        # Send expiry notification email
        _send_expired_email(sub)

    except Exception:
        frappe.log_error(
            title="Qalcuity: Failed to expire subscription {0}".format(sub.name)
        )


def _send_expiry_warning(sub, days_remaining):
    """
    Send expiry warning notification (before end_date).

    Args:
        sub: Subscription dict
        days_remaining: Number of days until expiry
    """
    try:
        customer_email = _get_customer_email(sub.customer)
        if not customer_email:
            return

        plan_name = frappe.db.get_value("Qalcuity Plan", sub.plan, "plan_name")

        frappe.sendmail(
            recipients=[customer_email],
            subject=_("Your Qalcuity subscription is expiring soon"),
            message=_(
                "Dear Customer,<br><br>"
                "Your Qalcuity subscription for plan <b>{plan}</b> "
                "will expire in <b>{days}</b> day(s) on <b>{date}</b>.<br><br>"
                "Please renew your subscription to avoid service interruption.<br><br>"
                "Best regards,<br>Qalcuity Team"
            ).format(
                plan=plan_name,
                days=days_remaining,
                date=sub.end_date,
            ),
        )

    except Exception:
        frappe.log_error(
            title="Qalcuity: Failed to send expiry warning for {0}".format(sub.name)
        )


def _send_grace_period_warning(sub, remaining_grace_days):
    """
    Send grace period warning notification (after end_date, within grace period).
    Warns customer that their subscription will expire in X days.

    Args:
        sub: Subscription dict
        remaining_grace_days: Number of grace days remaining
    """
    try:
        # Avoid duplicate warnings: check if we already sent today
        cache_key = "qalcuity_grace_warn_{0}".format(sub.name)
        if frappe.cache().get_value(cache_key):
            return

        frappe.cache().set_value(cache_key, True, expires_in_sec=86400)

        customer_email = _get_customer_email(sub.customer)
        if not customer_email:
            return

        plan_name = frappe.db.get_value("Qalcuity Plan", sub.plan, "plan_name")

        frappe.sendmail(
            recipients=[customer_email],
            subject=_("⚠️ Your Qalcuity subscription grace period"),
            message=_(
                "Dear Customer,<br><br>"
                "Your Qalcuity subscription for plan <b>{plan}</b> has <b>expired</b>.<br><br>"
                "However, you are currently in a <b>grace period</b> of <b>{days}</b> day(s).<br><br>"
                "During this grace period, your access remains active. "
                "After the grace period ends, your subscription will be marked as "
                "<b>Expired</b> and your access will be restricted.<br><br>"
                "Please renew your subscription as soon as possible.<br><br>"
                "Best regards,<br>Qalcuity Team"
            ).format(
                plan=plan_name,
                days=remaining_grace_days,
            ),
        )

    except Exception:
        frappe.log_error(
            title="Qalcuity: Failed to send grace period warning for {0}".format(sub.name)
        )


def _send_expired_email(sub):
    """
    Send expired subscription notification email.

    Args:
        sub: Subscription dict
    """
    try:
        customer_email = _get_customer_email(sub.customer)
        if not customer_email:
            return

        plan_name = frappe.db.get_value("Qalcuity Plan", sub.plan, "plan_name")

        frappe.sendmail(
            recipients=[customer_email],
            subject=_("Your Qalcuity subscription has expired"),
            message=_(
                "Dear Customer,<br><br>"
                "Your Qalcuity subscription for plan <b>{plan}</b> has <b>expired</b>.<br><br>"
                "Your access to ERP features has been restricted. "
                "To continue using Qalcuity ERP, please renew your subscription.<br><br>"
                "You can renew by visiting <b>{site_url}/pricing</b>.<br><br>"
                "Best regards,<br>Qalcuity Team"
            ).format(
                plan=plan_name,
                site_url=frappe.utils.get_url(),
            ),
        )

    except Exception:
        frappe.log_error(
            title="Qalcuity: Failed to send expired email for {0}".format(sub.name)
        )


def _get_customer_email(customer_name):
    """
    Get customer email with multiple fallback strategies.

    Args:
        customer_name: Customer docname

    Returns:
        str or None: Email address
    """
    if not customer_name:
        return None

    # Strategy 1: Customer.email_id
    email = frappe.db.get_value("Customer", customer_name, "email_id")
    if email:
        return email

    # Strategy 2: Customer Email child table
    email = frappe.db.get_value(
        "Customer Email",
        {"parent": customer_name, "email_id": ["is", "set"]},
        "email_id",
    )
    if email:
        return email

    # Strategy 3: Portal User → User.email
    portal_user = frappe.db.get_value(
        "Portal User",
        {"parent": customer_name, "parenttype": "Customer"},
        "user",
    )
    if portal_user:
        user_email = frappe.db.get_value("User", portal_user, "email")
        if user_email:
            return user_email

    return None


# =============================================================================
# ERP Provisioning on Subscription Expiry
# =============================================================================


def _trigger_deprovision_on_expiry(tenant_name):
    """
    Trigger ERP deprovisioning when subscription expires via scheduler.

    Note: This uses frappe.db.set_value directly (not the DocType on_update hook),
    so we need to explicitly trigger deprovisioning here.

    Args:
        tenant_name: Name of the Qalcuity Tenant document
    """
    try:
        tenant = frappe.get_doc("Qalcuity Tenant", tenant_name)
        if tenant.erp_provisioning_status == "Completed":
            from qalcuity.provisioning import deprovision_tenant
            result = deprovision_tenant(tenant_name)
            frappe.logger().info(
                "Qalcuity Scheduler: Deprovisioned tenant {0} after expiry — {1}".format(
                    tenant_name, result.get("status", "unknown")
                )
            )
    except Exception as e:
        frappe.log_error(
            title="Qalcuity Scheduler: Deprovisioning failed for {0}".format(tenant_name),
            message=str(e),
        )


# =============================================================================
# Backup Scheduler
# =============================================================================


def run_scheduled_backup():
    """
    Daily backup task — called by scheduler_events.

    Menjalankan backup otomatis (Full) dan cleanup backup lama.
    Dipanggil oleh Frappe scheduler via hooks.py:
        scheduler_events -> daily -> qalcuity.tasks.run_scheduled_backup

    Flow:
        1. Jalankan Full backup (database + files)
        2. Cleanup backup lama sesuai retention policy
        3. Log hasil ke Frappe error log
    """
    try:
        from qalcuity.backup import run_backup, cleanup_old_backups

        # Step 1: Run backup
        frappe.logger().info("Qalcuity Scheduler: Starting scheduled backup")
        result = run_backup(
            backup_type="Full",
            performed_by="Scheduler",
            notes="Scheduled daily backup",
        )
        frappe.logger().info(
            "Qalcuity Scheduler: Backup completed — {0}".format(
                result.get("backup_name", "unknown")
            )
        )

        # Step 2: Cleanup old backups
        cleanup_result = cleanup_old_backups()
        if cleanup_result.get("deleted_count", 0) > 0:
            frappe.logger().info(
                "Qalcuity Scheduler: Cleanup removed {0} old backups".format(
                    cleanup_result["deleted_count"]
                )
            )

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Scheduler: Scheduled backup failed",
            message=str(e),
        )


# =============================================================================
# ERP Provisioning Retry Scheduler
# =============================================================================


def retry_failed_provisioning():
    """
    Daily task: Retry any tenant with provisioning_status='Failed'.
    Called from hooks.py scheduler_events -> daily.

    Flow:
        1. Find all Active tenants with erp_provisioning_status='Failed'
        2. Retry provisioning for each
        3. Log results
    """
    try:
        from qalcuity.provisioning import retry_failed_provisioning as do_retry

        frappe.logger().info(
            "Qalcuity Scheduler: Starting failed provisioning retry"
        )
        result = do_retry()
        frappe.logger().info(
            "Qalcuity Scheduler: Provisioning retry completed — {0}".format(
                frappe.as_json(result)
            )
        )

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Scheduler: Provisioning retry failed",
            message=str(e),
        )


# =============================================================================
# Renewal Reminder Scheduler
# =============================================================================


def check_renewal_reminders():
    """
    Daily: send renewal reminders for expiring subscriptions.
    Called from hooks.py scheduler_events -> daily.

    Flow:
        1. Import and call check_and_send_renewal_reminders from renewal API
        2. Handles Active subscriptions expiring within warning_days
        3. Handles Grace Period subscriptions approaching final expiry
    """
    try:
        from qalcuity.api.renewal import check_and_send_renewal_reminders

        frappe.logger().info(
            "Qalcuity Scheduler: Starting renewal reminder check"
        )
        check_and_send_renewal_reminders()
        frappe.logger().info(
            "Qalcuity Scheduler: Renewal reminder check completed"
        )

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Scheduler: Renewal reminder check failed",
            message=str(e),
        )


# Catatan: seed_initial_data() dihapus karena sudah ditangani oleh fixtures di hooks.py
