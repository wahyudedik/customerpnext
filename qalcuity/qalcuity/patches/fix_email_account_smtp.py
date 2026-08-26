import frappe


def execute():
    """
    Fix Email Account 'Qalcuity Mail' SMTP credentials.
    Update SMTP settings using frappe.db.set_value() to bypass Frappe validation.
    """
    if not frappe.db.exists("Email Account", "Qalcuity Mail"):
        frappe.log_error(
            message="Patch fix_email_account_smtp: Email Account 'Qalcuity Mail' not found. Skipping.",
            title="Qalcuity Patch",
        )
        return

    smtp_settings = {
        "smtp_server": "mail.noteds.com",
        "smtp_port": 465,
        "smtp_username": "info@noteds.com",
        "smtp_password": "Wahyu123456789@",
        "use_ssl": 1,
        "enable_incoming": 0,
        "enable_outgoing": 1,
        "default_incoming": 0,
        "default_outgoing": 1,
        "awaiting_password": 0,
    }

    frappe.db.set_value("Email Account", "Qalcuity Mail", smtp_settings)
    frappe.db.commit()

    frappe.log_error(
        message=(
            "Patch fix_email_account_smtp: Email Account 'Qalcuity Mail' SMTP settings updated successfully.\n"
            "  smtp_server=mail.noteds.com, smtp_port=465, smtp_username=info@noteds.com\n"
            "  use_ssl=1, enable_outgoing=1, default_outgoing=1, awaiting_password=0"
        ),
        title="Qalcuity Patch",
    )
