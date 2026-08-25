# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Patch: Seed initial bank accounts for Qalcuity Settings

This patch populates the Qalcuity Settings with 4 bank accounts:
- BRI: 2118 0100 8728 508
- JAGO: 106818913479
- BTN: 5901500292405
- BSI: 7243220925

All accounts a/n: WAHYU DEDIK DWI ASTONO

Created: 2026-08-24
Reason: Sprint 5 — multiple bank accounts support for manual transfer payments.
"""


BANK_ACCOUNTS = [
    {
        "bank_name": "Bank BRI",
        "account_name": "WAHYU DEDIK DWI ASTONO",
        "account_number": "211801008728508",
        "bank_branch": "",
    },
    {
        "bank_name": "Bank JAGO",
        "account_name": "WAHYU DEDIK DWI ASTONO",
        "account_number": "106818913479",
        "bank_branch": "",
    },
    {
        "bank_name": "Bank BTN",
        "account_name": "WAHYU DEDIK DWI ASTONO",
        "account_number": "5901500292405",
        "bank_branch": "",
    },
    {
        "bank_name": "Bank BSI",
        "account_name": "WAHYU DEDIK DWI ASTONO",
        "account_number": "7243220925",
        "bank_branch": "",
    },
]


def execute():
    """Seed 4 bank accounts into Qalcuity Settings."""
    import frappe

    # Ensure the DocType is loaded before accessing
    frappe.reload_doctype("Qalcuity Settings", force=True)

    settings = frappe.get_single("Qalcuity Settings")

    # Check if bank_accounts already populated — skip if so
    if settings.bank_accounts and len(settings.bank_accounts) > 0:
        frappe.log_error(
            message="Seed bank accounts skipped: bank accounts already exist.",
            title="Qalcuity Seed Bank Accounts",
        )
        return

    # Add bank accounts as child table rows
    for bank in BANK_ACCOUNTS:
        settings.append("bank_accounts", bank)

    # Skip mandatory validation — patch only adds bank accounts,
    # other required fields (company_name, superadmin_email, payment_mode)
    # will be configured by admin via UI later.
    settings.flags.ignore_mandatory = True
    settings.save(ignore_permissions=True)
    frappe.db.commit()

    frappe.log_error(
        message=f"Seed bank accounts completed: {len(BANK_ACCOUNTS)} accounts added.",
        title="Qalcuity Seed Bank Accounts",
    )
