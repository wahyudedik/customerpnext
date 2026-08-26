# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Module Enforcement Validation — Comprehensive Test Suite
=========================================================

Sprint 11 Task 3: Verifikasi module enforcement berfungsi dengan benar.

Setiap plan (Starter, Business, Professional) mengontrol modul ERPNext
mana yang bisa diakses customer. Test ini memvalidasi bahwa:

1. Plan memiliki modules yang terkonfigurasi
2. User hanya bisa akses modul yang diaktifkan di plan
3. User TIDAK bisa akses modul yang tidak diaktifkan
4. Plan change (upgrade/downgrade) langsung mempengaruhi akses
5. Edge cases: expired, suspended, no plan

Arsitektur Enforcement:
- Qalcuity Plan → enabled_modules (child table Qalcuity Plan Module)
- Qalcuity Subscription → links customer to plan
- module_enforcement.py → get_user_enabled_modules(), is_module_enabled_for_user()
- erpnext_hooks.py → permission query conditions + has_permission hooks

Test Categories:
A. Plan Module Configuration (test_01 — test_04)
B. Module Access Enforcement (test_05 — test_08)
C. Plan Change Impact (test_09 — test_11)
D. Edge Cases (test_12 — test_14)
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate, add_days

from qalcuity.module_enforcement import (
    get_user_enabled_modules,
    is_module_enabled_for_user,
    is_doctype_enabled_for_user,
    get_module_block_message,
    get_enabled_modules_for_plan,
    MODULE_DOCTYPE_MAP,
)


class TestModuleEnforcement(IntegrationTestCase):
    """
    Comprehensive module enforcement test suite.

    Creates 3 test plans (Starter, Business, Professional) with different
    module configurations, then validates that enforcement works correctly
    for users assigned to each plan.
    """

    # =========================================================================
    # Setup & Teardown
    # =========================================================================

    def setUp(self):
        """Setup test plans, users, and subscriptions."""
        self._cleanup_all_test_data()
        self._create_test_roles()
        self._create_test_plans()
        self._create_test_users_and_subscriptions()
        frappe.db.commit()

    def tearDown(self):
        """Clean up all test data."""
        self._cleanup_all_test_data()
        frappe.db.commit()

    # =========================================================================
    # Helpers — Cleanup
    # =========================================================================

    def _cleanup_all_test_data(self):
        """Hapus semua test data yang mungkin tertinggal."""
        prefix = "Test Module Enforcement"

        # Hapus test payments
        for sub in frappe.get_all(
            "Qalcuity Subscription",
            filters={"customer": ["like", f"{prefix}%"]},
            fields=["name"],
        ):
            for pay in frappe.get_all(
                "Qalcuity Payment",
                filters={"subscription": sub.name},
                fields=["name"],
            ):
                frappe.delete_doc("Qalcuity Payment", pay.name, ignore_permissions=True)

        # Hapus test subscriptions
        frappe.db.sql(
            f"DELETE FROM `tabQalcuity Subscription` WHERE customer LIKE '{prefix}%%'"
        )

        # Hapus test tenants
        for tenant in frappe.get_all(
            "Qalcuity Tenant",
            filters={"customer": ["like", f"{prefix}%"]},
            fields=["name"],
        ):
            frappe.delete_doc("Qalcuity Tenant", tenant.name, ignore_permissions=True)

        # Hapus test portal users
        frappe.db.sql(
            f"DELETE FROM `tabPortal User` WHERE user LIKE 'test-mod-enf-%%@qalcuity.test'"
        )

        # Hapus test customers
        for customer_name in frappe.get_all(
            "Customer",
            filters={"customer_name": ["like", f"{prefix}%"]},
            fields=["name"],
        ):
            frappe.delete_doc("Customer", customer_name.name, ignore_permissions=True)

        # Hapus test users
        for email in [
            "test-mod-enf-starter@qalcuity.test",
            "test-mod-enf-business@qalcuity.test",
            "test-mod-enf-professional@qalcuity.test",
            "test-mod-enf-expired@qalcuity.test",
            "test-mod-enf-suspended@qalcuity.test",
            "test-mod-enf-noplan@qalcuity.test",
            "test-mod-enf-upgrade@qalcuity.test",
            "test-mod-enf-downgrade@qalcuity.test",
        ]:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, ignore_permissions=True)

        frappe.db.commit()

    # =========================================================================
    # Helpers — Roles
    # =========================================================================

    def _create_test_roles(self):
        """Pastikan test roles ada."""
        for role_name in [
            "Qalcuity Superadmin",
            "Qalcuity Admin",
            "Qalcuity ERP User",
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

    # =========================================================================
    # Helpers — Plan Creation
    # =========================================================================

    def _create_plan_with_modules(self, plan_name, modules_list, price=99000, max_users=3, max_storage_gb=5):
        """
        Helper: create a Qalcuity Plan with specific modules.

        Args:
            plan_name: Unique plan name
            modules_list: List of module names (e.g., ["Accounting", "Sales"])
            price: Plan price (default: 99000)
            max_users: Max users (default: 3)
            max_storage_gb: Max storage GB (default: 5)

        Returns:
            str: Plan name (docname)
        """
        existing = frappe.db.exists("Qalcuity Plan", {"plan_name": plan_name})
        if existing:
            return existing

        plan = frappe.get_doc(
            {
                "doctype": "Qalcuity Plan",
                "plan_name": plan_name,
                "description": f"Test plan: {plan_name}",
                "price": price,
                "currency": "IDR",
                "billing_period": "Monthly",
                "is_active": 1,
                "is_trial": 0,
                "max_users": max_users,
                "max_storage_gb": max_storage_gb,
                "sort_order": 99,
            }
        )

        # Add features based on modules
        for module_name in modules_list:
            plan.append("features", {"feature_name": module_name})

        # Add enabled modules
        for module_name in modules_list:
            plan.append("enabled_modules", {"module_name": module_name})

        plan.insert(ignore_permissions=True)
        frappe.db.commit()
        return plan.name

    def _create_test_plans(self):
        """Create 3 test plans with different module configurations."""
        # Starter: Limited modules (Accounting, Sales, Purchasing)
        self.plan_starter = self._create_plan_with_modules(
            plan_name="Test MOD Starter",
            modules_list=["Accounting", "Sales", "Purchasing"],
            price=99000,
            max_users=3,
            max_storage_gb=5,
        )

        # Business: More modules (+ CRM, Inventory, HR, Projects)
        self.plan_business = self._create_plan_with_modules(
            plan_name="Test MOD Business",
            modules_list=["Accounting", "Sales", "Purchasing", "CRM", "Inventory", "HR", "Projects"],
            price=299000,
            max_users=10,
            max_storage_gb=20,
        )

        # Professional: All modules
        self.plan_professional = self._create_plan_with_modules(
            plan_name="Test MOD Professional",
            modules_list=[
                "Accounting", "CRM", "Sales", "Purchasing",
                "Inventory", "Projects", "HR", "Manufacturing",
                "Support", "Assets",
            ],
            price=599000,
            max_users=50,
            max_storage_gb=100,
        )

    # =========================================================================
    # Helpers — User & Subscription Creation
    # =========================================================================

    def _create_user_with_customer(self, email, full_name, company_name):
        """
        Create a test User, Customer, Portal User, and Tenant.

        Args:
            email: User email
            full_name: Full name
            company_name: Customer/company name

        Returns:
            dict: {user, customer, tenant}
        """
        # Create User
        if not frappe.db.exists("User", email):
            user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": email,
                    "first_name": full_name,
                    "full_name": full_name,
                    "user_type": "Website User",
                    "send_welcome_email": 0,
                    "disabled": 0,
                }
            )
            user.append("roles", {"role": "Customer"})
            user.insert(ignore_permissions=True)

        # Create Customer
        if not frappe.db.exists("Customer", company_name):
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
                }
            )
            customer.insert(ignore_permissions=True)

        # Create Portal User
        if not frappe.db.exists(
            "Portal User", {"user": email, "parent": company_name}
        ):
            portal = frappe.get_doc(
                {
                    "doctype": "Portal User",
                    "user": email,
                    "parent": company_name,
                    "parenttype": "Customer",
                }
            )
            portal.insert(ignore_permissions=True)

        # Create Tenant
        tenant_id = f"MOD-TEST-{email.split('@')[0].replace('test-mod-enf-', '').upper()}"
        if not frappe.db.exists("Qalcuity Tenant", {"tenant_id": tenant_id}):
            tenant = frappe.get_doc(
                {
                    "doctype": "Qalcuity Tenant",
                    "customer": company_name,
                    "tenant_id": tenant_id,
                    "status": "Active",
                }
            )
            tenant.insert(ignore_permissions=True)

        frappe.db.commit()

        tenant_name = frappe.db.get_value(
            "Qalcuity Tenant", {"tenant_id": tenant_id}, "name"
        )

        return {
            "user": email,
            "customer": company_name,
            "tenant": tenant_name,
        }

    def _assign_plan_to_user(self, customer_name, plan_name, status="Active"):
        """
        Assign a plan to a customer via Qalcuity Subscription.

        Args:
            customer_name: Customer name
            plan_name: Qalcuity Plan name
            status: Subscription status (default: "Active")

        Returns:
            str: Subscription name
        """
        # Delete existing subscription for this customer
        existing = frappe.db.get_value(
            "Qalcuity Subscription", {"customer": customer_name}, "name"
        )
        if existing:
            frappe.delete_doc("Qalcuity Subscription", existing, ignore_permissions=True)

        sub = frappe.get_doc(
            {
                "doctype": "Qalcuity Subscription",
                "customer": customer_name,
                "plan": plan_name,
                "status": status,
                "start_date": nowdate(),
                "end_date": add_days(nowdate(), 30),
            }
        )
        sub.insert(ignore_permissions=True)
        frappe.db.commit()
        return sub.name

    def _create_test_users_and_subscriptions(self):
        """Create test users with subscriptions for each plan level."""
        # Starter user
        self.user_starter = self._create_user_with_customer(
            email="test-mod-enf-starter@qalcuity.test",
            full_name="Test Module Enforcement Starter",
            company_name="Test Module Enforcement Starter Co",
        )
        self._assign_plan_to_user(
            self.user_starter["customer"], self.plan_starter, "Active"
        )

        # Business user
        self.user_business = self._create_user_with_customer(
            email="test-mod-enf-business@qalcuity.test",
            full_name="Test Module Enforcement Business",
            company_name="Test Module Enforcement Business Co",
        )
        self._assign_plan_to_user(
            self.user_business["customer"], self.plan_business, "Active"
        )

        # Professional user
        self.user_professional = self._create_user_with_customer(
            email="test-mod-enf-professional@qalcuity.test",
            full_name="Test Module Enforcement Professional",
            company_name="Test Module Enforcement Professional Co",
        )
        self._assign_plan_to_user(
            self.user_professional["customer"], self.plan_professional, "Active"
        )

        # Expired subscription user
        self.user_expired = self._create_user_with_customer(
            email="test-mod-enf-expired@qalcuity.test",
            full_name="Test Module Enforcement Expired",
            company_name="Test Module Enforcement Expired Co",
        )
        self._assign_plan_to_user(
            self.user_expired["customer"], self.plan_starter, "Expired"
        )

        # Suspended subscription user
        self.user_suspended = self._create_user_with_customer(
            email="test-mod-enf-suspended@qalcuity.test",
            full_name="Test Module Enforcement Suspended",
            company_name="Test Module Enforcement Suspended Co",
        )
        self._assign_plan_to_user(
            self.user_suspended["customer"], self.plan_starter, "Suspended"
        )

        # No plan user (no subscription)
        self.user_noplan = self._create_user_with_customer(
            email="test-mod-enf-noplan@qalcuity.test",
            full_name="Test Module Enforcement NoPlan",
            company_name="Test Module Enforcement NoPlan Co",
        )

        # Upgrade test user
        self.user_upgrade = self._create_user_with_customer(
            email="test-mod-enf-upgrade@qalcuity.test",
            full_name="Test Module Enforcement Upgrade",
            company_name="Test Module Enforcement Upgrade Co",
        )
        self._assign_plan_to_user(
            self.user_upgrade["customer"], self.plan_starter, "Active"
        )

        # Downgrade test user
        self.user_downgrade = self._create_user_with_customer(
            email="test-mod-enf-downgrade@qalcuity.test",
            full_name="Test Module Enforcement Downgrade",
            company_name="Test Module Enforcement Downgrade Co",
        )
        self._assign_plan_to_user(
            self.user_downgrade["customer"], self.plan_professional, "Active"
        )

    # =========================================================================
    # Helpers — Access Check
    # =========================================================================

    def _check_module_access(self, user_email, module_name):
        """
        Helper: check if user can access specific module.

        Args:
            user_email: User email
            module_name: Module name (e.g., "Accounting", "Sales")

        Returns:
            bool: True if access allowed, False if blocked
        """
        return is_module_enabled_for_user(module_name, user_email)

    def _check_doctype_access(self, user_email, doctype_name):
        """
        Helper: check if user can access specific DocType.

        Args:
            user_email: User email
            doctype_name: ERPNext DocType name

        Returns:
            bool: True if access allowed, False if blocked
        """
        return is_doctype_enabled_for_user(doctype_name, user_email)

    # =========================================================================
    # A. Plan Module Configuration
    # =========================================================================

    def test_01_plan_has_modules_configured(self):
        """
        Verify that plans have modules configured in Qalcuity Plan Module.

        Each plan should have at least one module configured in the
        enabled_modules child table.
        """
        # Check Starter plan has modules
        starter_modules = get_enabled_modules_for_plan(self.plan_starter)
        self.assertGreater(
            len(starter_modules), 0,
            "Starter plan harus memiliki modules yang dikonfigurasi",
        )

        # Check Business plan has modules
        business_modules = get_enabled_modules_for_plan(self.plan_business)
        self.assertGreater(
            len(business_modules), 0,
            "Business plan harus memiliki modules yang dikonfigurasi",
        )

        # Check Professional plan has modules
        professional_modules = get_enabled_modules_for_plan(self.plan_professional)
        self.assertGreater(
            len(professional_modules), 0,
            "Professional plan harus memiliki modules yang dikonfigurasi",
        )

        # Verify modules are valid (must be in MODULE_DOCTYPE_MAP)
        all_valid_modules = set(MODULE_DOCTYPE_MAP.keys())
        for plan_name, modules in [
            (self.plan_starter, starter_modules),
            (self.plan_business, business_modules),
            (self.plan_professional, professional_modules),
        ]:
            for module in modules:
                self.assertIn(
                    module, all_valid_modules,
                    f"Module '{module}' di plan '{plan_name}' harus valid "
                    f"(ada di MODULE_DOCTYPE_MAP)",
                )

    def test_02_starter_plan_limited_modules(self):
        """
        Verify Starter plan only has limited modules (Accounting, Sales, Purchasing).

        Starter plan tidak boleh memiliki modules lanjutan seperti HR,
        Projects, Manufacturing, Support, Assets.
        """
        starter_modules = get_enabled_modules_for_plan(self.plan_starter)

        # Starter harus punya modul dasar
        self.assertIn("Accounting", starter_modules, "Starter harus punya Accounting")
        self.assertIn("Sales", starter_modules, "Starter harus punya Sales")
        self.assertIn("Purchasing", starter_modules, "Starter harus punya Purchasing")

        # Starter TIDAK boleh punya modul lanjutan
        self.assertNotIn("HR", starter_modules, "Starter TIDAK boleh punya HR")
        self.assertNotIn("Projects", starter_modules, "Starter TIDAK boleh punya Projects")
        self.assertNotIn("Manufacturing", starter_modules, "Starter TIDAK boleh punya Manufacturing")
        self.assertNotIn("Support", starter_modules, "Starter TIDAK boleh punya Support")
        self.assertNotIn("Assets", starter_modules, "Starter TIDAK boleh punya Assets")

        # Starter juga tidak boleh punya CRM dan Inventory (berdasarkan seed config)
        self.assertNotIn("CRM", starter_modules, "Starter TIDAK boleh punya CRM")
        self.assertNotIn("Inventory", starter_modules, "Starter TIDAK boleh punya Inventory")

        # Verifikasi jumlah modul
        self.assertEqual(
            len(starter_modules), 3,
            "Starter plan harus memiliki tepat 3 modules",
        )

    def test_03_business_plan_more_modules(self):
        """
        Verify Business plan has more modules than Starter.

        Business plan harus memiliki setidaknya modul di Starter +
        beberapa modul tambahan (CRM, Inventory, HR, Projects).
        """
        starter_modules = set(get_enabled_modules_for_plan(self.plan_starter))
        business_modules = set(get_enabled_modules_for_plan(self.plan_business))

        # Business harus lebih banyak dari Starter
        self.assertGreater(
            len(business_modules), len(starter_modules),
            "Business plan harus memiliki lebih banyak modules dari Starter",
        )

        # Business harus mencakup semua modul Starter
        self.assertTrue(
            starter_modules.issubset(business_modules),
            "Business plan harus mencakup semua modul Starter",
        )

        # Business harus punya modul tambahan
        self.assertIn("CRM", business_modules, "Business harus punya CRM")
        self.assertIn("Inventory", business_modules, "Business harus punya Inventory")
        self.assertIn("HR", business_modules, "Business harus punya HR")
        self.assertIn("Projects", business_modules, "Business harus punya Projects")

        # Business tidak boleh punya Manufacturing, Support, Assets
        self.assertNotIn("Manufacturing", business_modules, "Business TIDAK boleh punya Manufacturing")
        self.assertNotIn("Support", business_modules, "Business TIDAK boleh punya Support")
        self.assertNotIn("Assets", business_modules, "Business TIDAK boleh punya Assets")

    def test_04_professional_plan_all_modules(self):
        """
        Verify Professional plan has all available modules.

        Professional plan harus mencakup semua modul yang tersedia
        di MODULE_DOCTYPE_MAP.
        """
        professional_modules = set(get_enabled_modules_for_plan(self.plan_professional))
        all_modules = set(MODULE_DOCTYPE_MAP.keys())

        # Professional harus mencakup semua modul
        self.assertEqual(
            professional_modules, all_modules,
            "Professional plan harus memiliki SEMUA modules yang tersedia",
        )

        # Verifikasi setiap modul ada
        for module_name in all_modules:
            self.assertIn(
                module_name, professional_modules,
                f"Professional plan harus punya modul '{module_name}'",
            )

    # =========================================================================
    # B. Module Access Enforcement
    # =========================================================================

    def test_05_user_can_access_allowed_module(self):
        """
        Verify user can access a module that IS in their plan.

        Starter user harus bisa akses Accounting, Sales, Purchasing.
        Business user harus bisa akses semua modul Business.
        Professional user harus bisa akses semua modul.
        """
        # Starter user — allowed modules
        self.assertTrue(
            self._check_module_access(self.user_starter["user"], "Accounting"),
            "Starter user harus bisa akses Accounting",
        )
        self.assertTrue(
            self._check_module_access(self.user_starter["user"], "Sales"),
            "Starter user harus bisa akses Sales",
        )
        self.assertTrue(
            self._check_module_access(self.user_starter["user"], "Purchasing"),
            "Starter user harus bisa akses Purchasing",
        )

        # Business user — allowed modules
        self.assertTrue(
            self._check_module_access(self.user_business["user"], "Accounting"),
            "Business user harus bisa akses Accounting",
        )
        self.assertTrue(
            self._check_module_access(self.user_business["user"], "HR"),
            "Business user harus bisa akses HR",
        )
        self.assertTrue(
            self._check_module_access(self.user_business["user"], "Projects"),
            "Business user harus bisa akses Projects",
        )

        # Professional user — all modules
        for module_name in MODULE_DOCTYPE_MAP:
            self.assertTrue(
                self._check_module_access(self.user_professional["user"], module_name),
                f"Professional user harus bisa akses {module_name}",
            )

    def test_06_user_blocked_from_disallowed_module(self):
        """
        Verify user CANNOT access a module that is NOT in their plan.

        Starter user harus DIBLOKIR dari HR, Projects, Manufacturing,
        CRM, Inventory, Support, Assets.
        """
        # Starter user — blocked modules
        blocked_modules = ["HR", "Projects", "Manufacturing", "CRM", "Inventory", "Support", "Assets"]
        for module_name in blocked_modules:
            self.assertFalse(
                self._check_module_access(self.user_starter["user"], module_name),
                f"Starter user harus DIBLOKIR dari modul {module_name}",
            )

        # Business user — blocked modules (Manufacturing, Support, Assets)
        business_blocked = ["Manufacturing", "Support", "Assets"]
        for module_name in business_blocked:
            self.assertFalse(
                self._check_module_access(self.user_business["user"], module_name),
                f"Business user harus DIBLOKIR dari modul {module_name}",
            )

    def test_07_module_access_via_workspace(self):
        """
        Verify workspace shortcuts respect module enforcement.

        Test ini memvalidasi bahwa DocType-level enforcement bekerja
        dengan benar — DocType yang termasuk dalam modul yang diblokir
        juga harus diblokir.

        Contoh: Starter user tidak punya modul HR, maka Employee DocType
        (yang termasuk HR) juga harus diblokir.
        """
        # Starter user — DocType access
        # Sales module (allowed)
        self.assertTrue(
            self._check_doctype_access(self.user_starter["user"], "Sales Order"),
            "Starter user harus bisa akses Sales Order (Sales module)",
        )
        self.assertTrue(
            self._check_doctype_access(self.user_starter["user"], "Customer"),
            "Starter user harus bisa akses Customer (Sales module)",
        )

        # Accounting module (allowed)
        self.assertTrue(
            self._check_doctype_access(self.user_starter["user"], "Journal Entry"),
            "Starter user harus bisa akses Journal Entry (Accounting module)",
        )
        self.assertTrue(
            self._check_doctype_access(self.user_starter["user"], "Payment Entry"),
            "Starter user harus bisa akses Payment Entry (Accounting module)",
        )

        # Purchasing module (allowed)
        self.assertTrue(
            self._check_doctype_access(self.user_starter["user"], "Purchase Order"),
            "Starter user harus bisa akses Purchase Order (Purchasing module)",
        )

        # HR module (blocked)
        self.assertFalse(
            self._check_doctype_access(self.user_starter["user"], "Employee"),
            "Starter user harus DIBLOKIR dari Employee (HR module)",
        )
        self.assertFalse(
            self._check_doctype_access(self.user_starter["user"], "Attendance"),
            "Starter user harus DIBLOKIR dari Attendance (HR module)",
        )

        # Manufacturing module (blocked)
        self.assertFalse(
            self._check_doctype_access(self.user_starter["user"], "BOM"),
            "Starter user harus DIBLOKIR dari BOM (Manufacturing module)",
        )
        self.assertFalse(
            self._check_doctype_access(self.user_starter["user"], "Work Order"),
            "Starter user harus DIBLOKIR dari Work Order (Manufacturing module)",
        )

        # Projects module (blocked)
        self.assertFalse(
            self._check_doctype_access(self.user_starter["user"], "Project"),
            "Starter user harus DIBLOKIR dari Project (Projects module)",
        )
        self.assertFalse(
            self._check_doctype_access(self.user_starter["user"], "Task"),
            "Starter user harus DIBLOKIR dari Task (Projects module)",
        )

    def test_08_module_access_via_api(self):
        """
        Verify API endpoints respect module enforcement.

        Test ini memvalidasi bahwa get_module_block_message() mengembalikan
        pesan yang tepat untuk modul yang diblokir, dan bahwa DocType-level
        check konsisten dengan module-level check.
        """
        # Verify block message for blocked module
        block_msg = get_module_block_message("Employee", self.user_starter["user"])
        self.assertIsNotNone(block_msg, "Block message harus ada untuk modul yang diblokir")
        self.assertIn("HR", block_msg, "Block message harus menyebutkan nama modul (HR)")
        self.assertIn("not available", block_msg.lower(), "Block message harus menyatakan tidak tersedia")

        # Verify consistency: if module is blocked, its DocTypes are also blocked
        for module_name, doctypes in MODULE_DOCTYPE_MAP.items():
            if not self._check_module_access(self.user_starter["user"], module_name):
                # Module is blocked — all its DocTypes should also be blocked
                for doctype_name in doctypes:
                    self.assertFalse(
                        self._check_doctype_access(self.user_starter["user"], doctype_name),
                        f"DocType '{doctype_name}' harus diblokir karena modul '{module_name}' "
                        f"tidak aktif di plan Starter",
                    )

        # Verify consistency: if module is allowed, at least some DocTypes are allowed
        for module_name, doctypes in MODULE_DOCTYPE_MAP.items():
            if self._check_module_access(self.user_starter["user"], module_name):
                # Module is allowed — DocTypes should also be allowed
                for doctype_name in doctypes:
                    self.assertTrue(
                        self._check_doctype_access(self.user_starter["user"], doctype_name),
                        f"DocType '{doctype_name}' harus diizinkan karena modul '{module_name}' "
                        f"aktif di plan Starter",
                    )

    # =========================================================================
    # C. Plan Change Impact
    # =========================================================================

    def test_09_upgrade_adds_modules(self):
        """
        Verify upgrading plan adds new modules to user's access.

        Upgrade dari Starter ke Business harus menambahkan modul
        CRM, Inventory, HR, Projects ke akses user.
        """
        # Verify Starter access (before upgrade)
        starter_modules_before = set(get_user_enabled_modules(self.user_upgrade["user"]))
        self.assertNotIn("HR", starter_modules_before, "Sebelum upgrade, HR harus blocked")

        # Perform upgrade: change subscription plan to Business
        sub_name = frappe.db.get_value(
            "Qalcuity Subscription",
            {"customer": self.user_upgrade["customer"]},
            "name",
        )
        self.assertIsNotNone(sub_name, "Subscription harus ada")

        sub_doc = frappe.get_doc("Qalcuity Subscription", sub_name)
        sub_doc.plan = self.plan_business
        sub_doc.save(ignore_permissions=True)
        frappe.db.commit()

        # Verify Business access (after upgrade)
        upgraded_modules = set(get_user_enabled_modules(self.user_upgrade["user"]))

        # New modules should be available
        self.assertIn("HR", upgraded_modules, "Setelah upgrade ke Business, HR harus tersedia")
        self.assertIn("Projects", upgraded_modules, "Setelah upgrade ke Business, Projects harus tersedia")
        self.assertIn("CRM", upgraded_modules, "Setelah upgrade ke Business, CRM harus tersedia")
        self.assertIn("Inventory", upgraded_modules, "Setelah upgrade ke Business, Inventory harus tersedia")

        # Original modules should still be available
        self.assertIn("Accounting", upgraded_modules, "Accounting harus tetap tersedia")
        self.assertIn("Sales", upgraded_modules, "Sales harus tetap tersedia")
        self.assertIn("Purchasing", upgraded_modules, "Purchasing harus tetap tersedia")

        # Modules not in Business should still be blocked
        self.assertNotIn("Manufacturing", upgraded_modules, "Manufacturing masih harus blocked")

        # Verify module check functions reflect the change
        self.assertTrue(
            is_module_enabled_for_user("HR", self.user_upgrade["user"]),
            "HR harus enabled setelah upgrade",
        )
        self.assertFalse(
            is_module_enabled_for_user("Manufacturing", self.user_upgrade["user"]),
            "Manufacturing harus tetap blocked setelah upgrade ke Business",
        )

    def test_10_downgrade_removes_modules(self):
        """
        Verify downgrading plan removes modules from user's access.

        Downgrade dari Professional ke Starter harus menghapus
        HR, Projects, Manufacturing, CRM, Inventory, Support, Assets.
        """
        # Verify Professional access (before downgrade)
        prof_modules_before = set(get_user_enabled_modules(self.user_downgrade["user"]))
        self.assertIn("HR", prof_modules_before, "Sebelum downgrade, HR harus tersedia")
        self.assertIn("Manufacturing", prof_modules_before, "Sebelum downgrade, Manufacturing harus tersedia")

        # Perform downgrade: change subscription plan to Starter
        sub_name = frappe.db.get_value(
            "Qalcuity Subscription",
            {"customer": self.user_downgrade["customer"]},
            "name",
        )
        self.assertIsNotNone(sub_name, "Subscription harus ada")

        sub_doc = frappe.get_doc("Qalcuity Subscription", sub_name)
        sub_doc.plan = self.plan_starter
        sub_doc.save(ignore_permissions=True)
        frappe.db.commit()

        # Verify Starter access (after downgrade)
        downgraded_modules = set(get_user_enabled_modules(self.user_downgrade["user"]))

        # Removed modules should NOT be available
        removed_modules = ["HR", "Projects", "Manufacturing", "CRM", "Inventory", "Support", "Assets"]
        for module_name in removed_modules:
            self.assertNotIn(
                module_name, downgraded_modules,
                f"Setelah downgrade ke Starter, {module_name} harus dihapus",
            )

        # Original Starter modules should still be available
        self.assertIn("Accounting", downgraded_modules, "Accounting harus tetap tersedia")
        self.assertIn("Sales", downgraded_modules, "Sales harus tetap tersedia")
        self.assertIn("Purchasing", downgraded_modules, "Purchasing harus tetap tersedia")

        # Verify module check functions reflect the change
        self.assertFalse(
            is_module_enabled_for_user("HR", self.user_downgrade["user"]),
            "HR harus diblokir setelah downgrade",
        )
        self.assertFalse(
            is_module_enabled_for_user("Manufacturing", self.user_downgrade["user"]),
            "Manufacturing harus diblokir setelah downgrade",
        )
        self.assertTrue(
            is_module_enabled_for_user("Accounting", self.user_downgrade["user"]),
            "Accounting harus tetap enabled setelah downgrade",
        )

    def test_11_plan_change_reflects_immediately(self):
        """
        Verify plan change takes effect immediately (not after re-login).

        Setelah mengubah plan di subscription, module access harus langsung
        berubah tanpa perlu session baru.
        """
        # Use the upgrade user — currently on Starter
        user_email = self.user_upgrade["user"]

        # Verify current state: Starter plan
        modules_before = get_user_enabled_modules(user_email)
        self.assertIn("Sales", modules_before, "Sebelum change, Sales harus tersedia")
        self.assertNotIn("HR", modules_before, "Sebelum change, HR harus blocked")

        # Change plan to Professional (all modules)
        sub_name = frappe.db.get_value(
            "Qalcuity Subscription",
            {"customer": self.user_upgrade["customer"]},
            "name",
        )
        sub_doc = frappe.get_doc("Qalcuity Subscription", sub_name)
        sub_doc.plan = self.plan_professional
        sub_doc.save(ignore_permissions=True)
        frappe.db.commit()

        # Verify IMMEDIATELY — no cache clear, no re-login
        modules_after = get_user_enabled_modules(user_email)

        # All modules should be available NOW
        self.assertIn("HR", modules_after, "HR harus tersedia SEGERA setelah plan change")
        self.assertIn("Manufacturing", modules_after, "Manufacturing harus tersedia SEGERA setelah plan change")
        self.assertIn("Support", modules_after, "Support harus tersedia SEGERA setelah plan change")
        self.assertIn("Assets", modules_after, "Assets harus tersedia SEGERA setelah plan change")

        # Verify individual module checks also reflect immediately
        self.assertTrue(
            is_module_enabled_for_user("HR", user_email),
            "HR harus enabled SEGERA setelah plan change",
        )
        self.assertTrue(
            is_module_enabled_for_user("Manufacturing", user_email),
            "Manufacturing harus enabled SEGERA setelah plan change",
        )

        # Now change back to Starter — modules should be removed immediately
        sub_doc = frappe.get_doc("Qalcuity Subscription", sub_name)
        sub_doc.plan = self.plan_starter
        sub_doc.save(ignore_permissions=True)
        frappe.db.commit()

        modules_reverted = get_user_enabled_modules(user_email)
        self.assertNotIn("HR", modules_reverted, "HR harus blocked SEGERA setelah revert ke Starter")
        self.assertNotIn("Manufacturing", modules_reverted, "Manufacturing harus blocked SEGERA setelah revert")

    # =========================================================================
    # D. Edge Cases
    # =========================================================================

    def test_12_user_without_plan_cannot_access_modules(self):
        """
        Verify user without any plan/subscription cannot access ERP modules.

        User tanpa subscription harus diblokir dari akses module ERPNext.
        """
        user_email = self.user_noplan["user"]

        # User without subscription should still have module access check
        # The module enforcement checks subscription status first
        enabled_modules = get_user_enabled_modules(user_email)

        # For user without subscription, get_user_enabled_modules returns None
        # (because there's no subscription to check), which means no restriction
        # at the module level. However, subscription enforcement in erpnext_hooks.py
        # blocks access via _has_active_subscription() returning False.
        #
        # This test verifies that the subscription check works correctly.

        from qalcuity.erpnext_hooks import _has_active_subscription

        has_sub = _has_active_subscription(user_email)
        self.assertFalse(
            has_sub,
            "User tanpa subscription harus DIBLOKIR oleh subscription enforcement",
        )

        # Verify that permission query conditions block access
        from qalcuity.erpnext_hooks import (
            get_customer_permission_query_conditions,
            get_sales_order_permission_query_conditions,
        )

        pqc_customer = get_customer_permission_query_conditions(
            user_email, "Customer"
        )
        self.assertEqual(
            pqc_customer, "1=0",
            "Permission query condition harus memblokir akses Customer "
            "untuk user tanpa subscription",
        )

        pqc_so = get_sales_order_permission_query_conditions(
            user_email, "Sales Order"
        )
        self.assertEqual(
            pqc_so, "1=0",
            "Permission query condition harus memblokir akses Sales Order "
            "untuk user tanpa subscription",
        )

    def test_13_expired_subscription_blocks_modules(self):
        """
        Verify expired subscription blocks all module access.

        User dengan subscription Expired harus diblokir dari semua
        akses ERPNext module.
        """
        user_email = self.user_expired["user"]

        # Verify subscription status is Expired
        sub_status = frappe.db.get_value(
            "Qalcuity Subscription",
            {"customer": self.user_expired["customer"]},
            "status",
        )
        self.assertEqual(
            sub_status, "Expired",
            "Subscription status harus Expired",
        )

        # Verify subscription enforcement blocks access
        from qalcuity.erpnext_hooks import _has_active_subscription

        has_sub = _has_active_subscription(user_email)
        self.assertFalse(
            has_sub,
            "User dengan subscription Expired harus DIBLOKIR",
        )

        # Verify permission query conditions block access
        from qalcuity.erpnext_hooks import (
            get_customer_permission_query_conditions,
            get_sales_order_permission_query_conditions,
            get_sales_invoice_permission_query_conditions,
            get_purchase_order_permission_query_conditions,
        )

        for doctype, pqc_func in [
            ("Customer", get_customer_permission_query_conditions),
            ("Sales Order", get_sales_order_permission_query_conditions),
            ("Sales Invoice", get_sales_invoice_permission_query_conditions),
            ("Purchase Order", get_purchase_order_permission_query_conditions),
        ]:
            pqc = pqc_func(user_email, doctype)
            self.assertEqual(
                pqc, "1=0",
                f"Expired subscription harus memblokir akses {doctype} "
                f"(query condition harus '1=0')",
            )

    def test_14_suspended_subscription_blocks_modules(self):
        """
        Verify suspended subscription blocks all module access.

        User dengan subscription Suspended harus diblokir dari semua
        akses ERPNext module.
        """
        user_email = self.user_suspended["user"]

        # Verify subscription status is Suspended
        sub_status = frappe.db.get_value(
            "Qalcuity Subscription",
            {"customer": self.user_suspended["customer"]},
            "status",
        )
        self.assertEqual(
            sub_status, "Suspended",
            "Subscription status harus Suspended",
        )

        # Verify subscription enforcement blocks access
        from qalcuity.erpnext_hooks import _has_active_subscription

        has_sub = _has_active_subscription(user_email)
        self.assertFalse(
            has_sub,
            "User dengan subscription Suspended harus DIBLOKIR",
        )

        # Verify permission query conditions block access
        from qalcuity.erpnext_hooks import (
            get_customer_permission_query_conditions,
            get_sales_order_permission_query_conditions,
            get_sales_invoice_permission_query_conditions,
            get_purchase_order_permission_query_conditions,
            get_purchase_invoice_permission_query_conditions,
        )

        for doctype, pqc_func in [
            ("Customer", get_customer_permission_query_conditions),
            ("Sales Order", get_sales_order_permission_query_conditions),
            ("Sales Invoice", get_sales_invoice_permission_query_conditions),
            ("Purchase Order", get_purchase_order_permission_query_conditions),
            ("Purchase Invoice", get_purchase_invoice_permission_query_conditions),
        ]:
            pqc = pqc_func(user_email, doctype)
            self.assertEqual(
                pqc, "1=0",
                f"Suspended subscription harus memblokir akses {doctype} "
                f"(query condition harus '1=0')",
            )

        # Verify has_permission also blocks access
        # Test with a mock document-like object for has_permission checks
        from qalcuity.erpnext_hooks import has_customer_permission, has_sales_order_permission

        # Create a mock document
        class MockDoc:
            def __init__(self, name, customer=None, company=None):
                self.name = name
                self.customer = customer
                self.company = company

        # Customer document check
        has_cust_perm = has_customer_permission(
            MockDoc("Test Customer", customer=self.user_suspended["customer"]),
            "read",
            user_email,
        )
        self.assertFalse(
            has_cust_perm,
            "Suspended subscription harus memblokir has_permission untuk Customer",
        )
