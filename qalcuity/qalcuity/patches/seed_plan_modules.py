# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Patch: Seed ERPNext modules ke Qalcuity Plan yang sudah ada.
Menambahkan enabled_modules child table berdasarkan plan type.
"""

import frappe


# Default module configurations per plan
PLAN_MODULE_CONFIG = {
    "Starter": [
        "Accounting",
        "Sales",
        "Purchasing",
    ],
    "Professional": [
        "Accounting",
        "CRM",
        "Sales",
        "Purchasing",
        "Inventory",
        "Projects",
        "HR",
    ],
    "Enterprise": [
        "Accounting",
        "CRM",
        "Sales",
        "Purchasing",
        "Inventory",
        "Projects",
        "HR",
        "Manufacturing",
        "Support",
        "Assets",
    ],
    "Trial": [
        "Accounting",
        "CRM",
        "Sales",
        "Purchasing",
        "Inventory",
        "Projects",
        "HR",
    ],
}


def execute():
    """Seed enabled_modules ke semua Qalcuity Plan yang belum punya."""
    plans = frappe.get_all("Qalcuity Plan", fields=["name", "plan_name"])

    for plan in plans:
        # Check if plan already has enabled_modules
        existing_count = frappe.db.count(
            "Qalcuity Plan Module",
            {"parent": plan.name},
        )

        if existing_count > 0:
            # Already has modules configured, skip
            continue

        # Get default config for this plan
        modules = PLAN_MODULE_CONFIG.get(plan.plan_name)
        if not modules:
            # Unknown plan — give all modules
            modules = [
                "Accounting", "CRM", "Sales", "Purchasing",
                "Inventory", "Projects", "HR", "Manufacturing",
                "Support", "Assets",
            ]

        # Update plan with enabled_modules
        plan_doc = frappe.get_doc("Qalcuity Plan", plan.name)
        for module_name in modules:
            plan_doc.append("enabled_modules", {"module_name": module_name})

        plan_doc.flags.ignore_permissions = True
        plan_doc.flags.ignore_validate = True
        plan_doc.save()

        frappe.logger().info(
            "Qalcuity Patch: Added {0} modules to plan '{1}'".format(
                len(modules), plan.plan_name
            )
        )

    frappe.db.commit()
    frappe.logger().info("Qalcuity Patch: seed_plan_modules completed successfully")
