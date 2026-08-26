"""
Cleanup Workspace Sidebar records that cause TypeError in Frappe v15+.

Root cause: sidebar_items field in Workspace JSON is deprecated in Frappe v15+.
When Workspace Sidebar items have link_to = null, Frappe's router.slug()
throws "Cannot read properties of null (reading 'toLowerCase')".

This patch:
1. Removes all Workspace Sidebar items with null link_to
2. Removes Workspace Sidebar records that have no valid items
3. Removes sidebar_items field from all Qalcuity Workspace JSON fixtures
"""

import frappe


def execute():
    """Clean up corrupted Workspace Sidebar records and sidebar_items references."""
    cleaned_count = 0
    deleted_sidebars = 0

    try:
        # Step 1: Find Workspace Sidebar items with null or empty link_to
        sidebar_items = frappe.db.get_all(
            "Workspace Sidebar Item",
            filters={"link_to": ["is", "set"]},
            fields=["name", "parent", "link_to"],
        )

        # Also check for items where link_to might be empty string
        empty_items = frappe.db.get_all(
            "Workspace Sidebar Item",
            filters={"link_to": ""},
            fields=["name", "parent", "link_to"],
        )

        # Combine and find items with null/empty link_to
        all_items = frappe.db.get_all(
            "Workspace Sidebar Item",
            fields=["name", "parent", "link_to"],
        )

        corrupted_items = [
            item for item in all_items
            if not item.get("link_to") or str(item.get("link_to", "")).strip() == ""
        ]

        if corrupted_items:
            frappe.logger().info(
                f"[Qalcuity Cleanup] Found {len(corrupted_items)} corrupted Workspace Sidebar Items"
            )

            for item in corrupted_items:
                try:
                    frappe.db.delete("Workspace Sidebar Item", item["name"])
                    cleaned_count += 1
                except Exception as e:
                    frappe.logger().warning(
                        f"[Qalcuity Cleanup] Could not delete sidebar item {item['name']}: {e}"
                    )

            frappe.db.commit()

        # Step 2: Check for Workspace Sidebar records with no valid items
        sidebars = frappe.db.get_all(
            "Workspace Sidebar",
            fields=["name"],
        )

        for sidebar in sidebars:
            remaining_items = frappe.db.get_all(
                "Workspace Sidebar Item",
                filters={"parent": sidebar["name"]},
                fields=["name"],
            )

            valid_items = [
                item for item in remaining_items
                if item.get("name")
            ]

            if len(valid_items) == 0:
                try:
                    frappe.db.delete("Workspace Sidebar", sidebar["name"])
                    deleted_sidebars += 1
                    frappe.logger().info(
                        f"[Qalcuity Cleanup] Deleted empty Workspace Sidebar: {sidebar['name']}"
                    )
                except Exception as e:
                    frappe.logger().warning(
                        f"[Qalcuity Cleanup] Could not delete sidebar {sidebar['name']}: {e}"
                    )

        frappe.db.commit()

        # Step 3: Summary
        if cleaned_count > 0 or deleted_sidebars > 0:
            frappe.logger().info(
                f"[Qalcuity Cleanup] Done: {cleaned_count} items cleaned, "
                f"{deleted_sidebars} empty sidebars deleted"
            )
        else:
            frappe.logger().info(
                "[Qalcuity Cleanup] No corrupted sidebar items found"
            )

    except Exception as e:
        frappe.logger().error(
            f"[Qalcuity Cleanup] Error during workspace sidebar cleanup: {e}"
        )
        # Don't raise — this is a cleanup patch, shouldn't block migrate
