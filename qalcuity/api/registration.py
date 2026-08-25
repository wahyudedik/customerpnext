# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Registration API endpoints for Qalcuity ERP.
Provides whitelisted methods for customer registration.
"""

import frappe
from frappe import _
import re


@frappe.whitelist(allow_guest=True)
def register_customer(full_name, email, password, company_name, phone):
    """
    Register a new customer.

    Creates: User → Customer → Portal User → Tenant (via hook)

    Args:
        full_name: Nama lengkap customer
        email: Email address (unique)
        password: Password (min 8 chars, kombinasi huruf+angka)
        company_name: Nama perusahaan
        phone: Nomor telepon

    Returns:
        dict: Success message with instructions
    """
    # ── 1. Validasi input ──────────────────────────────────────────────
    full_name = (full_name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""
    company_name = (company_name or "").strip()
    phone = (phone or "").strip()

    if not full_name:
        frappe.throw(_("Nama lengkap wajib diisi."))

    if not email:
        frappe.throw(_("Email wajib diisi."))

    if not password:
        frappe.throw(_("Password wajib diisi."))

    if not company_name:
        frappe.throw(_("Nama perusahaan wajib diisi."))

    if not phone:
        frappe.throw(_("Nomor telepon wajib diisi."))

    # ── 2. Validasi email format ───────────────────────────────────────
    email_regex = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_regex, email):
        frappe.throw(_("Format email tidak valid."))

    # ── 3. Cek email belum terdaftar ───────────────────────────────────
    if frappe.db.exists("User", {"email": email}):
        frappe.throw(
            _("Email {0} sudah terdaftar. Silakan gunakan email lain atau login.").format(
                email
            )
        )

    # ── 4. Validasi password strength ──────────────────────────────────
    if len(password) < 8:
        frappe.throw(_("Password minimal 8 karakter."))

    if not re.search(r"[a-zA-Z]", password):
        frappe.throw(_("Password harus mengandung minimal satu huruf."))

    if not re.search(r"[0-9]", password):
        frappe.throw(_("Password harus mengandung minimal satu angka."))

    # ── 5. Validasi phone format ───────────────────────────────────────
    phone_clean = re.sub(r"[\s\-\(\)]", "", phone)
    if not re.match(r"^[\+]?[0-9]{8,15}$", phone_clean):
        frappe.throw(
            _(
                "Format nomor telepon tidak valid. Gunakan format: +62xxxxxxxxxx atau 08xxxxxxxxxx"
            )
        )

    try:
        # ── 5.5. Cek user limit (jika ada subscription aktif) ──────────
        # Note: Registration adalah flow baru, jadi user limit check
        # dilakukan secara defensif — jika ada customer existing yang
        # sudah mencapai limit, registration tetap diizinkan untuk
        # customer BARU (karena mereka belum punya tenant/subscription).
        # Enforcement aktual dilakukan di before_user_insert hook.

        # ── 6. Buat User (Frappe User) ────────────────────────────────
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": full_name,
                "full_name": full_name,
                "password": password,
                "user_type": "Website User",
                "send_welcome_email": 0,
            }
        )
        user.append("roles", {"role": "Customer"})
        user.insert(ignore_permissions=True)

        # ── 7. Buat Customer (ERPNext) ────────────────────────────────
        customer = frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": company_name,
                "customer_group": frappe.db.get_single_value(
                    "Selling Settings", "customer_group"
                )
                or "All Customer Groups",
                "territory": frappe.db.get_single_value(
                    "Selling Settings", "territory"
                )
                or "All Territories",
                "customer_type": "Company",
                "customer_details": company_name,
            }
        )
        customer.insert(ignore_permissions=True)

        # ── 8. Buat Portal User (link User ↔ Customer) ────────────────
        portal_user = frappe.get_doc(
            {
                "doctype": "Portal User",
                "user": email,
                "parenttype": "Customer",
                "parent": customer.name,
                "parentfield": "portal_users",
            }
        )
        portal_user.insert(ignore_permissions=True)

        # ── 9. Buat Qalcuity Tenant (via hook after_customer_insert) ───
        # Hook sudah handle auto-create Tenant di customer.py
        # Jika hook tidak create (karena enable_trial_period off), buat manual
        if not frappe.db.exists("Qalcuity Tenant", {"customer": customer.name}):
            try:
                tenant = frappe.get_doc(
                    {
                        "doctype": "Qalcuity Tenant",
                        "customer": customer.name,
                        "status": "Active",
                    }
                )
                tenant.insert(ignore_permissions=True)
            except Exception:
                frappe.log_error(
                    title="Qalcuity: Failed to provision tenant for {0}".format(
                        customer.name
                    )
                )

        frappe.db.commit()

        return {
            "success": True,
            "message": _(
                "Registrasi berhasil! Akun Anda telah dibuat. "
                "Silakan login menggunakan email dan password yang sudah didaftarkan."
            ),
            "email": email,
        }

    except frappe.DuplicateEntryError:
        frappe.throw(
            _(
                "Email {0} sudah terdaftar. Silakan gunakan email lain atau login."
            ).format(email)
        )
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            title="Qalcuity: Registration failed for {0}".format(email)
        )
        frappe.throw(
            _("Terjadi kesalahan saat registrasi. Silakan coba lagi atau hubungi admin.")
        )
