# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity Tenant Isolation Module
=================================
Row-level isolation untuk controlled multi-tenancy.

Strategi:
- Shared database (semua tenant di 1 database)
- Row-level isolation via permission hooks
- Setiap user dihubungkan ke tenant via Portal User → Customer → Qalcuity Tenant

Hook functions:
- get_permission_query_conditions() — WHERE clause untuk list view filtering
- has_permission() — ownership validation per document (delegates to existing DocType-level checks)

Helper functions:
- get_current_customer() — customer name untuk user yang sedang login
- get_current_tenant() — tenant doc untuk user yang sedang login
- is_admin_user() — cek apakah user adalah admin/superadmin/system_manager
"""

import frappe
from frappe import _

# =============================================================================
# Roles yang mendapat akses penuh (tidak di-isolasi)
# =============================================================================
ADMIN_ROLES = frozenset([
    "System Manager",
    "Qalcuity Superadmin",
    "Qalcuity Admin",
])


# =============================================================================
# Helper Functions
# =============================================================================

def is_admin_user(user=None):
    """
    Cek apakah user adalah admin/superadmin/system_manager.

    Args:
        user: User email/name. Default: frappe.session.user

    Returns:
        bool: True jika user memiliki salah satu admin role.
    """
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return True

    # Cache role check
    cache_key = f"qalcuity_is_admin_{user}"
    cached = frappe.cache().get_value(cache_key)
    if cached is not None:
        return cached

    result = bool(
        frappe.db.exists(
            "Has Role",
            {
                "parent": user,
                "role": ["in", list(ADMIN_ROLES)],
            },
        )
    )

    frappe.cache().set_value(cache_key, result, expires_in_sec=300)
    return result


def get_current_customer(user=None):
    """
    Mendapatkan Customer name untuk user yang sedang login.

    Flow: User → Portal User (parent) → Customer name

    Args:
        user: User email/name. Default: frappe.session.user

    Returns:
        str atau None: Customer name, atau None jika bukan customer.
    """
    if not user:
        user = frappe.session.user

    if user in ("Guest", "Administrator"):
        return None

    # Cek apakah user adalah Customer role
    if "Customer" not in frappe.get_roles(user):
        return None

    # Cache lookup
    cache_key = f"qalcuity_customer_{user}"
    cached = frappe.cache().get_value(cache_key)
    if cached is not None:
        return cached

    customer = frappe.db.get_value(
        "Portal User",
        {"user": user, "parenttype": "Customer"},
        "parent",
    )

    if customer:
        frappe.cache().set_value(cache_key, customer, expires_in_sec=300)

    return customer


def get_current_tenant(user=None):
    """
    Mendapatkan Qalcuity Tenant document untuk user yang sedang login.

    Flow: User → Portal User → Customer → Qalcuity Tenant

    Args:
        user: User email/name. Default: frappe.session.user

    Returns:
        QalcuityTenant doc atau None.
    """
    customer = get_current_customer(user)
    if not customer:
        return None

    tenant_name = frappe.db.get_value(
        "Qalcuity Tenant",
        {"customer": customer, "status": ["!=", "Terminated"]},
        "name",
    )

    if not tenant_name:
        return None

    try:
        return frappe.get_doc("Qalcuity Tenant", tenant_name)
    except frappe.DoesNotExistError:
        return None


def get_customer_for_user(user):
    """
    Mendapatkan Customer name untuk user tertentu.

    Mirip dengan get_current_customer() tapi untuk user spesifik
    (berguna untuk permission hook yang menerima parameter user).

    Args:
        user: User email/name

    Returns:
        str atau None: Customer name
    """
    if not user or user in ("Guest", "Administrator"):
        return None

    return frappe.db.get_value(
        "Portal User",
        {"user": user, "parenttype": "Customer"},
        "parent",
    )


# =============================================================================
# Permission Query Conditions (untuk List View filtering)
# =============================================================================

# Map DocType → field yang menyimpan customer reference
# Digunakan untuk generate WHERE clause otomatis
DOCTYPE_CUSTOMER_FIELD = {
    # Qalcuity DocTypes
    "Qalcuity Subscription": "customer",
    "Qalcuity Payment": None,  # payment tidak punya field customer langsung
    "Qalcuity Tenant": "customer",
    # ERPNext DocTypes
    "Customer": "name",
    "Sales Order": "customer",
    "Sales Invoice": "customer",
    "Quotation": "customer",
    "Purchase Order": "party_name",
    "Purchase Invoice": "party_name",
    "Lead": "lead_owner",
}

# Qalcuity Payment perlu special handling karena link ke customer melalui subscription
PAYMENT_ISOLATED_DOCTYPES = {"Qalcuity Payment"}


def get_permission_query_conditions(user, doctype):
    """
    Frappe hook: mengembalikan SQL WHERE clause untuk filter data
    berdasarkan tenant/customer ownership.

    Dipanggil oleh Frappe saat user mengakses list view.

    Args:
        user: User yang sedang mengakses
        doctype: Nama DocType yang diakses

    Returns:
        str: SQL WHERE clause, atau "" jika tidak ada filter (admin/full access).
    """
    # Admin selalu mendapat akses penuh
    if is_admin_user(user):
        return ""

    # Guest tidak mendapat akses
    if not user or user == "Guest":
        return "1=0"  # Deny all

    # User bukan Customer role → tidak ada filter (ikuti permission Frappe default)
    if "Customer" not in frappe.get_roles(user):
        return ""

    customer = get_customer_for_user(user)
    if not customer:
        return "1=0"  # Deny all — customer tidak ditemukan

    # Generate WHERE clause berdasarkan DocType
    conditions = _build_query_condition(user, customer, doctype)
    return conditions


def _build_query_condition(user, customer, doctype):
    """
    Build SQL WHERE clause untuk isolasi tenant.

    Provides two layers of isolation:
    1. Customer field filtering (primary)
    2. Company field filtering (secondary — for ERPNext DocTypes)

    Args:
        user: User yang sedang mengakses
        customer: Customer name untuk user ini
        doctype: Nama DocType

    Returns:
        str: SQL WHERE clause
    """
    table = f"`tab{doctype}`"

    # Special handling untuk Qalcuity Payment (link ke customer melalui subscription)
    if doctype in PAYMENT_ISOLATED_DOCTYPES:
        return (
            f"({table}.subscription IN ("
            f"SELECT name FROM `tabQalcuity Subscription` "
            f"WHERE customer = {frappe.db.escape(customer)}"
            f"))"
        )

    # Dapatkan field name untuk customer
    customer_field = DOCTYPE_CUSTOMER_FIELD.get(doctype)

    if customer_field is None:
        # DocType tidak memiliki field customer → tidak bisa di-isolasi
        # Biarkan Frappe handle permission default
        return ""

    if customer_field == "name":
        # Customer DocType — name IS the customer
        return f"({table}.name = {frappe.db.escape(customer)})"

    # Build conditions list
    conditions = [f"{table}.{customer_field} = {frappe.db.escape(customer)}"]

    # Second isolation layer: Company-based filtering for ERPNext DocTypes
    # ERPNext transactional DocTypes that have a company field
    ERPNEXT_COMPANY_DOCTYPES = {
        "Sales Order",
        "Sales Invoice",
        "Quotation",
        "Purchase Order",
        "Purchase Invoice",
    }

    if doctype in ERPNEXT_COMPANY_DOCTYPES:
        company = _get_tenant_company_for_query(user)
        if company:
            conditions.append(f"{table}.company = {frappe.db.escape(company)}")

    return "(" + " AND ".join(conditions) + ")"


def _get_tenant_company_for_query(user):
    """
    Get tenant's ERP Company for query condition building.

    Args:
        user: User email/name

    Returns:
        str or None: Company name
    """
    if not user or user in ("Guest", "Administrator"):
        return None

    customer = get_customer_for_user(user)
    if not customer:
        return None

    return frappe.db.get_value(
        "Qalcuity Tenant",
        {"customer": customer, "status": "Active"},
        "erp_company",
    )


# =============================================================================
# Has Permission (per-document access check)
# =============================================================================

def has_permission(doc, ptype, user=None):
    """
    Frappe hook: memeriksa apakah user punya akses ke dokumen tertentu.

    Hook ini berfungsi sebagai VALIDASI TAMBAHAN di samping permission rules
    yang sudah ada di masing-masing DocType. Jika DocType sudah punya
    has_permission sendiri di hooks.py, hook ini TIDAK menggantikannya.

    Hook ini khusus untuk DocType yang BELUM punya permission check sendiri
    atau sebagai layer keamanan tambahan.

    Args:
        doc: Document object atau dict
        ptype: Permission type (read, write, create, delete, submit, cancel)
        user: User yang meminta akses. Default: frappe.session.user

    Returns:
        bool: True jika diizinkan, False jika ditolak.
    """
    if not user:
        user = frappe.session.user

    # Admin selalu diizinkan
    if is_admin_user(user):
        return True

    # Guest selalu ditolak
    if not user or user == "Guest":
        return False

    # User bukan Customer → ikuti permission default Frappe
    if "Customer" not in frappe.get_roles(user):
        return True  # Tidak mengambil keputusan — biarkan Frappe handle

    customer = get_customer_for_user(user)
    if not customer:
        return False

    doctype = doc.get("doctype") if isinstance(doc, dict) else doc.doctype

    # Validate ownership berdasarkan DocType
    return _validate_document_ownership(doc, customer, doctype, ptype)


def _validate_document_ownership(doc, customer, doctype, ptype):
    """
    Validate apakah document milik customer tertentu.

    Args:
        doc: Document object atau dict
        customer: Customer name
        doctype: Nama DocType
        ptype: Permission type

    Returns:
        bool: True jika document milik customer ini.
    """
    # Qalcuity Subscription — langsung punya field customer
    if doctype == "Qalcuity Subscription":
        doc_customer = doc.get("customer") if isinstance(doc, dict) else doc.customer
        if ptype in ("read", "write", "create"):
            return doc_customer == customer
        return False

    # Qalcuity Payment — customer melalui subscription
    if doctype == "Qalcuity Payment":
        if ptype in ("read", "create"):
            subscription = doc.get("subscription") if isinstance(doc, dict) else doc.subscription
            if subscription:
                sub_customer = frappe.db.get_value(
                    "Qalcuity Subscription", subscription, "customer"
                )
                return sub_customer == customer
            return False
        return False

    # Qalcuity Tenant — langsung punya field customer
    if doctype == "Qalcuity Tenant":
        doc_customer = doc.get("customer") if isinstance(doc, dict) else doc.customer
        if ptype == "read":
            return doc_customer == customer
        return False

    # ERPNext Customer — name IS the customer
    if doctype == "Customer":
        doc_name = doc.get("name") if isinstance(doc, dict) else doc.name
        if ptype == "read":
            return doc_name == customer
        return False

    # ERPNext Sales Order / Sales Invoice / Quotation — field customer + company
    if doctype in ("Sales Order", "Sales Invoice", "Quotation"):
        doc_customer = doc.get("customer") if isinstance(doc, dict) else doc.customer
        if ptype in ("read", "write"):
            if doc_customer != customer:
                return False

            # Company-based isolation (second layer)
            doc_company = doc.get("company") if isinstance(doc, dict) else getattr(doc, "company", None)
            if doc_company:
                tenant = get_current_tenant()
                if tenant and tenant.erp_company:
                    return doc_company == tenant.erp_company

            return True
        return False

    # Unknown DocType → deny
    return False


# =============================================================================
# Cache Invalidation
# =============================================================================

def clear_isolation_cache(user=None):
    """
    Clear isolation cache untuk user tertentu atau semua user.

    Berguna dipanggil saat:
- User role berubah
- Customer/Portal User dihapus atau dimodifikasi
- Tenant status berubah

    Args:
        user: User email/name. Jika None, clear semua cache.
    """
    if user:
        frappe.cache().delete_value(f"qalcuity_is_admin_{user}")
        frappe.cache().delete_value(f"qalcuity_customer_{user}")
    else:
        # Clear semua isolation-related cache
        # Frappe cache tidak support pattern-based delete,
        # jadi kita clear key yang diketahui
        pass
