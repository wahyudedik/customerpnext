# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Test Tenant Isolation — Row-level Isolation
=============================================
Skenario test untuk memastikan:
1. User A hanya bisa lihat data User A
2. User B hanya bisa lihat data User B
3. Superadmin bisa lihat semua data
4. Cross-tenant access ditolak
"""

import frappe
from frappe.tests import IntegrationTestCase

from qalcuity.isolation import (
    is_admin_user,
    get_current_customer,
    get_current_tenant,
    get_customer_for_user,
    get_permission_query_conditions,
    has_permission,
    clear_isolation_cache,
)


class TestTenantIsolation(IntegrationTestCase):
    """Test cases untuk Tenant Isolation."""

    def setUp(self):
        """Setup test data — buat 2 customer, 2 tenant, 2 user."""
        self._cleanup_test_data()
        self._create_test_users_and_customers()

    def tearDown(self):
        """Cleanup test data."""
        frappe.db.rollback()

    def _cleanup_test_data(self):
        """Hapus test data jika ada."""
        for user in ["test-customer-a@qalcuity.test", "test-customer-b@qalcuity.test"]:
            if frappe.db.exists("User", user):
                frappe.delete_doc("User", user, ignore_permissions=True)

        for customer in ["Test Customer A - Isolation", "Test Customer B - Isolation"]:
            if frappe.db.exists("Customer", customer):
                frappe.delete_doc("Customer", customer, ignore_permissions=True)

        for tenant_id in ["TENANT-TEST-A", "TENANT-TEST-B"]:
            if frappe.db.exists("Qalcuity Tenant", {"tenant_id": tenant_id}):
                frappe.delete_doc(
                    "Qalcuity Tenant",
                    frappe.db.get_value("Qalcuity Tenant", {"tenant_id": tenant_id}, "name"),
                    ignore_permissions=True,
                )

    def _create_test_users_and_customers(self):
        """Buat 2 test users dengan customer dan tenant masing-masing."""
        # === User A ===
        self.user_a = "test-customer-a@qalcuity.test"
        if not frappe.db.exists("User", self.user_a):
            user_a = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": self.user_a,
                    "first_name": "Test Customer A",
                    "send_welcome_email": 0,
                }
            )
            user_a.append("roles", {"role": "Customer"})
            user_a.insert(ignore_permissions=True)

        # Customer A
        self.customer_a = "Test Customer A - Isolation"
        if not frappe.db.exists("Customer", self.customer_a):
            customer_a = frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": self.customer_a,
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
            customer_a.insert(ignore_permissions=True)

        # Portal User A
        if not frappe.db.exists(
            "Portal User", {"user": self.user_a, "parent": self.customer_a}
        ):
            portal_a = frappe.get_doc(
                {
                    "doctype": "Portal User",
                    "user": self.user_a,
                    "parent": self.customer_a,
                    "parenttype": "Customer",
                }
            )
            portal_a.insert(ignore_permissions=True)

        # Tenant A
        if not frappe.db.exists("Qalcuity Tenant", {"tenant_id": "TENANT-TEST-A"}):
            tenant_a = frappe.get_doc(
                {
                    "doctype": "Qalcuity Tenant",
                    "customer": self.customer_a,
                    "tenant_id": "TENANT-TEST-A",
                    "status": "Active",
                }
            )
            tenant_a.insert(ignore_permissions=True)

        # === User B ===
        self.user_b = "test-customer-b@qalcuity.test"
        if not frappe.db.exists("User", self.user_b):
            user_b = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": self.user_b,
                    "first_name": "Test Customer B",
                    "send_welcome_email": 0,
                }
            )
            user_b.append("roles", {"role": "Customer"})
            user_b.insert(ignore_permissions=True)

        # Customer B
        self.customer_b = "Test Customer B - Isolation"
        if not frappe.db.exists("Customer", self.customer_b):
            customer_b = frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": self.customer_b,
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
            customer_b.insert(ignore_permissions=True)

        # Portal User B
        if not frappe.db.exists(
            "Portal User", {"user": self.user_b, "parent": self.customer_b}
        ):
            portal_b = frappe.get_doc(
                {
                    "doctype": "Portal User",
                    "user": self.user_b,
                    "parent": self.customer_b,
                    "parenttype": "Customer",
                }
            )
            portal_b.insert(ignore_permissions=True)

        # Tenant B
        if not frappe.db.exists("Qalcuity Tenant", {"tenant_id": "TENANT-TEST-B"}):
            tenant_b = frappe.get_doc(
                {
                    "doctype": "Qalcuity Tenant",
                    "customer": self.customer_b,
                    "tenant_id": "TENANT-TEST-B",
                    "status": "Active",
                }
            )
            tenant_b.insert(ignore_permissions=True)

        # Create test subscriptions
        self._create_test_subscriptions()

        # Create test payments
        self._create_test_payments()

    def _create_test_subscriptions(self):
        """Buat test subscriptions untuk kedua customer."""
        plan = frappe.db.exists("Qalcuity Plan", {"is_active": 1})
        if not plan:
            plan_doc = frappe.get_doc(
                {
                    "doctype": "Qalcuity Plan",
                    "plan_name": "Test Plan - Isolation",
                    "price": 99000,
                    "billing_period": "Monthly",
                    "is_active": 1,
                }
            )
            plan_doc.insert(ignore_permissions=True)
            plan = plan_doc.name

        # Subscription A
        if not frappe.db.exists(
            "Qalcuity Subscription", {"customer": self.customer_a}
        ):
            sub_a = frappe.get_doc(
                {
                    "doctype": "Qalcuity Subscription",
                    "customer": self.customer_a,
                    "plan": plan,
                    "status": "Active",
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                }
            )
            sub_a.insert(ignore_permissions=True)

        # Subscription B
        if not frappe.db.exists(
            "Qalcuity Subscription", {"customer": self.customer_b}
        ):
            sub_b = frappe.get_doc(
                {
                    "doctype": "Qalcuity Subscription",
                    "customer": self.customer_b,
                    "plan": plan,
                    "status": "Active",
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                }
            )
            sub_b.insert(ignore_permissions=True)

    def _create_test_payments(self):
        """Buat test payments untuk kedua customer."""
        sub_a = frappe.db.get_value(
            "Qalcuity Subscription", {"customer": self.customer_a}, "name"
        )
        sub_b = frappe.db.get_value(
            "Qalcuity Subscription", {"customer": self.customer_b}, "name"
        )

        if sub_a and not frappe.db.exists(
            "Qalcuity Payment", {"subscription": sub_a}
        ):
            payment_a = frappe.get_doc(
                {
                    "doctype": "Qalcuity Payment",
                    "subscription": sub_a,
                    "amount": 99000,
                    "payment_method": "Bank Transfer",
                    "payment_date": "2026-01-01",
                    "status": "Pending",
                }
            )
            payment_a.insert(ignore_permissions=True)

        if sub_b and not frappe.db.exists(
            "Qalcuity Payment", {"subscription": sub_b}
        ):
            payment_b = frappe.get_doc(
                {
                    "doctype": "Qalcuity Payment",
                    "subscription": sub_b,
                    "amount": 99000,
                    "payment_method": "Bank Transfer",
                    "payment_date": "2026-01-01",
                    "status": "Pending",
                }
            )
            payment_b.insert(ignore_permissions=True)

    # =========================================================================
    # Helper: switch session user
    # =========================================================================

    def _login_as(self, user):
        """Switch session user untuk testing."""
        frappe.set_user(user)

    def _login_as_admin(self):
        """Login sebagai Administrator."""
        frappe.set_user("Administrator")

    # =========================================================================
    # Test: is_admin_user
    # =========================================================================

    def test_admin_user_is_admin(self):
        """System Manager diakui sebagai admin."""
        self.assertTrue(is_admin_user("Administrator"))

    def test_superadmin_is_admin(self):
        """Qalcuity Superadmin diakui sebagai admin."""
        # Buat superadmin user jika belum ada
        user = "test-superadmin@qalcuity.test"
        if not frappe.db.exists("User", user):
            u = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": user,
                    "first_name": "Test Superadmin",
                    "send_welcome_email": 0,
                }
            )
            u.append("roles", {"role": "Qalcuity Superadmin"})
            u.insert(ignore_permissions=True)
        self.assertTrue(is_admin_user(user))

    def test_customer_is_not_admin(self):
        """Customer TIDAK diakui sebagai admin."""
        self.assertFalse(is_admin_user(self.user_a))

    def test_guest_is_not_admin(self):
        """Guest TIDAK diakui sebagai admin."""
        self.assertFalse(is_admin_user("Guest"))

    # =========================================================================
    # Test: get_customer_for_user
    # =========================================================================

    def test_get_customer_for_user_a(self):
        """User A mendapat Customer A."""
        customer = get_customer_for_user(self.user_a)
        self.assertEqual(customer, self.customer_a)

    def test_get_customer_for_user_b(self):
        """User B mendapat Customer B."""
        customer = get_customer_for_user(self.user_b)
        self.assertEqual(customer, self.customer_b)

    def test_get_customer_for_admin(self):
        """Administrator tidak punya customer."""
        customer = get_customer_for_user("Administrator")
        self.assertIsNone(customer)

    def test_get_customer_for_guest(self):
        """Guest tidak punya customer."""
        customer = get_customer_for_user("Guest")
        self.assertIsNone(customer)

    # =========================================================================
    # Test: get_current_customer
    # =========================================================================

    def test_get_current_customer_user_a(self):
        """Session user A mendapat Customer A."""
        self._login_as(self.user_a)
        customer = get_current_customer()
        self.assertEqual(customer, self.customer_a)
        self._login_as_admin()

    def test_get_current_customer_user_b(self):
        """Session user B mendapat Customer B."""
        self._login_as(self.user_b)
        customer = get_current_customer()
        self.assertEqual(customer, self.customer_b)
        self._login_as_admin()

    # =========================================================================
    # Test: get_current_tenant
    # =========================================================================

    def test_get_current_tenant_user_a(self):
        """Session user A mendapat Tenant A."""
        self._login_as(self.user_a)
        tenant = get_current_tenant()
        self.assertIsNotNone(tenant)
        self.assertEqual(tenant.customer, self.customer_a)
        self.assertEqual(tenant.tenant_id, "TENANT-TEST-A")
        self._login_as_admin()

    def test_get_current_tenant_user_b(self):
        """Session user B mendapat Tenant B."""
        self._login_as(self.user_b)
        tenant = get_current_tenant()
        self.assertIsNotNone(tenant)
        self.assertEqual(tenant.customer, self.customer_b)
        self.assertEqual(tenant.tenant_id, "TENANT-TEST-B")
        self._login_as_admin()

    def test_get_current_tenant_admin_returns_none(self):
        """Admin tidak punya tenant."""
        self._login_as_admin()
        tenant = get_current_tenant()
        self.assertIsNone(tenant)

    # =========================================================================
    # Test: get_permission_query_conditions — Qalcuity DocTypes
    # =========================================================================

    def test_query_conditions_subscription_user_a(self):
        """Query conditions untuk Subscription harus filter by Customer A."""
        self._login_as(self.user_a)
        conditions = get_permission_query_conditions(self.user_a, "Qalcuity Subscription")
        self.assertIn(self.customer_a, conditions)
        self.assertNotIn(self.customer_b, conditions)
        self._login_as_admin()

    def test_query_conditions_subscription_user_b(self):
        """Query conditions untuk Subscription harus filter by Customer B."""
        self._login_as(self.user_b)
        conditions = get_permission_query_conditions(self.user_b, "Qalcuity Subscription")
        self.assertIn(self.customer_b, conditions)
        self.assertNotIn(self.customer_a, conditions)
        self._login_as_admin()

    def test_query_conditions_subscription_admin_no_filter(self):
        """Admin mendapat query conditions kosong (full access)."""
        conditions = get_permission_query_conditions("Administrator", "Qalcuity Subscription")
        self.assertEqual(conditions, "")

    def test_query_conditions_tenant_user_a(self):
        """Query conditions untuk Tenant harus filter by Customer A."""
        conditions = get_permission_query_conditions(self.user_a, "Qalcuity Tenant")
        self.assertIn(self.customer_a, conditions)
        self.assertNotIn(self.customer_b, conditions)

    def test_query_conditions_payment_user_a(self):
        """Query conditions untuk Payment harus filter via Subscription."""
        conditions = get_permission_query_conditions(self.user_a, "Qalcuity Payment")
        self.assertIn("Qalcuity Subscription", conditions)
        self.assertIn(self.customer_a, conditions)

    def test_query_conditions_guest_denied(self):
        """Guest mendapat WHERE 1=0 (denied)."""
        conditions = get_permission_query_conditions("Guest", "Qalcuity Subscription")
        self.assertEqual(conditions, "1=0")

    # =========================================================================
    # Test: get_permission_query_conditions — ERPNext DocTypes
    # =========================================================================

    def test_query_conditions_customer_user_a(self):
        """Query conditions untuk Customer DocType harus filter by Customer A."""
        conditions = get_permission_query_conditions(self.user_a, "Customer")
        self.assertIn(self.customer_a, conditions)
        self.assertNotIn(self.customer_b, conditions)

    def test_query_conditions_customer_user_b(self):
        """Query conditions untuk Customer DocType harus filter by Customer B."""
        conditions = get_permission_query_conditions(self.user_b, "Customer")
        self.assertIn(self.customer_b, conditions)
        self.assertNotIn(self.customer_a, conditions)

    def test_query_conditions_customer_admin(self):
        """Admin mendapat query conditions kosong untuk Customer DocType."""
        conditions = get_permission_query_conditions("Administrator", "Customer")
        self.assertEqual(conditions, "")

    # =========================================================================
    # Test: has_permission — Qalcuity DocTypes
    # =========================================================================

    def test_has_permission_subscription_user_a_own(self):
        """User A punya akses read ke Subscription miliknya sendiri."""
        sub_a = frappe.db.get_value(
            "Qalcuity Subscription", {"customer": self.customer_a}, "name"
        )
        doc = frappe.get_doc("Qalcuity Subscription", sub_a)
        self.assertTrue(has_permission(doc, "read", self.user_a))

    def test_has_permission_subscription_user_a_cannot_read_b(self):
        """User A TIDAK punya akses read ke Subscription milik User B."""
        sub_b = frappe.db.get_value(
            "Qalcuity Subscription", {"customer": self.customer_b}, "name"
        )
        doc = frappe.get_doc("Qalcuity Subscription", sub_b)
        self.assertFalse(has_permission(doc, "read", self.user_a))

    def test_has_permission_subscription_user_b_own(self):
        """User B punya akses read ke Subscription miliknya sendiri."""
        sub_b = frappe.db.get_value(
            "Qalcuity Subscription", {"customer": self.customer_b}, "name"
        )
        doc = frappe.get_doc("Qalcuity Subscription", sub_b)
        self.assertTrue(has_permission(doc, "read", self.user_b))

    def test_has_permission_subscription_user_b_cannot_read_a(self):
        """User B TIDAK punya akses read ke Subscription milik User A."""
        sub_a = frappe.db.get_value(
            "Qalcuity Subscription", {"customer": self.customer_a}, "name"
        )
        doc = frappe.get_doc("Qalcuity Subscription", sub_a)
        self.assertFalse(has_permission(doc, "read", self.user_b))

    def test_has_permission_subscription_admin_full_access(self):
        """Admin punya akses penuh ke semua Subscription."""
        sub_a = frappe.db.get_value(
            "Qalcuity Subscription", {"customer": self.customer_a}, "name"
        )
        doc = frappe.get_doc("Qalcuity Subscription", sub_a)
        self.assertTrue(has_permission(doc, "read", "Administrator"))

    def test_has_permission_tenant_user_a_own(self):
        """User A punya akses read ke Tenant miliknya sendiri."""
        tenant_a = frappe.db.get_value(
            "Qalcuity Tenant", {"customer": self.customer_a}, "name"
        )
        doc = frappe.get_doc("Qalcuity Tenant", tenant_a)
        self.assertTrue(has_permission(doc, "read", self.user_a))

    def test_has_permission_tenant_user_a_cannot_read_b(self):
        """User A TIDAK punya akses read ke Tenant milik User B."""
        tenant_b = frappe.db.get_value(
            "Qalcuity Tenant", {"customer": self.customer_b}, "name"
        )
        doc = frappe.get_doc("Qalcuity Tenant", tenant_b)
        self.assertFalse(has_permission(doc, "read", self.user_a))

    def test_has_permission_customer_user_a_own(self):
        """User A punya akses read ke Customer record miliknya sendiri."""
        customer_doc = frappe.get_doc("Customer", self.customer_a)
        self.assertTrue(has_permission(customer_doc, "read", self.user_a))

    def test_has_permission_customer_user_a_cannot_read_b(self):
        """User A TIDAK punya akses read ke Customer record milik User B."""
        customer_doc = frappe.get_doc("Customer", self.customer_b)
        self.assertFalse(has_permission(customer_doc, "read", self.user_a))

    # =========================================================================
    # Test: Cross-tenant isolation — Integration test
    # =========================================================================

    def test_cross_tenant_subscription_isolation(self):
        """
        Skenario: User A query subscriptions, hanya data A yang muncul.
        User B query subscriptions, hanya data B yang muncul.
        """
        # User A queries
        self._login_as(self.user_a)
        subs_a = frappe.get_all(
            "Qalcuity Subscription",
            filters={"customer": ["!=", ""]},
            fields=["name", "customer"],
        )
        # Hanya subscription Customer A yang terlihat
        for sub in subs_a:
            self.assertEqual(sub.customer, self.customer_a)
        self._login_as_admin()

        # User B queries
        self._login_as(self.user_b)
        subs_b = frappe.get_all(
            "Qalcuity Subscription",
            filters={"customer": ["!=", ""]},
            fields=["name", "customer"],
        )
        # Hanya subscription Customer B yang terlihat
        for sub in subs_b:
            self.assertEqual(sub.customer, self.customer_b)
        self._login_as_admin()

    def test_cross_tenant_payment_isolation(self):
        """
        Skenario: User A query payments, hanya data A yang muncul.
        User B query payments, hanya data B yang muncul.
        """
        # User A queries
        self._login_as(self.user_a)
        payments_a = frappe.get_all(
            "Qalcuity Payment",
            filters={"subscription": ["!=", ""]},
            fields=["name", "subscription"],
        )
        for payment in payments_a:
            sub_customer = frappe.db.get_value(
                "Qalcuity Subscription", payment.subscription, "customer"
            )
            self.assertEqual(sub_customer, self.customer_a)
        self._login_as_admin()

        # User B queries
        self._login_as(self.user_b)
        payments_b = frappe.get_all(
            "Qalcuity Payment",
            filters={"subscription": ["!=", ""]},
            fields=["name", "subscription"],
        )
        for payment in payments_b:
            sub_customer = frappe.db.get_value(
                "Qalcuity Subscription", payment.subscription, "customer"
            )
            self.assertEqual(sub_customer, self.customer_b)
        self._login_as_admin()

    def test_superadmin_sees_all_data(self):
        """
        Skenario: Superadmin bisa melihat data dari semua tenant.
        """
        self._login_as_admin()

        # Admin bisa lihat semua subscriptions
        all_subs = frappe.get_all("Qalcuity Subscription", fields=["name", "customer"])
        customers_in_subs = {sub.customer for sub in all_subs}
        self.assertIn(self.customer_a, customers_in_subs)
        self.assertIn(self.customer_b, customers_in_subs)

        # Admin bisa lihat semua tenants
        all_tenants = frappe.get_all(
            "Qalcuity Tenant", fields=["name", "customer"]
        )
        customers_in_tenants = {t.customer for t in all_tenants}
        self.assertIn(self.customer_a, customers_in_tenants)
        self.assertIn(self.customer_b, customers_in_tenants)

    # =========================================================================
    # Test: Cache invalidation
    # =========================================================================

    def test_clear_isolation_cache(self):
        """Clear cache tidak menyebabkan error."""
        clear_isolation_cache(self.user_a)
        clear_isolation_cache()  # Clear all
        # Tidak ada assertion — cukup tidak error

    def test_cache_invalidation_on_customer_lookup(self):
        """Customer lookup menggunakan cache."""
        # First call — populate cache
        customer1 = get_customer_for_user(self.user_a)
        # Second call — should use cache
        customer2 = get_customer_for_user(self.user_a)
        self.assertEqual(customer1, customer2)
        self.assertEqual(customer1, self.customer_a)

    # =========================================================================
    # Test: Edge cases
    # =========================================================================

    def test_non_customer_role_no_filter(self):
        """User tanpa role Customer mendapat query conditions kosong."""
        # Buat user tanpa role Customer
        user = "test-non-customer@qalcuity.test"
        if not frappe.db.exists("User", user):
            u = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": user,
                    "first_name": "Non Customer User",
                    "send_welcome_email": 0,
                }
            )
            u.append("roles", {"role": "Employee"})
            u.insert(ignore_permissions=True)

        conditions = get_permission_query_conditions(user, "Qalcuity Subscription")
        # Non-customer user gets empty conditions (Frappe handles role-based perm)
        self.assertEqual(conditions, "")

    def test_user_without_portal_user_denied(self):
        """User dengan role Customer tapi tanpa Portal User ditolak."""
        # Buat user dengan role Customer tapi TANPA Portal User
        user = "test-no-portal@qalcuity.test"
        if not frappe.db.exists("User", user):
            u = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": user,
                    "first_name": "No Portal User",
                    "send_welcome_email": 0,
                }
            )
            u.append("roles", {"role": "Customer"})
            u.insert(ignore_permissions=True)

        conditions = get_permission_query_conditions(user, "Qalcuity Subscription")
        # Tanpa Portal User → tidak bisa akses data apapun
        self.assertEqual(conditions, "1=0")
