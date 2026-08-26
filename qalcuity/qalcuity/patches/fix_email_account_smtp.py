import frappe


def execute():
    """
    Fix Email Account 'Qalcuity Mail' SMTP credentials.
    Update SMTP settings using frappe.db.set_value() to bypass Frappe validation.

    Field mapping (Frappe Email Account DocType):
      - smtp_username → login_id (SMTP login/email)
      - smtp_password → password  (encrypted password field)
      - use_ssl       → use_ssl_for_outgoing (SSL for outgoing SMTP)
    """
    try:
        if not frappe.db.exists("Email Account", "Qalcuity Mail"):
            frappe.log_error(
                message="Patch fix_email_account_smtp: Email Account 'Qalcuity Mail' not found. Skipping.",
                title="Qalcuity Patch",
            )
            return

        # Field names based on Frappe Email Account DocType JSON definition:
        #   login_id             = SMTP username/email (NOT smtp_username)
        #   password             = SMTP password (NOT smtp_password)
        #   use_ssl_for_outgoing = SSL toggle for outgoing (NOT use_ssl)
        smtp_settings = {
            "smtp_server": "mail.noteds.com",
            "smtp_port": 465,
            "login_id": "info@noteds.com",
            "password": "Wahyu123456789@",
            "use_ssl_for_outgoing": 1,
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
                "  smtp_server=mail.noteds.com, smtp_port=465, login_id=info@noteds.com\n"
                "  use_ssl_for_outgoing=1, enable_outgoing=1, default_outgoing=1, awaiting_password=0"
            ),
            title="Qalcuity Patch",
        )

    except Exception as e:
        frappe.log_error(
            message=(
                f"Patch fix_email_account_smtp: FAILED — {str(e)}\n"
                "SMTP settings for 'Qalcuity Mail' could not be updated. "
                "This patch will not block migration."
            ),
            title="Qalcuity Patch Error",
        )
        # Do NOT re-raise — allow migration to continue
