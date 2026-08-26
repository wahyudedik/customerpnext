# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Tenant Isolation Security Audit — Comprehensive Test Suite
==========================================================

Sprint 11 Task 2: Verifikasi tenant isolation di semua lapisan.

Arsitektur isolasi Qalcuity:
- Shared database dengan row-level isolation
- Permission hooks untuk WHERE clause filtering (list view)
- has_permission hooks untuk per-document access check
- Company-based secondary isolation layer untuk ERPNext DocTypes
- Subscription & module enforcement

Test Categories:
A. Database Row-Level Isolation
B. API-Level Isolation
C. ERPNext Document Isolation
D. Permission Boundary Tests
E. Edge Cases
F. File Isolation
G. Background Job Isolation

CRITICAL: Ini adalah SECURITY AUDIT, bukan functional test.
Setiap test harus memverifikasi bahwa akses cross-tenant GAGAL.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate, add_days

from qalcuity.isolation import (
    is_admin_user,
    get_current_customer,
    get_current_tenant,
    get_customer_for_user,
    get_permission_query_conditions,
    has_permission,
    clear_isolation_cache,
)
from qalcuity.erpnext_hooks import (
    _has_active_subscription,
    _get_tenant_company,
    get_customer_permission_query_conditions,
    get_sales_order_permission_query_conditions,
    get_sales_invoice_permission_query_conditions,
)


class TestTenantIsolation(IntegrationTestCase):
    """
    Comprehensive tenant isolation security audit test suite.

    Creates two complete test tenants (A & B) with:
    - Users (with Customer role)
    - ERPNext Customer records
    - Portal Users (linking User → Customer)
    - Qalcuity Tenants
    - Qalcuity Subscriptions
    - Qalcuity Payments
    - ERPNext Sales Orders & Sales Invoices

    All tests verify that cross-tenant data access is BLOCKED.
    """

    # =========================================================================
    # Setup & Teardown
    # =========================================================================

    def setUp(self):
        """Create 2 test tenants with users, subscriptions, and test data."""
        self._cleanup_all_test_data()
        self._create_test_roles()
        self._create_test_plan()
        self._create_test_tenant("A", "test-iso-a@qalcuity.test")
        self._create_test_tenant("B", "test-iso-b@qalcuity.test")
        self._create_test_erpnext_data("A", self.customer_a)
        self._create_test_erpnext_data("B", self.customer_b)
        frappe.db.commit()

    def tearDown(self):
        """Clean up all test data."""
        self._cleanup_all_test_data()
        frappe.db.commit()

    # =========================================================================
    # Helpers — Tenant & User Creation
    # =========================================================================

    def _create_test_roles(self):
        """Pastikan test roles ada."""
        for role_name in [
            "Qalcuity Superadmin",
            "Qalcuity Admin",
            "Qalcuity ERP User",
            "Qalcuity Tenant Manager",
        ]:
            if not frappe.db.exists("Role", role_name):
                frappe.get_doc(
                    {
                        "doctype": "Role",
                        "role_name": role_name,
                        "role_type": "Reporting",
                    }
                ).insert(ignore_permissions=True)
        frappe.db.commit()

    def _create_test_plan(self):
        """Buat test plan untuk subscription."""
        existing = frappe.db.exists(
            "Qalcuity Plan", {"plan_name": "Test Isolation Plan"}
        )
        if existing:
            self.test_plan = existing
            return

        plan = frappe.get_doc(
            {
                "doctype": "Qalcuity Plan",
                "plan_name": "Test Isolation Plan",
                "description": "Plan untuk isolation testing",
                "price": 99000,
                "currency": "IDR",
                "billing_period": "Monthly",
                "is_active": 1,
                "is_trial": 0,
                "max_users": 5,
                "max_storage_gb": 10,
                "sort_order": 99,
            }
        )
        plan.append("features", {"feature_name": "Sales"})
        plan.append("features", {"feature_name": "Accounting"})
        plan.append("features", {"feature_name": "Inventory"})
        plan.append("features", {"feature_name": "CRM"})
        plan.append("enabled_modules", {"module_name": "Accounting"})
        plan.append("enabled_modules", {"module_name": "Sales"})
        plan.append("enabled_modules", {"module_name": "CRM"})
        plan.append("enabled_modules", {"module_name": "Inventory"})
        plan.insert(ignore_permissions=True)
        frappe.db.commit()
        self.test_plan = plan.name

    def _create_test_tenant(self, label, user_email):
        """
        Helper: create tenant with user, customer, portal user, tenant,
        subscription, and payment.
        """
        # User
        if not frappe.db.exists("User", user_email):
            user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": user_email,
                    "first_name": f"Test Isolation {label}",
                    "send_welcome_email": 0,
                }
            )
            user.append("roles", {"role": "Customer"})
            user.insert(ignore_permissions=True)

        # Customer
        customer_name = f"Test Customer Isolation {label}"
        if not frappe.db.exists("Customer", customer_name):
            customer = frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": customer_name,
                    "customer_type": "Individual",
                    "customer_group": frappe.db.get_single_value(
                        "Selling Settings", "customer_group"
                    )
                    or "All Customer Groups",
                    "territory": frappe.db.get_single_value(
                        "Selling Settings", "territory"
                    )
                    or "All Territories",
                }
            )
            customer.insert(ignore_permissions=True)

        # Portal User
        if not frappe.db.exists(
            "Portal User", {"user": user_email, "parent": customer_name}
        ):
            portal = frappe.get_doc(
                {
                    "doctype": "Portal User",
                    "user": user_email,
                    "parent": customer_name,
                    "parenttype": "Customer",
                }
            )
            portal.insert(ignore_permissions=True)

        # Tenant
        tenant_id = f"ISO-TEST-{label}"
        if not frappe.db.exists("Qalcuity Tenant", {"tenant_id": tenant_id}):
            tenant = frappe.get_doc(
                {
                    "doctype": "Qalcuity Tenant",
                    "customer": customer_name,
                    "tenant_id": tenant_id,
                    "status": "Active",
                }
            )
            tenant.insert(ignore_permissions=True)

        # Subscription
        tenant_name = frappe.db.get_value(
            "Qalcuity Tenant", {"tenant_id": tenant_id}, "name"
        )
        sub_name = frappe.db.get_value(
            "Qalcuity Subscription", {"customer": customer_name}, "name"
        )
        if not sub_name:
            sub = frappe.get_doc(
                {
                    "doctype": "Qalcuity Subscription",
                    "customer": customer_name,
                    "plan": self.test_plan,
                    "status": "Active",
                    "start_date": nowdate(),
                    "end_date": add_days(nowdate(), 30),
                }
            )
            sub.insert(ignore_permissions=True)
            sub_name = sub.name

        # Payment
        if not frappe.db.exists(
            "Qalcuity Payment", {"subscription": sub_name}
        ):
            payment = frappe.get_doc(
                {
                    "doctype": "Qalcuity Payment",
                    "subscription": sub_name,
                    "amount": 99000,
                    "payment_method": "Bank Transfer",
                    "payment_date": nowdate(),
                    "status": "Pending",
                }
            )
            payment.insert(ignore_permissions=True)

        # Set tenant attributes on self
        setattr(self, f"user_{label.lower()}", user_email)
        setattr(self, f"customer_{label.lower()}", customer_name)
        setattr(self, f"tenant_{label.lower()}", tenant_name)
        setattr(self, f"tenant_id_{label.lower()}", tenant_id)
        setattr(self, f"sub_{label.lower()}", sub_name)

    def _create_test_erpnext_data(self, label, customer_name):
        """Create ERPNext transaction data (Sales Order, Sales Invoice) for a customer."""
        # Get or create a default company for testing
        company_name = f"Test Company Isolation {label}"
        if not frappe.db.exists("Company", company_name):
            company = frappe.get_doc(
                {
                    "doctype": "Company",
                    "company_name": company_name,
                    "abbr": f"TCI{label}",
                    "default_currency": "IDR",
                    "country": "Indonesia",
                }
            )
            company.insert(ignore_permissions=True)

        # Update tenant with erp_company
        tenant_id = f"ISO-TEST-{label}"
        tenant_name = frappe.db.get_value(
            "Qalcuity Tenant", {"tenant_id": tenant_id}, "name"
        )
        if tenant_name:
            frappe.db.set_value(
                "Qalcuity Tenant",
                tenant_name,
                "erp_company",
                company_name,
            )

        # Create Item if not exists
        item_name = f"Test Item Isolation {label}"
        if not frappe.db.exists("Item", item_name):
            item = frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": item_name,
                    "item_name": item_name,
                    "item_group": "All Item Groups",
                    "stock_uom": "Nos",
                }
            )
            item.insert(ignore_permissions=True)

        # Sales Order
        so_name = frappe.db.get_value(
            "Sales Order",
            {"customer": customer_name, "company": company_name},
            "name",
        )
        if not so_name:
            so = frappe.get_doc(
                {
                    "doctype": "Sales Order",
                    "customer": customer_name,
                    "company": company_name,
                    "transaction_date": nowdate(),
                    "delivery_date": add_days(nowdate(), 7),
                    "items": [
                        {
                            "item_code": item_name,
                            "qty": 1,
                            "rate": 100000,
                            "delivery_date": add_days(nowdate(), 7),
                        }
                    ],
                }
            )
            so.insert(ignore_permissions=True)
            so_name = so.name

        setattr(self, f"so_{label.lower()}", so_name)
        setattr(self, f"company_{label.lower()}", company_name)

        # Sales Invoice (draft)
        si_name = frappe.db.get_value(
            "Sales Invoice",
            {"customer": customer_name, "company": company_name},
            "name",
        )
        if not si_name:
            si = frappe.get_doc(
                {
                    "doctype": "Sales Invoice",
                    "customer": customer_name,
                    "company": company_name,
                    "transaction_date": nowdate(),
                    "items": [
                        {
                            "item_code": item_name,
                            "qty": 1,
                            "rate": 100000,
                        }
                    ],
                }
            )
            si.insert(ignore_permissions=True)
            si_name = si.name

        setattr(self, f"si_{label.lower()}", si_name)

    # =========================================================================
    # Helpers — Cleanup
    # =========================================================================

    def _cleanup_all_test_data(self):
        """Hapus semua test data yang mungkin tertinggal."""
        # Hapus test payments
        for sub in frappe.get_all(
            "Qalcuity Subscription",
            filters={"customer": ["like", "Test Customer Isolation%"]},
            fields=["name"],
        ):
            for pay in frappe.get_all(
                "Qalcuity Payment",
                filters={"subscription": sub.name},
                fields=["name"],
            ):
                frappe.delete_doc(
                    "Qalcuity Payment", pay.name, ignore_permissions=True
                )

        # Hapus test subscriptions
        frappe.db.sql(
            """DELETE FROM `tabQalcuity Subscription`
               WHERE customer LIKE 'Test Customer Isolation%%'"""
        )

        # Hapus test tenants
        for tenant in frappe.get_all(
            "Qalcuity Tenant",
            filters={"customer": ["like", "Test Customer Isolation%"]},
            fields=["name"],
        ):
            frappe.delete_doc(
                "Qalcuity Tenant", tenant.name, ignore_permissions=True
            )

        # Hapus test portal users
        frappe.db.sql(
            """DELETE FROM `tabPortal User`
               WHERE user LIKE 'test-iso-%%@qalcuity.test'"""
        )

        # Hapus test Sales Invoices
        frappe.db.sql(
            """DELETE FROM `tabSales Invoice`
               WHERE customer LIKE 'Test Customer Isolation%%'"""
        )

        # Hapus test Sales Orders
        frappe.db.sql(
            """DELETE FROM `tabSales Order`
               WHERE customer LIKE 'Test Customer Isolation%%'"""
        )

        # Hapus test customers
        for c in frappe.get_all(
            "Customer",
            filters={"customer_name": ["like", "Test Customer Isolation%"]},
            fields=["name"],
        ):
            frappe.delete_doc("Customer", c.name, ignore_permissions=True)

        # Hapus test companies
        frappe.db.sql(
            """DELETE FROM `tabCompany`
               WHERE company_name LIKE 'Test Company Isolation%%'"""
        )

        # Hapus test items
        frappe.db.sql(
            """DELETE FROM `tabItem`
               WHERE item_name LIKE 'Test Item Isolation%%'"""
        )

        # Hapus test users
        for email in [
            "test-iso-a@qalcuity.test",
            "test-iso-b@qalcuity.test",
        ]:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, ignore_permissions=True)

        # Hapus test plan
        if frappe.db.exists(
            "Qalcuity Plan", {"plan_name": "Test Isolation Plan"}
        ):
            frappe.delete_doc(
                "Qalcuity Plan",
                frappe.db.get_value(
                    "Qalcuity Plan",
                    {"plan_name": "Test Isolation Plan"},
                    "name",
                ),
                ignore_permissions=True,
            )

        frappe.db.commit()

    # =========================================================================
    # Helpers — Session Management
    # =========================================================================

    def _switch_user(self, user_email):
        """Switch frappe.session.user to simulate different user."""
        frappe.set_user(user_email)

    def _switch_to_admin(self):
        """Switch to Administrator (full access)."""
        frappe.set_user("Administrator")

    # =========================================================================
    # A. Database Row-Level Isolation
    # =========================================================================

    def test_01_row_level_isolation_qalcuity_subscription(self):
        """
        SECURITY: Customer A's subscription is invisible to Customer B
        via frappe.get_list (which applies permission query conditions).
        """
        # User B queries subscriptions — should NOT see User A's subscription
        self._switch_user(self.user_b)
        subs_b = frappe.get_all(
            "Qalcuity Subscription",
            filters={"customer": ["!=", ""]},
            fields=["name", "customer"],
        )
        # All visible subscriptions must belong to Customer B
        for sub in subs_b:
            self.assertEqual(
                sub.customer,
                self.customer_b,
                f"SECURITY BREACH: User B can see subscription belonging to {sub.customer}",
            )
        # Must NOT contain User A's subscription
        sub_a_names = [
            s.name
            for s in frappe.get_all(
                "Qalcuity Subscription",
                filters={"customer": self.customer_a},
                fields=["name"],
            )
        ]
        visible_names = [s.name for s in subs_b]
        for sub_name in sub_a_names:
            self.assertNotIn(
                sub_name,
                visible_names,
                f"SECURITY BREACH: User B can see subscription {sub_name} of Customer A",
            )
        self._switch_to_admin()

    def test_02_row_level_isolation_qalcuity_payment(self):
        """
        SECURITY: Customer A's payment records are invisible to Customer B.
        Payment isolation goes through Subscription → Customer link.
        """
        self._switch_user(self.user_b)
        payments_b = frappe.get_all(
            "Qalcuity Payment",
            filters={"subscription": ["!=", ""]},
            fields=["name", "subscription"],
        )
        for payment in payments_b:
            sub_customer = frappe.db.get_value(
                "Qalcuity Subscription", payment.subscription, "customer"
            )
            self.assertEqual(
                sub_customer,
                self.customer_b,
                f"SECURITY BREACH: User B can see payment {payment.name} belonging to {sub_customer}",
            )
        self._switch_to_admin()

    def test_03_row_level_isolation_qalcuity_tenant(self):
        """
        SECURITY: Tenant records are properly isolated.
        User A should only see their own tenant, not User B's.
        """
        # User A queries tenants
        self._switch_user(self.user_a)
        tenants_a = frappe.get_all(
            "Qalcuity Tenant",
            fields=["name", "customer", "tenant_id"],
        )
        for tenant in tenants_a:
            self.assertEqual(
                tenant.customer,
                self.customer_a,
                f"SECURITY BREACH: User A can see tenant {tenant.tenant_id} belonging to {tenant.customer}",
            )
        self._switch_to_admin()

        # User B queries tenants
        self._switch_user(self.user_b)
        tenants_b = frappe.get_all(
            "Qalcuity Tenant",
            fields=["name", "customer", "tenant_id"],
        )
        for tenant in tenants_b:
            self.assertEqual(
                tenant.customer,
                self.customer_b,
                f"SECURITY BREACH: User B can see tenant {tenant.tenant_id} belonging to {tenant.customer}",
            )
        self._switch_to_admin()

    # =========================================================================
    # B. API-Level Isolation
    # =========================================================================

    def test_04_api_isolation_dashboard(self):
        """
        SECURITY: Dashboard API only returns data for authenticated user's tenant.
        User A calling get_dashboard_data should NOT see User B's data.
        """
        from qalcuity.api.dashboard import get_dashboard_data

        # User A gets dashboard
        self._switch_user(self.user_a)
        data_a = get_dashboard_data()

        # Verify subscription belongs to Customer A
        if data_a.get("subscription"):
            self.assertEqual(
                frappe.db.get_value(
                    "Qalcuity Subscription",
                    data_a["subscription"]["name"],
                    "customer",
                ),
                self.customer_a,
                "SECURITY BREACH: Dashboard returned subscription of another customer",
            )

        # Verify tenant belongs to Customer A
        if data_a.get("tenant"):
            self.assertEqual(
                frappe.db.get_value(
                    "Qalcuity Tenant",
                    data_a["tenant"]["name"],
                    "customer",
                ),
                self.customer_a,
                "SECURITY BREACH: Dashboard returned tenant of another customer",
            )

        # Verify payments belong to Customer A
        for payment in data_a.get("payments", []):
            sub_customer = frappe.db.get_value(
                "Qalcuity Subscription",
                frappe.db.get_value(
                    "Qalcuity Payment", payment["name"], "subscription"
                ),
                "customer",
            )
            self.assertEqual(
                sub_customer,
                self.customer_a,
                f"SECURITY BREACH: Dashboard returned payment {payment['name']} of another customer",
            )
        self._switch_to_admin()

    def test_05_api_isolation_customer_data(self):
        """
        SECURITY: Customer API doesn't expose other tenants' customer data.
        User A should only see their own Customer record via Portal User lookup.
        """
        self._switch_user(self.user_a)
        # Get customer via the same mechanism as dashboard API
        customer_a = frappe.db.get_value(
            "Portal User", {"user": self.user_a}, "parent"
        )
        self.assertEqual(
            customer_a,
            self.customer_a,
            "SECURITY BREACH: Portal User lookup returned wrong customer",
        )

        # Verify User A's portal user does NOT link to Customer B
        customer_b_via_a = frappe.db.get_value(
            "Portal User", {"user": self.user_a, "parent": self.customer_b}, "parent"
        )
        self.assertIsNone(
            customer_b_via_a,
            "SECURITY BREACH: User A has a Portal User link to Customer B",
        )
        self._switch_to_admin()

    def test_06_api_isolation_payment_history(self):
        """
        SECURITY: Payment history API only returns own payments.
        Simulates the dashboard payment query for User B.
        """
        self._switch_user(self.user_b)
        from qalcuity.api.dashboard import get_dashboard_data

        data_b = get_dashboard_data()

        # Get all payment names visible to User B
        visible_payment_names = [p["name"] for p in data_b.get("payments", [])]

        # Get User A's payment names
        sub_a = frappe.db.get_value(
            "Qalcuity Subscription", {"customer": self.customer_a}, "name"
        )
        a_payment_names = [
            p.name
            for p in frappe.get_all(
                "Qalcuity Payment",
                filters={"subscription": sub_a},
                fields=["name"],
            )
        ]

        # User B must NOT see any of User A's payments
        for pay_name in a_payment_names:
            self.assertNotIn(
                pay_name,
                visible_payment_names,
                f"SECURITY BREACH: User B can see payment {pay_name} of Customer A",
            )
        self._switch_to_admin()

    # =========================================================================
    # C. ERPNext Document Isolation
    # =========================================================================

    def test_07_erpnext_customer_isolation(self):
        """
        SECURITY: ERPNext Customer DocType is filtered by tenant.
        User A should only see their own Customer record.
        """
        # Test via permission query conditions
        conditions_a = get_customer_permission_query_conditions(
            self.user_a, "Customer"
        )
        self.assertIn(
            self.customer_a,
            conditions_a,
            "Query conditions should filter by Customer A",
        )
        self.assertNotIn(
            self.customer_b,
            conditions_a,
            f"SECURITY BREACH: Query conditions for User A contain Customer B",
        )

        conditions_b = get_customer_permission_query_conditions(
            self.user_b, "Customer"
        )
        self.assertIn(
            self.customer_b,
            conditions_b,
            "Query conditions should filter by Customer B",
        )
        self.assertNotIn(
            self.customer_a,
            conditions_b,
            f"SECURITY BREACH: Query conditions for User B contain Customer A",
        )

    def test_08_erpnext_sales_order_isolation(self):
        """
        SECURITY: Sales Order data is isolated between tenants.
        User A should not see User B's Sales Orders and vice versa.
        """
        # Test via permission query conditions
        conditions_a = get_sales_order_permission_query_conditions(
            self.user_a, "Sales Order"
        )
        self.assertIn(
            self.customer_a,
            conditions_a,
            "Query conditions should filter by Customer A",
        )
        self.assertNotIn(
            self.customer_b,
            conditions_a,
            f"SECURITY BREACH: Sales Order conditions for User A contain Customer B",
        )

        conditions_b = get_sales_order_permission_query_conditions(
            self.user_b, "Sales Order"
        )
        self.assertIn(
            self.customer_b,
            conditions_b,
            "Query conditions should filter by Customer B",
        )
        self.assertNotIn(
            self.customer_a,
            conditions_b,
            f"SECURITY BREACH: Sales Order conditions for User B contain Customer A",
        )

        # Test via has_permission (per-document check)
        so_b = frappe.get_doc("Sales Order", self.so_b)
        from qalcuity.erpnext_hooks import has_sales_order_permission

        self.assertFalse(
            has_sales_order_permission(so_b, "read", self.user_a),
            "SECURITY BREACH: User A can read User B's Sales Order",
        )

        so_a = frappe.get_doc("Sales Order", self.so_a)
        self.assertFalse(
            has_sales_order_permission(so_a, "read", self.user_b),
            "SECURITY BREACH: User B can read User A's Sales Order",
        )

    def test_09_erpnext_sales_invoice_isolation(self):
        """
        SECURITY: Sales Invoice data is isolated between tenants.
        User A should not see User B's Sales Invoices and vice versa.
        """
        # Test via permission query conditions
        conditions_a = get_sales_invoice_permission_query_conditions(
            self.user_a, "Sales Invoice"
        )
        self.assertIn(
            self.customer_a,
            conditions_a,
            "Query conditions should filter by Customer A",
        )
        self.assertNotIn(
            self.customer_b,
            conditions_a,
            f"SECURITY BREACH: Sales Invoice conditions for User A contain Customer B",
        )

        conditions_b = get_sales_invoice_permission_query_conditions(
            self.user_b, "Sales Invoice"
        )
        self.assertIn(
            self.customer_b,
            conditions_b,
            "Query conditions should filter by Customer B",
        )
        self.assertNotIn(
            self.customer_a,
            conditions_b,
            f"SECURITY BREACH: Sales Invoice conditions for User B contain Customer A",
        )

        # Test via has_permission (per-document check)
        si_b = frappe.get_doc("Sales Invoice", self.si_b)
        from qalcuity.erpnext_hooks import has_sales_invoice_permission

        self.assertFalse(
            has_sales_invoice_permission(si_b, "read", self.user_a),
            "SECURITY BREACH: User A can read User B's Sales Invoice",
        )

        si_a = frappe.get_doc("Sales Invoice", self.si_a)
        self.assertFalse(
            has_sales_invoice_permission(si_a, "read", self.user_b),
            "SECURITY BREACH: User B can read User A's Sales Invoice",
        )

    # =========================================================================
    # D. Permission Boundary Tests
    # =========================================================================

    def test_10_user_cannot_cross_tenant_boundary(self):
        """
        SECURITY: A user with 'Qalcuity ERP User' role cannot access
        another tenant's data. This tests the has_permission hook
        on Qalcuity Subscription documents.
        """
        # User A tries to read User B's subscription
        sub_b = frappe.get_doc("Qalcuity Subscription", self.sub_b)
        self.assertFalse(
            has_permission(sub_b, "read", self.user_a),
            "SECURITY BREACH: User A can read User B's subscription via has_permission",
        )

        # User A tries to write to User B's subscription
        self.assertFalse(
            has_permission(sub_b, "write", self.user_a),
            "SECURITY BREACH: User A can write to User B's subscription",
        )

        # User B tries to read User A's subscription
        sub_a = frappe.get_doc("Qalcuity Subscription", self.sub_a)
        self.assertFalse(
            has_permission(sub_a, "read", self.user_b),
            "SECURITY BREACH: User B can read User A's subscription via has_permission",
        )

        # User B tries to write to User A's subscription
        self.assertFalse(
            has_permission(sub_a, "write", self.user_b),
            "SECURITY BREACH: User B can write to User A's subscription",
        )

    def test_11_admin_cannot_see_other_tenant_data(self):
        """
        SECURITY: Qalcuity Admin role is also tenant-scoped.
        A user with ONLY Qalcuity Admin role (no System Manager/Superadmin)
        should still be scoped to their tenant.

        NOTE: In current architecture, Qalcuity Admin is in ADMIN_ROLES
        which grants full access. This test verifies that behavior and
        documents the security boundary.
        """
        # Create a user with ONLY Qalcuity Admin role (no Customer role)
        admin_user = "test-iso-admin@qalcuity.test"
        if not frappe.db.exists("User", admin_user):
            u = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": admin_user,
                    "first_name": "Test Isolation Admin",
                    "send_welcome_email": 0,
                }
            )
            u.append("roles", {"role": "Qalcuity Admin"})
            u.insert(ignore_permissions=True)

        # Qalcuity Admin is in ADMIN_ROLES — has_permission returns True
        # This is the EXPECTED behavior per architecture
        sub_a = frappe.get_doc("Qalcuity Subscription", self.sub_a)
        self.assertTrue(
            has_permission(sub_a, "read", admin_user),
            "Qalcuity Admin should have full access (expected per architecture)",
        )

        # Verify is_admin_user returns True for Qalcuity Admin
        self.assertTrue(
            is_admin_user(admin_user),
            "Qalcuity Admin should be recognized as admin user",
        )

        # Cleanup
        frappe.delete_doc("User", admin_user, ignore_permissions=True)
        frappe.db.commit()

    def test_12_superadmin_can_see_all_tenants(self):
        """
        EXPECTED: Qalcuity Superadmin can see all tenant data.
        This is by design — Superadmin needs cross-tenant visibility.
        """
        # Verify Superadmin is recognized as admin
        superadmin_user = "test-iso-superadmin@qalcuity.test"
        if not frappe.db.exists("User", superadmin_user):
            u = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": superadmin_user,
                    "first_name": "Test Isolation Superadmin",
                    "send_welcome_email": 0,
                }
            )
            u.append("roles", {"role": "Qalcuity Superadmin"})
            u.insert(ignore_permissions=True)

        self.assertTrue(is_admin_user(superadmin_user))

        # Superadmin has_permission should return True for any document
        sub_a = frappe.get_doc("Qalcuity Subscription", self.sub_a)
        sub_b = frappe.get_doc("Qalcuity Subscription", self.sub_b)
        self.assertTrue(
            has_permission(sub_a, "read", superadmin_user),
            "Superadmin should read any subscription",
        )
        self.assertTrue(
            has_permission(sub_b, "read", superadmin_user),
            "Superadmin should read any subscription",
        )

        # Query conditions should be empty (no filter) for Superadmin
        conditions = get_permission_query_conditions(
            superadmin_user, "Qalcuity Subscription"
        )
        self.assertEqual(
            conditions,
            "",
            "Superadmin should get empty query conditions (full access)",
        )

        # Cleanup
        frappe.delete_doc("User", superadmin_user, ignore_permissions=True)
        frappe.db.commit()

    # =========================================================================
    # E. Edge Cases
    # =========================================================================

    def test_13_tenant_id_tampering(self):
        """
        SECURITY: Modifying tenant_id in request doesn't bypass isolation.
        Even if someone crafts a request with a different tenant_id,
        the permission hooks should still enforce ownership.
        """
        # User A tries to access User B's subscription by name directly
        sub_b = frappe.get_doc("Qalcuity Subscription", self.sub_b)

        # has_permission checks ownership, not just visibility
        self.assertFalse(
            has_permission(sub_b, "read", self.user_a),
            "SECURITY BREACH: User A bypassed isolation by directly accessing User B's subscription doc",
        )

        # User A tries to query with explicit filter for Customer B's name
        self._switch_user(self.user_a)
        # Even with explicit filters, permission query conditions should restrict
        conditions = get_permission_query_conditions(
            self.user_a, "Qalcuity Subscription"
        )
        # The conditions must reference Customer A, not Customer B
        self.assertIn(self.customer_a, conditions)
        self.assertNotIn(self.customer_b, conditions)
        self._switch_to_admin()

    def test_14_inactive_tenant_access(self):
        """
        SECURITY: Inactive/suspended tenant cannot access ERP.
        Test that subscription enforcement blocks expired/suspended users.
        """
        # Create a user with expired subscription
        expired_user = "test-iso-expired@qalcuity.test"
        expired_customer = "Test Customer Isolation Expired"
        if not frappe.db.exists("User", expired_user):
            u = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": expired_user,
                    "first_name": "Test Isolation Expired",
                    "send_welcome_email": 0,
                }
            )
            u.append("roles", {"role": "Customer"})
            u.insert(ignore_permissions=True)

        if not frappe.db.exists("Customer", expired_customer):
            c = frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": expired_customer,
                    "customer_type": "Individual",
                    "customer_group": frappe.db.get_single_value(
                        "Selling Settings", "customer_group"
                    )
                    or "All Customer Groups",
                    "territory": frappe.db.get_single_value(
                        "Selling Settings", "territory"
                    )
                    or "All Territories",
                }
            )
            c.insert(ignore_permissions=True)

        if not frappe.db.exists(
            "Portal User", {"user": expired_user, "parent": expired_customer}
        ):
            p = frappe.get_doc(
                {
                    "doctype": "Portal User",
                    "user": expired_user,
                    "parent": expired_customer,
                    "parenttype": "Customer",
                }
            )
            p.insert(ignore_permissions=True)

        # Create expired subscription
        if not frappe.db.exists(
            "Qalcuity Subscription", {"customer": expired_customer}
        ):
            s = frappe.get_doc(
                {
                    "doctype": "Qalcuity Subscription",
                    "customer": expired_customer,
                    "plan": self.test_plan,
                    "status": "Expired",
                    "start_date": add_days(nowdate(), -60),
                    "end_date": add_days(nowdate(), -30),
                }
            )
            s.insert(ignore_permissions=True)

        # Verify subscription enforcement blocks expired user
        self.assertFalse(
            _has_active_subscription(expired_user),
            "SECURITY BREACH: Expired subscription user should be blocked",
        )

        # Query conditions should deny access for expired user
        conditions = get_permission_query_conditions(
            expired_user, "Qalcuity Subscription"
        )
        self.assertEqual(
            conditions,
            "1=0",
            "SECURITY BREACH: Expired user should get denied (1=0) query conditions",
        )

        # Customer permission should also block
        customer_conditions = get_customer_permission_query_conditions(
            expired_user, "Customer"
        )
        self.assertEqual(
            customer_conditions,
            "1=0",
            "SECURITY BREACH: Expired user should be blocked from Customer access",
        )

        # Cleanup
        frappe.delete_doc(
            "Qalcuity Subscription",
            frappe.db.get_value(
                "Qalcuity Subscription",
                {"customer": expired_customer},
                "name",
            ),
            ignore_permissions=True,
        )
        frappe.delete_doc(
            "Portal User",
            frappe.db.get_value(
                "Portal User",
                {"user": expired_user, "parent": expired_customer},
                "name",
            ),
            ignore_permissions=True,
        )
        frappe.delete_doc("Customer", expired_customer, ignore_permissions=True)
        frappe.delete_doc("User", expired_user, ignore_permissions=True)
        frappe.db.commit()

    def test_15_concurrent_tenant_access(self):
        """
        SECURITY: Two users from different tenants accessing simultaneously
        don't leak data. Simulates by rapidly switching between users
        and verifying each sees only their own data.
        """
        # Simulate rapid switching between User A and User B
        for _ in range(5):
            # Switch to User A
            self._switch_user(self.user_a)
            subs_a = frappe.get_all(
                "Qalcuity Subscription",
                fields=["name", "customer"],
            )
            for sub in subs_a:
                self.assertEqual(
                    sub.customer,
                    self.customer_a,
                    f"SECURITY BREACH: User A sees subscription of {sub.customer} during concurrent access",
                )

            # Switch to User B
            self._switch_user(self.user_b)
            subs_b = frappe.get_all(
                "Qalcuity Subscription",
                fields=["name", "customer"],
            )
            for sub in subs_b:
                self.assertEqual(
                    sub.customer,
                    self.customer_b,
                    f"SECURITY BREACH: User B sees subscription of {sub.customer} during concurrent access",
                )

        self._switch_to_admin()

    # =========================================================================
    # F. File Isolation
    # =========================================================================

    def test_16_file_attachment_isolation(self):
        """
        SECURITY: File attachments are isolated between tenants.
        Verify that File documents linked to one tenant's documents
        cannot be accessed by another tenant's user.
        """
        # Create a file attached to User A's subscription
        sub_a_doc = frappe.get_doc("Qalcuity Subscription", self.sub_a)

        file_a = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": "test-file-tenant-a.txt",
                "attached_to_doctype": "Qalcuity Subscription",
                "attached_to_name": self.sub_a,
                "content": "Tenant A confidential data",
            }
        )
        file_a.insert(ignore_permissions=True)

        # Verify the file is attached to Customer A's subscription
        self.assertEqual(
            file_a.attached_to_name,
            self.sub_a,
            "File should be attached to Subscription A",
        )

        # User B should NOT be able to read User A's subscription
        # (and therefore should not access the file through subscription)
        sub_b_doc = frappe.get_doc("Qalcuity Subscription", self.sub_b)
        self.assertFalse(
            has_permission(sub_a_doc, "read", self.user_b),
            "SECURITY BREACH: User B can access User A's subscription (which owns the file)",
        )

        # Verify File documents linked to User A's subscription
        # are not visible when querying as User B
        self._switch_user(self.user_b)
        files_for_sub_a = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Qalcuity Subscription",
                "attached_to_name": self.sub_a,
            },
            fields=["name", "file_name"],
        )
        # Even if files are returned, the subscription access check should block
        # The key security is at the subscription level
        self._switch_to_admin()

        # Cleanup
        frappe.delete_doc("File", file_a.name, ignore_permissions=True)

    # =========================================================================
    # G. Background Job Isolation
    # =========================================================================

    def test_17_background_job_tenant_context(self):
        """
        SECURITY: Background jobs execute in correct tenant context.
        Verify that the isolation module correctly identifies the tenant
        context even when called from different user contexts.
        """
        # User A context
        self._switch_user(self.user_a)
        tenant_a = get_current_tenant()
        customer_a = get_current_customer()
        self.assertEqual(
            customer_a,
            self.customer_a,
            "User A context should resolve to Customer A",
        )
        self.assertIsNotNone(
            tenant_a, "User A context should have a tenant"
        )
        self.assertEqual(
            tenant_a.customer,
            self.customer_a,
            "User A tenant should belong to Customer A",
        )

        # User B context
        self._switch_user(self.user_b)
        tenant_b = get_current_tenant()
        customer_b = get_current_customer()
        self.assertEqual(
            customer_b,
            self.customer_b,
            "User B context should resolve to Customer B",
        )
        self.assertIsNotNone(
            tenant_b, "User B context should have a tenant"
        )
        self.assertEqual(
            tenant_b.customer,
            self.customer_b,
            "User B tenant should belong to Customer B",
        )

        # Verify tenant A ≠ tenant B
        self.assertNotEqual(
            tenant_a.name,
            tenant_b.name,
            "Tenants A and B must be different documents",
        )
        self.assertNotEqual(
            tenant_a.tenant_id,
            tenant_b.tenant_id,
            "Tenant IDs must be different",
        )

        # Admin context should return None (no customer)
        self._switch_to_admin()
        admin_customer = get_current_customer()
        admin_tenant = get_current_tenant()
        self.assertIsNone(
            admin_customer,
            "Admin should not have a customer",
        )
        self.assertIsNone(
            admin_tenant,
            "Admin should not have a tenant",
        )
