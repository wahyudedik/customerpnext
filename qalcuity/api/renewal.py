# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Renewal Reminder API for Qalcuity ERP.
Handles automated and manual renewal reminder emails/notifications
for subscriptions that are about to expire.
"""

import frappe
from frappe import _
from frappe.utils import getdate, nowdate, add_days, now_datetime


# =============================================================================
# Scheduler Task — Daily Renewal Reminder
# =============================================================================


def check_and_send_renewal_reminders():
    """
    Dipanggil oleh scheduler (daily).
    Cek subscription yang akan expired dalam X hari.
    Kirim reminder email + in-app notification ke customer.

    Flow:
        1. Baca warning_days dari Qalcuity Settings
        2. Query Active subscriptions yang end_date <= today + warning_days
        3. Query subscriptions dalam Grace Period
        4. Kirim email reminder + in-app notification
        5. Anti-duplicate: cek cache sebelum kirim
        6. Log ke audit
    """
    try:
        settings = frappe.get_single("Qalcuity Settings")
        warning_days = settings.subscription_expiry_warning_days or 7

        today = getdate(nowdate())
        warning_cutoff = add_days(today, warning_days)

        # --- Part 1: Active subscriptions yang akan expired dalam X hari ---
        expiring_subs = frappe.get_all(
            "Qalcuity Subscription",
            filters={
                "status": "Active",
                "end_date": ["is", "set"],
                "end_date": [">", today],
                "end_date": ["<=", warning_cutoff],
            },
            fields=["name", "customer", "plan", "end_date", "tenant"],
        )

        for sub in expiring_subs:
            end_date = getdate(sub.end_date)
            days_remaining = (end_date - today).days
            _send_renewal_reminder_email(sub, days_remaining, "expiring")

        # --- Part 2: Subscriptions dalam Grace Period ---
        grace_subs = frappe.get_all(
            "Qalcuity Subscription",
            filters={
                "status": "Grace Period",
                "end_date": ["is", "set"],
            },
            fields=["name", "customer", "plan", "end_date", "tenant"],
        )

        for sub in grace_subs:
            end_date = getdate(sub.end_date)
            grace_end = add_days(end_date, 7)
            days_until_final = (grace_end - today).days
            if days_until_final > 0:
                _send_renewal_reminder_email(sub, days_until_final, "grace_period")

        frappe.logger().info(
            "Qalcuity Renewal: Checked {0} expiring + {1} grace period subscriptions".format(
                len(expiring_subs), len(grace_subs)
            )
        )

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Renewal: check_and_send_renewal_reminders failed",
            message=str(e),
        )


def _send_renewal_reminder_email(sub, days_remaining, reminder_type):
    """
    Kirim email reminder + in-app notification untuk subscription yang mau expired.
    Anti-duplicate: menggunakan cache key per subscription per hari.

    Args:
        sub: Subscription dict (name, customer, plan, end_date, tenant)
        days_remaining: Sisa hari sampai expiry
        reminder_type: "expiring" atau "grace_period"
    """
    # Anti-duplicate: skip jika sudah dikirim hari ini
    today_str = str(getdate(nowdate()))
    cache_key = "qalcuity_renewal_remind_{0}_{1}".format(sub.name, today_str)
    if frappe.cache().get_value(cache_key):
        return

    try:
        customer_email = _get_customer_email(sub.customer)
        if not customer_email:
            frappe.logger().warning(
                "Qalcuity Renewal: No email found for customer {0}, skipping reminder".format(
                    sub.customer
                )
            )
            return

        plan_name = frappe.db.get_value("Qalcuity Plan", sub.plan, "plan_name") or "Unknown"
        end_date_str = str(getdate(sub.end_date))
        site_url = frappe.utils.get_url()
        pricing_url = "{0}/pricing".format(site_url)

        # --- Build email ---
        if reminder_type == "grace_period":
            subject = "⚠️ Your Qalcuity subscription grace period is ending"
            status_text = (
                "Your subscription for plan <b>{plan}</b> is currently in the <b>grace period</b>."
            ).format(plan=plan_name)
            urgency_text = (
                "The grace period will end in <b>{days}</b> day(s) on <b>{date}</b>. "
                "After that, your ERP access will be completely restricted."
            ).format(days=days_remaining, date=end_date_str)
        else:
            subject = "Your Qalcuity subscription is expiring soon"
            status_text = (
                "Your subscription for plan <b>{plan}</b> is expiring soon."
            ).format(plan=plan_name)
            urgency_text = (
                "Your subscription will expire in <b>{days}</b> day(s) on <b>{date}</b>. "
                "Please renew to avoid service interruption."
            ).format(days=days_remaining, date=end_date_str)

        message = _build_renewal_email_html(
            plan_name=plan_name,
            status_text=status_text,
            urgency_text=urgency_text,
            days_remaining=days_remaining,
            pricing_url=pricing_url,
        )

        # --- Send email ---
        frappe.sendmail(
            recipients=[customer_email],
            subject=_(subject),
            message=message,
        )

        # --- Mark as sent in cache (expires in 24 hours) ---
        frappe.cache().set_value(cache_key, True, expires_in_sec=86400)

        frappe.logger().info(
            "Qalcuity Renewal: Sent {0} reminder for subscription {1} to {2} ({3} days remaining)".format(
                reminder_type, sub.name, customer_email, days_remaining
            )
        )

        # --- In-app notification ---
        _create_renewal_notification(sub, days_remaining, reminder_type, plan_name, end_date_str)

        # --- Audit log ---
        _log_renewal_reminder(sub.name, sub.customer, reminder_type, days_remaining)

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Renewal: Failed to send reminder for {0}".format(sub.name),
            message=str(e),
        )


def _build_renewal_email_html(plan_name, status_text, urgency_text, days_remaining, pricing_url):
    """
    Build HTML email body for renewal reminder.

    Returns:
        str: HTML email content
    """
    # Urgency color
    if days_remaining <= 2:
        urgency_color = "#dc3545"  # Red
    elif days_remaining <= 5:
        urgency_color = "#fd7e14"  # Orange
    else:
        urgency_color = "#2490EF"  # Blue

    return """
    <div style="max-width: 600px; margin: 0 auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <!-- Header -->
        <div style="background: {urgency_color}; padding: 30px; text-align: center; border-radius: 12px 12px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 24px;">⚠️ Subscription Reminder</h1>
        </div>

        <!-- Body -->
        <div style="background: #ffffff; padding: 30px; border: 1px solid #e2e8f0; border-top: none;">
            <p style="color: #334155; font-size: 16px; line-height: 1.6;">
                {status_text}
            </p>

            <div style="background: #fef2f2; border-left: 4px solid {urgency_color}; padding: 16px; margin: 20px 0; border-radius: 4px;">
                <p style="color: #334155; margin: 0; font-size: 15px;">
                    {urgency_text}
                </p>
            </div>

            <p style="color: #334155; font-size: 15px; line-height: 1.6;">
                To continue using Qalcuity ERP without interruption, please renew your subscription now.
            </p>

            <!-- CTA Button -->
            <div style="text-align: center; margin: 30px 0;">
                <a href="{pricing_url}"
                   style="display: inline-block; background: {urgency_color}; color: #ffffff;
                          text-decoration: none; padding: 14px 32px; border-radius: 8px;
                          font-size: 16px; font-weight: 600;">
                    Renew Now
                </a>
            </div>

            <p style="color: #94a3b8; font-size: 13px; text-align: center; margin-top: 20px;">
                If you have already renewed, please disregard this message.
            </p>
        </div>

        <!-- Footer -->
        <div style="background: #f8fafc; padding: 20px; text-align: center; border-radius: 0 0 12px 12px; border: 1px solid #e2e8f0; border-top: none;">
            <p style="color: #64748b; font-size: 13px; margin: 0;">
                &copy; 2026 Qalcuity ERP &mdash; SaaS ERP Platform
            </p>
            <p style="color: #94a3b8; font-size: 12px; margin: 8px 0 0 0;">
                This is an automated reminder. Please do not reply to this email.
            </p>
        </div>
    </div>
    """.format(
        urgency_color=urgency_color,
        status_text=status_text,
        urgency_text=urgency_text,
        pricing_url=pricing_url,
    )


def _create_renewal_notification(sub, days_remaining, reminder_type, plan_name, end_date_str):
    """
    Buat in-app notification untuk renewal reminder.

    Args:
        sub: Subscription dict
        days_remaining: Sisa hari
        reminder_type: "expiring" atau "grace_period"
        plan_name: Nama plan
        end_date_str: Tanggal expiry (string)
    """
    try:
        # Resolve customer user via Portal User
        portal_user = frappe.db.get_value(
            "Portal User",
            {"parent": sub.customer, "parenttype": "Customer"},
            "user",
        )
        if not portal_user:
            return

        if reminder_type == "grace_period":
            title = "⚠️ Grace Period Ending Soon"
            message = (
                "Your {plan} subscription grace period will end in {days} day(s) "
                "on {date}. Please renew to continue accessing ERP."
            ).format(plan=plan_name, days=days_remaining, date=end_date_str)
        else:
            title = "Subscription Expiring Soon"
            message = (
                "Your {plan} subscription will expire in {days} day(s) "
                "on {date}. Please renew to continue accessing ERP."
            ).format(plan=plan_name, days=days_remaining, date=end_date_str)

        notification = frappe.get_doc(
            {
                "doctype": "Qalcuity Notification",
                "recipient": portal_user,
                "notification_type": "System",
                "title": title,
                "message": message,
                "link": "/pricing",
                "timestamp": now_datetime(),
            }
        )
        notification.insert(ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        frappe.log_error(
            title="Qalcuity Renewal: Failed to create notification for {0}".format(sub.name),
            message=str(e),
        )


def _log_renewal_reminder(subscription_name, customer_name, reminder_type, days_remaining):
    """
    Log renewal reminder ke Frappe logger untuk audit trail.

    Args:
        subscription_name: Subscription docname
        customer_name: Customer docname
        reminder_type: "expiring" atau "grace_period"
        days_remaining: Sisa hari
    """
    try:
        frappe.logger().info(
            "Qalcuity Renewal Audit: reminder_type={0} subscription={1} customer={2} days_remaining={3} date={4}".format(
                reminder_type, subscription_name, customer_name, days_remaining, nowdate()
            )
        )
    except Exception:
        pass  # Audit log failure should not block the flow


# =============================================================================
# Customer API — Renewal Status
# =============================================================================


@frappe.whitelist()
def get_renewal_status():
    """
    Customer: status renewal subscription mereka.
    Return subscription info + days until expiry.

    Returns:
        dict: Subscription renewal information
    """
    user = frappe.session.user

    # Get customer linked to user
    customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
    if not customer:
        frappe.throw(_("No customer account found for current user."))

    # Get latest active/grace/expired subscription
    subscription = frappe.get_all(
        "Qalcuity Subscription",
        filters={
            "customer": customer,
            "status": ["in", ["Active", "Grace Period", "Expired"]],
        },
        fields=[
            "name",
            "plan",
            "status",
            "start_date",
            "end_date",
            "is_trial",
        ],
        order_by="creation desc",
        limit_page_length=1,
    )

    if not subscription:
        return {
            "has_subscription": False,
            "message": "No subscription found.",
        }

    sub = subscription[0]
    plan_name = frappe.db.get_value("Qalcuity Plan", sub.plan, "plan_name") or "Unknown"
    today = getdate(nowdate())

    result = {
        "has_subscription": True,
        "subscription_id": sub.name,
        "plan_name": plan_name,
        "status": sub.status,
        "start_date": str(sub.start_date) if sub.start_date else None,
        "end_date": str(sub.end_date) if sub.end_date else None,
        "is_trial": sub.is_trial,
        "days_remaining": 0,
        "is_expired": False,
        "is_grace_period": False,
        "pricing_url": "{0}/pricing".format(frappe.utils.get_url()),
    }

    if sub.end_date:
        end_date = getdate(sub.end_date)
        days_remaining = (end_date - today).days
        result["days_remaining"] = max(0, days_remaining)

        if sub.status == "Expired":
            result["is_expired"] = True
        elif sub.status == "Grace Period":
            result["is_grace_period"] = True
            grace_end = add_days(end_date, 7)
            result["grace_period_end"] = str(grace_end)
            result["days_until_final_expiry"] = max(0, (grace_end - today).days)
        elif days_remaining <= 0:
            result["is_expired"] = True

    return result


# =============================================================================
# Admin API — Manual Renewal Reminder
# =============================================================================


@frappe.whitelist()
def send_renewal_reminder(subscription_id):
    """
    Admin: manual kirim reminder ke customer tertentu.
    Tidak menggunakan anti-duplicate cache (manual trigger).

    Args:
        subscription_id: Name of Qalcuity Subscription

    Returns:
        dict: Result of the reminder sending
    """
    # Check permissions
    if not frappe.has_permission("Qalcuity Subscription", "write"):
        frappe.throw(_("Insufficient permissions to send renewal reminders."))

    # Validate subscription
    if not frappe.db.exists("Qalcuity Subscription", subscription_id):
        frappe.throw(_("Subscription {0} not found.").format(subscription_id))

    sub_data = frappe.get_all(
        "Qalcuity Subscription",
        filters={"name": subscription_id},
        fields=["name", "customer", "plan", "end_date", "status", "tenant"],
        limit_page_length=1,
    )

    if not sub_data:
        frappe.throw(_("Subscription {0} not found.").format(subscription_id))

    sub = sub_data[0]

    if sub.status not in ["Active", "Grace Period"]:
        frappe.throw(
            _("Cannot send renewal reminder for a {0} subscription.").format(sub.status)
        )

    customer_email = _get_customer_email(sub.customer)
    if not customer_email:
        frappe.throw(
            _("No email address found for customer {0}.").format(sub.customer)
        )

    plan_name = frappe.db.get_value("Qalcuity Plan", sub.plan, "plan_name") or "Unknown"
    today = getdate(nowdate())
    end_date = getdate(sub.end_date)
    days_remaining = max(0, (end_date - today).days)

    # Determine reminder type
    if sub.status == "Grace Period":
        reminder_type = "grace_period"
        grace_end = add_days(end_date, 7)
        days_remaining = max(0, (grace_end - today).days)
    else:
        reminder_type = "expiring"

    # Build and send email (bypass anti-duplicate for manual trigger)
    end_date_str = str(end_date)
    site_url = frappe.utils.get_url()
    pricing_url = "{0}/pricing".format(site_url)

    if reminder_type == "grace_period":
        subject = "⚠️ Your Qalcuity subscription grace period is ending"
        status_text = (
            "Your subscription for plan <b>{plan}</b> is currently in the <b>grace period</b>."
        ).format(plan=plan_name)
        urgency_text = (
            "The grace period will end in <b>{days}</b> day(s) on <b>{date}</b>. "
            "After that, your ERP access will be completely restricted."
        ).format(days=days_remaining, date=end_date_str)
    else:
        subject = "Your Qalcuity subscription is expiring soon"
        status_text = (
            "Your subscription for plan <b>{plan}</b> is expiring soon."
        ).format(plan=plan_name)
        urgency_text = (
            "Your subscription will expire in <b>{days}</b> day(s) on <b>{date}</b>. "
            "Please renew to avoid service interruption."
        ).format(days=days_remaining, date=end_date_str)

    message = _build_renewal_email_html(
        plan_name=plan_name,
        status_text=status_text,
        urgency_text=urgency_text,
        days_remaining=days_remaining,
        pricing_url=pricing_url,
    )

    frappe.sendmail(
        recipients=[customer_email],
        subject=_(subject),
        message=message,
    )

    # In-app notification
    _create_renewal_notification(sub, days_remaining, reminder_type, plan_name, end_date_str)

    frappe.logger().info(
        "Qalcuity Renewal: Admin manually sent {0} reminder for subscription {1} to {2}".format(
            reminder_type, sub.name, customer_email
        )
    )

    return {
        "success": True,
        "message": "Renewal reminder sent to {0}.".format(customer_email),
        "subscription": sub.name,
        "customer": sub.customer,
        "days_remaining": days_remaining,
    }


# =============================================================================
# Helper — Email Resolution (same pattern as tasks.py)
# =============================================================================


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
