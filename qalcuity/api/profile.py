# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Profile API endpoints for Qalcuity ERP.
Provides whitelisted methods for customer profile management.
"""

import frappe
from frappe import _


@frappe.whitelist()
def get_profile():
    """
    Get profile data for the currently logged-in user.
    Returns user info, customer info, and tenant info.

    Returns:
        dict: Profile data with user, customer, and tenant information
    """
    user = frappe.session.user

    if user == "Guest":
        frappe.throw(_("Silakan login untuk mengakses profil."))

    user_doc = frappe.get_doc("User", user)

    # Get customer linked to user
    customer_name = frappe.db.get_value(
        "Portal User", {"user": user, "parenttype": "Customer"}, "parent"
    )

    customer = None
    if customer_name:
        customer_doc = frappe.get_doc("Customer", customer_name)
        customer = {
            "name": customer_doc.name,
            "customer_name": customer_doc.customer_name,
            "customer_group": customer_doc.customer_group,
            "territory": customer_doc.territory,
        }

    # Get tenant info
    tenant = None
    if customer_name:
        tenant_doc = frappe.db.get_value(
            "Qalcuity Tenant",
            {"customer": customer_name},
            ["name", "tenant_id", "status", "creation"],
            as_dict=True,
        )
        if tenant_doc:
            tenant = {
                "name": tenant_doc.name,
                "tenant_id": tenant_doc.tenant_id,
                "status": tenant_doc.status,
                "created": str(tenant_doc.creation) if tenant_doc.creation else None,
            }

    # Get user roles (excluding standard Frappe roles)
    roles = [r.role for r in user_doc.roles]
    qalcuity_roles = [r for r in roles if r.startswith("Qalcuity")]
    display_roles = qalcuity_roles if qalcuity_roles else ["Customer"]

    return {
        "user": {
            "name": user_doc.name,
            "full_name": user_doc.full_name,
            "email": user_doc.email,
            "phone": user_doc.phone,
            "company_name": user_doc.company_name,
            "user_image": user_doc.user_image,
            "creation": str(user_doc.creation) if user_doc.creation else None,
            "roles": display_roles,
        },
        "customer": customer,
        "tenant": tenant,
    }


@frappe.whitelist()
def update_profile(data):
    """
    Update profile data for the currently logged-in user.
    Allows updating: full_name, phone, company_name.

    Args:
        data: JSON string or dict with fields to update

    Returns:
        dict: Updated profile data
    """
    user = frappe.session.user

    if user == "Guest":
        frappe.throw(_("Silakan login untuk memperbarui profil."))

    # Parse data if string
    if isinstance(data, str):
        import json
        data = json.loads(data)

    if not data:
        frappe.throw(_("Data tidak boleh kosong."))

    # Allowed fields
    allowed_fields = ["full_name", "phone", "company_name"]
    update_data = {}

    for field in allowed_fields:
        if field in data:
            update_data[field] = data[field]

    if not update_data:
        frappe.throw(_("Tidak ada field yang valid untuk diperbarui."))

    # Update user document
    user_doc = frappe.get_doc("User", user)
    for field, value in update_data.items():
        user_doc.set(field, value)

    user_doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "message": _("Profil berhasil diperbarui."),
        "updated_fields": list(update_data.keys()),
    }


@frappe.whitelist()
def change_password(old_password, new_password):
    """
    Change password for the currently logged-in user.
    Validates old password before allowing change.

    Args:
        old_password: Current password
        new_password: New password

    Returns:
        dict: Success status
    """
    user = frappe.session.user

    if user == "Guest":
        frappe.throw(_("Silakan login untuk mengubah password."))

    if not old_password:
        frappe.throw(_("Password lama tidak boleh kosong."))

    if not new_password:
        frappe.throw(_("Password baru tidak boleh kosong."))

    if len(new_password) < 6:
        frappe.throw(_("Password baru minimal 6 karakter."))

    if old_password == new_password:
        frappe.throw(_("Password baru harus berbeda dari password lama."))

    # Validate old password
    from frappe.utils.password import check_password
    try:
        check_password(user, old_password)
    except frappe.AuthenticationError:
        frappe.throw(_("Password lama tidak sesuai."))

    # Update password
    from frappe.utils.password import update_password
    update_password(user, new_password)

    frappe.db.commit()

    return {
        "success": True,
        "message": _("Password berhasil diubah."),
    }
