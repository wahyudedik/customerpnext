# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Scheduled tasks for Qalcuity ERP.
Handles background jobs like subscription expiry checks.
"""

import frappe
from frappe import _
from frappe.utils import getdate, nowdate, add_days, get_datetime


def check_subscription_expiry():
    """
    Daily task: Check for subscriptions that are about to expire or have expired.
    - Mark expired subscriptions
    - Send warning notifications before expiry
    """
    settings = frappe.get_single("Qalcuity Settings")
    warning_days = settings.subscription_expiry_warning_days or 7

    # Get active subscriptions
    active_subs = frappe.get_all(
        "Qalcuity Subscription",
        filters={"status": "Active", "end_date": ["is", "set"]},
        fields=["name", "customer", "plan", "end_date", "is_trial"],
    )

    today = getdate(nowdate())

    for sub in active_subs:
        end_date = getdate(sub.end_date)

        # Check if expired
        if end_date < today:
            _expire_subscription(sub)
            continue

        # Check if warning needed
        days_remaining = (end_date - today).days
        if days_remaining <= warning_days:
            _send_expiry_warning(sub, days_remaining)


def _expire_subscription(sub):
    """
    Mark a subscription as expired and suspend its tenant.

    Args:
        sub: Subscription dict with name, customer, plan fields
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
        tenant = frappe.db.get_value(
            "Qalcuity Tenant",
            {"customer": sub.customer, "status": "Active"},
            "name",
        )
        if tenant:
            frappe.db.set_value("Qalcuity Tenant", tenant, "status", "Suspended")

        frappe.db.commit()

        frappe.logger().info(
            "Qalcuity: Subscription {0} expired for customer {1}".format(
                sub.name, sub.customer
            )
        )

    except Exception:
        frappe.log_error(
            title="Qalcuity: Failed to expire subscription {0}".format(sub.name)
        )


def _send_expiry_warning(sub, days_remaining):
    """
    Send expiry warning notification.

    Args:
        sub: Subscription dict
        days_remaining: Number of days until expiry
    """
    try:
        customer_email = frappe.db.get_value("Customer", sub.customer, "email_id")
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


def seed_initial_data():
    """Manually seed initial data for Qalcuity ERP."""
    import json
    import os

    # Seed Qalcuity Settings if not exists
    if not frappe.db.exists("Qalcuity Settings", "Qalcuity Settings"):
        settings = frappe.get_doc({
            "doctype": "Qalcuity Settings",
            "company_name": "Qalcuity ERP",
            "superadmin_email": "admin@qalcuity.com",
            "max_file_size_mb": 10,
            "subscription_expiry_warning_days": 7,
            "enable_trial_period": 1,
            "trial_period_days": 14,
            "currency": "IDR"
        })
        settings.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✓ Qalcuity Settings created")

    # Seed Plans if not exists
    plans = [
        {"plan_name": "Starter", "price": 99000, "max_users": 2, "max_storage_gb": 1, "is_trial": 0, "sort_order": 1},
        {"plan_name": "Professional", "price": 299000, "max_users": 10, "max_storage_gb": 5, "is_trial": 0, "sort_order": 2},
        {"plan_name": "Enterprise", "price": 799000, "max_users": 50, "max_storage_gb": 20, "is_trial": 0, "sort_order": 3},
        {"plan_name": "Trial", "price": 0, "max_users": 5, "max_storage_gb": 1, "is_trial": 1, "sort_order": 0},
    ]

    for plan_data in plans:
        if not frappe.db.exists("Qalcuity Plan", plan_data["plan_name"]):
            doc = frappe.get_doc({
                "doctype": "Qalcuity Plan",
                "plan_name": plan_data["plan_name"],
                "price": plan_data["price"],
                "currency": "IDR",
                "billing_period": "Monthly",
                "max_users": plan_data["max_users"],
                "max_storage_gb": plan_data["max_storage_gb"],
                "is_active": 1,
                "is_trial": plan_data["is_trial"],
                "sort_order": plan_data["sort_order"],
            })
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"✓ Plan '{plan_data['plan_name']}' created")

    print("Seeding completed!")
