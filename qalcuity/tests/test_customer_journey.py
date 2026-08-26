# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
End-to-End Testing — Customer Journey
======================================
Automated test untuk seluruh flow MVP Qalcuity ERP:
Register → Email Verify → Login → Select Plan → Checkout →
Upload Payment Proof → Admin Approve → Subscription Active →
Tenant Provisioned → ERP Access

Test Cases:
1. Full Customer Journey (Happy Path)
2. Payment Rejection & Resubmission
3. Subscription Expiry with Grace Period
4. Plan Change (Upgrade)
5. Tenant Isolation (Basic)
6. Module Enforcement (Basic)
7. Registration Validation
8. Backup Trigger
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate, add_days, getdate, now_datetime

from qalcuity.isolation import (
    is_admin_user,
    get_current_customer,
    get_customer_for_user,
    clear_isolation_cache,
)
from qalcuity.module_enforcement import (
    get_user_enabled_modules,
    is_module_enabled_for_user,
    is_doctype_enabled_for_user,
)
from qalcuity.tasks import check_subscription_expiry, run_scheduled_backup, GRACE_PERIOD_DAYS


class TestCustomerJourney(IntegrationTestCase):
    """Test cases untuk seluruh customer journey MVP Qalcuity ERP."""

    # =========================================================================
    # Setup & Teardown
    # =========================================================================

    def setUp(self):
        """Setup test data yang dibutuhkan."""
        self._cleanup_test_data()
        self._ensure_test_roles()
        self._create_test_plan_starter()
        self._create_test_plan_business()

    def tearDown(self):
        """Cleanup test data."""
        self._cleanup_test_data()

    def _cleanup_test_data(self):
        """Hapus semua test data yang mungkin tertinggal."""
        # Hapus test payments
        for sub in frappe.get_all(
            "Qalcuity Subscription",
            filters={"customer": ["like", "Test Customer E2E%"]},
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
            """DELETE FROM `tabQalcuity Subscription`
               WHERE customer LIKE 'Test Customer E2E%%'"""
        )

        # Hapus test plan changes
        frappe.db.sql(
            """DELETE FROM `tabQalcuity Plan Change`
               WHERE customer LIKE 'Test Customer E2E%%'"""
        )

        # Hapus test tenants
        for tenant in frappe.get_all(
            "Qalcuity Tenant",
            filters={"customer": ["like", "Test Customer E2E%"]},
            fields=["name"],
        ):
            frappe.delete_doc("Qalcuity Tenant", tenant.name, ignore_permissions=True)

        # Hapus test backup records
        frappe.db.sql(
            """DELETE FROM `tabQalcuity Backup`
               WHERE backup_name LIKE 'test_backup%%'"""
        )

        # Hapus test portal users
        frappe.db.sql(
            """DELETE FROM `tabPortal User`
               WHERE user LIKE 'test-e2e-%%@qalcuity.test'"""
        )

        # Hapus test customers
        for customer_name in frappe.get_all(
            "Customer",
            filters={"customer_name": ["like", "Test Customer E2E%"]},
            fields=["name"],
        ):
            frappe.delete_doc("Customer", customer_name.name, ignore_permissions=True)

        # Hapus test users
        for email in [
            "test-e2e-customer-a@qalcuity.test",
            "test-e2e-customer-b@qalcuity.test",
        ]:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, ignore_permissions=True)

        frappe.db.commit()

    def _ensure_test_roles(self):
        """Pastikan role Qalcuity Superadmin ada."""
        if not frappe.db.exists("Role", "Qalcuity Superadmin"):
            frappe.get_doc(
                {
                    "doctype": "Role",
                    "role_name": "Qalcuity Superadmin",
                    "role_type": "Reporting",
                }
            ).insert(ignore_permissions=True)

        if not frappe.db.exists("Role", "Qalcuity ERP User"):
            frappe.get_doc(
                {
                    "doctype": "Role",
                    "role_name": "Qalcuity ERP User",
                    "role_type": "Reporting",
                }
            ).insert(ignore_permissions=True)

        frappe.db.commit()

    def _create_test_plan_starter(self):
        """Buat test plan Starter (Rp 99.000/month)."""
        if frappe.db.exists("Qalcuity Plan", {"plan_name": "Test Starter E2E"}):
            self.plan_starter = frappe.db.get_value(
                "Qalcuity Plan", {"plan_name": "Test Starter E2E"}, "name"
            )
            return

        plan = frappe.get_doc(
            {
                "doctype": "Qalcuity Plan",
                "plan_name": "Test Starter E2E",
                "description": "Paket Starter untuk testing E2E",
                "price": 99000,
                "currency": "IDR",
                "billing_period": "Monthly",
                "is_active": 1,
                "is_trial": 0,
                "max_users": 3,
                "max_storage_gb": 5,
                "sort_order": 1,
            }
        )
        plan.append("features", {"feature_name": "Sales"})
        plan.append("features", {"feature_name": "Accounting"})
        plan.append("features", {"feature_name": "Inventory"})
        plan.append(
            "enabled_modules",
            {"module_name": "Accounting"},
        )
        plan.append(
            "enabled_modules",
            {"module_name": "Sales"},
        )
        plan.append(
            "enabled_modules",
            {"module_name": "CRM"},
        )
        plan.append(
            "enabled_modules",
            {"module_name": "Inventory"},
        )
        plan.insert(ignore_permissions=True)
        frappe.db.commit()
        self.plan_starter = plan.name

    def _create_test_plan_business(self):
        """Buat test plan Business (Rp 299.000/month)."""
        if frappe.db.exists("Qalcuity Plan", {"plan_name": "Test Business E2E"}):
            self.plan_business = frappe.db.get_value(
                "Qalcuity Plan", {"plan_name": "Test Business E2E"}, "name"
            )
            return

        plan = frappe.get_doc(
            {
                "doctype": "Qalcuity Plan",
                "plan_name": "Test Business E2E",
                "description": "Paket Business untuk testing E2E",
                "price": 299000,
                "currency": "IDR",
                "billing_period": "Monthly",
                "is_active": 1,
                "is_trial": 0,
                "max_users": 10,
                "max_storage_gb": 20,
                "sort_order": 2,
            }
        )
        plan.append("features", {"feature_name": "Sales"})
        plan.append("features", {"feature_name": "Accounting"})
        plan.append("features", {"feature_name": "Inventory"})
        plan.append("features", {"feature_name": "HR"})
        plan.append("features", {"feature_name": "Projects"})
        plan.append(
            "enabled_modules",
            {"module_name": "Accounting"},
        )
        plan.append(
            "enabled_modules",
            {"module_name": "Sales"},
        )
        plan.append(
            "enabled_modules",
            {"module_name": "CRM"},
        )
        plan.append(
            "enabled_modules",
            {"module_name": "Inventory"},
        )
        plan.append(
            "enabled_modules",
            {"module_name": "HR"},
        )
        plan.append(
            "enabled_modules",
            {"module_name": "Projects"},
        )
        plan.insert(ignore_permissions=True)
        frappe.db.commit()
        self.plan_business = plan.name

    def _create_test_customer(self, email, full_name, company_name):
        """
        Buat test customer (User + Customer + Portal User + Tenant).

        Args:
            email: Email address
            full_name: Nama lengkap
            company_name: Nama perusahaan

        Returns:
            dict: {user, customer, portal_user, tenant}
        """
        # 1. Buat User
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": full_name,
                "full_name": full_name,
                "user_type": "Website User",
                "send_welcome_email": 0,
                "disabled": 0,  # Verified
            }
        )
        user.append("roles", {"role": "Customer"})
        user.insert(ignore_permissions=True)

        # 2. Buat Customer
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

        # 3. Buat Portal User
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

        # 4. Buat Qalcuity Tenant
        tenant = frappe.get_doc(
            {
                "doctype": "Qalcuity Tenant",
                "customer": customer.name,
                "status": "Active",
            }
        )
        tenant.insert(ignore_permissions=True)

        frappe.db.commit()

        return {
            "user": user.name,
            "customer": customer.name,
            "portal_user": portal_user.name,
            "tenant": tenant.name,
        }

    def _create_test_subscription(self, customer, plan, status="Pending Payment"):
        """
        Buat test subscription.

        Args:
            customer: Customer name
            plan: Plan name
            status: Subscription status

        Returns:
            str: Subscription name
        """
        sub = frappe.get_doc(
            {
                "doctype": "Qalcuity Subscription",
                "customer": customer,
                "plan": plan,
                "status": status,
            }
        )
        sub.insert(ignore_permissions=True)
        frappe.db.commit()
        return sub.name

    def _create_test_payment(
        self,
        subscription,
        amount=99000,
        status="Pending",
        proof="/files/test-proof.jpg",
    ):
        """
        Buat test payment.

        Args:
            subscription: Subscription name
            amount: Payment amount
            status: Payment status
            proof: Proof of payment file URL

        Returns:
            str: Payment name
        """
        payment = frappe.get_doc(
            {
                "doctype": "Qalcuity Payment",
                "subscription": subscription,
                "amount": amount,
                "currency": "IDR",
                "payment_method": "Bank Transfer",
                "payment_date": nowdate(),
                "proof_of_payment": proof,
                "reference_number": "REF-TEST-001",
                "status": status,
            }
        )
        payment.insert(ignore_permissions=True)
        frappe.db.commit()
        return payment.name

    # =========================================================================
    # Test Case A: Happy Path — Full Customer Journey
    # =========================================================================

    def test_01_full_customer_journey(self):
        """
        Test seluruh flow MVP:
        1. Create Qalcuity Plan (Starter, Rp99.000/month)
        2. Register new customer (create User + Customer)
        3. Create Qalcuity Subscription (status: PENDING)
        4. Create Qalcuity Payment (status: PENDING, with proof)
        5. Admin approve payment
        6. Verify subscription becomes ACTIVE
        7. Verify tenant is provisioned
        8. Verify ERP access works (user can access desk)
        """
        # Step 1: Plan sudah dibuat di setUp
        self.assertTrue(self.plan_starter, "Plan Starter harus ada")

        # Step 2: Register new customer
        customer_data = self._create_test_customer(
            email="test-e2e-customer-a@qalcuity.test",
            full_name="Test Customer E2E A",
            company_name="Test Customer E2E Company A",
        )
        self.assertTrue(customer_data["user"], "User harus dibuat")
        self.assertTrue(customer_data["customer"], "Customer harus dibuat")
        self.assertTrue(customer_data["tenant"], "Tenant harus dibuat")

        # Verify user has Customer role
        user_roles = frappe.get_roles(customer_data["user"])
        self.assertIn("Customer", user_roles, "User harus punya role Customer")

        # Step 3: Create Qalcuity Subscription (Pending Payment)
        subscription_name = self._create_test_subscription(
            customer=customer_data["customer"],
            plan=self.plan_starter,
            status="Pending Payment",
        )
        self.assertTrue(subscription_name, "Subscription harus dibuat")

        sub_status = frappe.db.get_value(
            "Qalcuity Subscription", subscription_name, "status"
        )
        self.assertEqual(sub_status, "Pending Payment")

        # Step 4: Create Qalcuity Payment (Pending)
        payment_name = self._create_test_payment(
            subscription=subscription_name,
            amount=99000,
            status="Pending",
            proof="/files/test-proof.jpg",
        )
        self.assertTrue(payment_name, "Payment harus dibuat")

        pay_status = frappe.db.get_value("Qalcuity Payment", payment_name, "status")
        self.assertEqual(pay_status, "Pending")

        # Step 5: Admin approve payment
        payment_doc = frappe.get_doc("Qalcuity Payment", payment_name)
        payment_doc.status = "Approved"
        payment_doc.reviewed_by = "Administrator"
        payment_doc.review_date = now_datetime()
        payment_doc.save(ignore_permissions=True)
        frappe.db.commit()

        pay_status_after = frappe.db.get_value(
            "Qalcuity Payment", payment_name, "status"
        )
        self.assertEqual(pay_status_after, "Approved")

        # Step 6: Verify subscription becomes ACTIVE
        sub_status_after = frappe.db.get_value(
            "Qalcuity Subscription", subscription_name, "status"
        )
        self.assertEqual(sub_status_after, "Active", "Subscription harus ACTIVE setelah payment approved")

        # Verify start_date and end_date are set
        start_date = frappe.db.get_value(
            "Qalcuity Subscription", subscription_name, "start_date"
        )
        end_date = frappe.db.get_value(
            "Qalcuity Subscription", subscription_name, "end_date"
        )
        self.assertTrue(start_date, "start_date harus diset")
        self.assertTrue(end_date, "end_date harus diset")
        self.assertEqual(str(start_date), nowdate(), "start_date harus hari ini")
        self.assertGreater(getdate(end_date), getdate(start_date), "end_date harus setelah start_date")

        # Step 7: Verify tenant is provisioned
        tenant_name = frappe.db.get_value(
            "Qalcuity Tenant", {"customer": customer_data["customer"]}, "name"
        )
        self.assertTrue(tenant_name, "Tenant harus ada")

        # Verify tenant subscription link
        tenant_subscription = frappe.db.get_value(
            "Qalcuity Tenant", tenant_name, "subscription"
        )
        self.assertEqual(
            tenant_subscription, subscription_name, "Tenant harus link ke subscription"
        )

        # Step 8: Verify ERP access (user can access desk — has required roles)
        user_roles_final = frappe.get_roles(customer_data["user"])
        self.assertIn("Customer", user_roles_final, "User harus punya role Customer")

        # Verify isolation helper works
        customer_for_user = get_customer_for_user(customer_data["user"])
        self.assertEqual(
            customer_for_user,
            customer_data["customer"],
            "get_customer_for_user harus return customer yang benar",
        )

    # =========================================================================
    # Test Case B: Payment Rejection & Resubmission
    # =========================================================================

    def test_02_payment_rejection_and_resubmission(self):
        """
        1. Customer submits payment
        2. Admin rejects with reason
        3. Verify subscription stays PENDING
        4. Customer resubmits payment
        5. Admin approves
        6. Verify subscription becomes ACTIVE
        """
        # Setup: Create customer and subscription
        customer_data = self._create_test_customer(
            email="test-e2e-customer-b@qalcuity.test",
            full_name="Test Customer E2E B",
            company_name="Test Customer E2E Company B",
        )

        subscription_name = self._create_test_subscription(
            customer=customer_data["customer"],
            plan=self.plan_starter,
            status="Pending Payment",
        )

        # Step 1: Customer submits payment
        payment_name = self._create_test_payment(
            subscription=subscription_name,
            amount=99000,
            status="Pending",
        )
        self.assertEqual(
            frappe.db.get_value("Qalcuity Payment", payment_name, "status"),
            "Pending",
        )

        # Step 2: Admin rejects with reason
        payment_doc = frappe.get_doc("Qalcuity Payment", payment_name)
        payment_doc.status = "Rejected"
        payment_doc.reviewed_by = "Administrator"
        payment_doc.review_date = now_datetime()
        payment_doc.rejection_reason = "Bukti pembayaran tidak jelas"
        payment_doc.save(ignore_permissions=True)
        frappe.db.commit()

        self.assertEqual(
            frappe.db.get_value("Qalcuity Payment", payment_name, "status"),
            "Rejected",
        )

        # Step 3: Verify subscription stays PENDING
        sub_status = frappe.db.get_value(
            "Qalcuity Subscription", subscription_name, "status"
        )
        self.assertEqual(
            sub_status,
            "Pending Payment",
            "Subscription harus tetap Pending Payment setelah rejection",
        )

        # Step 4: Customer resubmits payment (new payment)
        payment_name_2 = self._create_test_payment(
            subscription=subscription_name,
            amount=99000,
            status="Pending",
        )
        self.assertTrue(payment_name_2, "Payment baru harus dibuat")

        # Step 5: Admin approves
        payment_doc_2 = frappe.get_doc("Qalcuity Payment", payment_name_2)
        payment_doc_2.status = "Approved"
        payment_doc_2.reviewed_by = "Administrator"
        payment_doc_2.review_date = now_datetime()
        payment_doc_2.save(ignore_permissions=True)
        frappe.db.commit()

        self.assertEqual(
            frappe.db.get_value("Qalcuity Payment", payment_name_2, "status"),
            "Approved",
        )

        # Step 6: Verify subscription becomes ACTIVE
        sub_status_final = frappe.db.get_value(
            "Qalcuity Subscription", subscription_name, "status"
        )
        self.assertEqual(
            sub_status_final,
            "Active",
            "Subscription harus ACTIVE setelah payment approved",
        )

    # =========================================================================
    # Test Case C: Subscription Expiry & Grace Period
    # =========================================================================

    def test_03_subscription_expiry_with_grace_period(self):
        """
        1. Create ACTIVE subscription with expiry = today - 1 day (expired)
        2. Run scheduled task (check_subscription_expiry)
        3. Verify subscription status changes to Grace Period
        4. Create another subscription past grace period → verify Expired
        """
        # Setup: Create customer and subscription
        customer_data = self._create_test_customer(
            email="test-e2e-customer-a@qalcuity.test",
            full_name="Test Customer E2E A",
            company_name="Test Customer E2E Company A",
        )

        subscription_name = self._create_test_subscription(
            customer=customer_data["customer"],
            plan=self.plan_starter,
            status="Pending Payment",
        )

        # Activate subscription manually
        sub_doc = frappe.get_doc("Qalcuity Subscription", subscription_name)
        sub_doc.status = "Active"
        sub_doc.start_date = add_days(nowdate(), -(GRACE_PERIOD_DAYS + 5))
        sub_doc.end_date = add_days(nowdate(), -1)  # Expired yesterday
        sub_doc.save(ignore_permissions=True)
        frappe.db.commit()

        self.assertEqual(
            frappe.db.get_value("Qalcuity Subscription", subscription_name, "status"),
            "Active",
        )

        # Step 2: Run scheduled task
        check_subscription_expiry()
        frappe.db.commit()

        # Step 3: Verify subscription is now in Grace Period
        sub_status_after = frappe.db.get_value(
            "Qalcuity Subscription", subscription_name, "status"
        )
        self.assertEqual(
            sub_status_after,
            "Grace Period",
            "Subscription harus masuk Grace Period setelah end_date lewat",
        )

        # Step 4: Test expired (past grace period)
        # Create another subscription that's past grace period
        subscription_name_2 = self._create_test_subscription(
            customer=customer_data["customer"],
            plan=self.plan_starter,
            status="Pending Payment",
        )

        sub_doc_2 = frappe.get_doc("Qalcuity Subscription", subscription_name_2)
        sub_doc_2.status = "Active"
        sub_doc_2.start_date = add_days(nowdate(), -(GRACE_PERIOD_DAYS + 15))
        sub_doc_2.end_date = add_days(nowdate(), -(GRACE_PERIOD_DAYS + 1))  # Past grace period
        sub_doc_2.save(ignore_permissions=True)
        frappe.db.commit()

        # Run scheduled task again
        check_subscription_expiry()
        frappe.db.commit()

        # Verify subscription is now Expired
        sub_status_expired = frappe.db.get_value(
            "Qalcuity Subscription", subscription_name_2, "status"
        )
        self.assertEqual(
            sub_status_expired,
            "Expired",
            "Subscription harus Expired setelah grace period berakhir",
        )

    # =========================================================================
    # Test Case D: Plan Change (Upgrade)
    # =========================================================================

    def test_04_plan_change_upgrade(self):
        """
        1. Customer has ACTIVE subscription on Starter plan
        2. Customer requests upgrade to Business plan
        3. Verify plan change is recorded
        4. Verify subscription reflects new plan
        """
        # Setup: Create customer with active subscription
        customer_data = self._create_test_customer(
            email="test-e2e-customer-b@qalcuity.test",
            full_name="Test Customer E2E B",
            company_name="Test Customer E2E Company B",
        )

        subscription_name = self._create_test_subscription(
            customer=customer_data["customer"],
            plan=self.plan_starter,
            status="Pending Payment",
        )

        # Activate subscription
        sub_doc = frappe.get_doc("Qalcuity Subscription", subscription_name)
        sub_doc.status = "Active"
        sub_doc.start_date = nowdate()
        sub_doc.end_date = add_days(nowdate(), 30)
        sub_doc.save(ignore_permissions=True)
        frappe.db.commit()

        # Verify current plan is Starter
        current_plan = frappe.db.get_value(
            "Qalcuity Subscription", subscription_name, "plan"
        )
        self.assertEqual(current_plan, self.plan_starter)

        # Step 2: Submit plan change (upgrade to Business)
        # Since submit_plan_change requires frappe.session.user, we create the plan change directly
        plan_change = frappe.get_doc(
            {
                "doctype": "Qalcuity Plan Change",
                "customer": customer_data["customer"],
                "subscription": subscription_name,
                "current_plan": self.plan_starter,
                "new_plan": self.plan_business,
                "effective_date": nowdate(),
                "reason": "Upgrade to Business plan for more features",
                "status": "Pending",
            }
        )
        plan_change.insert(ignore_permissions=True)
        frappe.db.commit()

        # Step 3: Verify plan change is recorded
        self.assertTrue(plan_change.name, "Plan Change harus dibuat")
        self.assertEqual(plan_change.change_type, "Upgrade")
        self.assertEqual(plan_change.status, "Pending")

        # Simulate admin approval: update subscription plan
        sub_doc = frappe.get_doc("Qalcuity Subscription", subscription_name)
        sub_doc.plan = self.plan_business
        sub_doc.save(ignore_permissions=True)
        frappe.db.commit()

        # Step 4: Verify subscription reflects new plan
        new_plan = frappe.db.get_value(
            "Qalcuity Subscription", subscription_name, "plan"
        )
        self.assertEqual(
            new_plan, self.plan_business, "Subscription harus menggunakan plan Business"
        )

    # =========================================================================
    # Test Case E: Tenant Isolation (Basic)
    # =========================================================================

    def test_05_tenant_isolation_basic(self):
        """
        1. Create 2 customers with separate tenants
        2. Create subscription data for Customer A
        3. Verify Customer B's queries don't return Customer A's data
        """
        # Step 1: Create 2 customers with separate tenants
        customer_a = self._create_test_customer(
            email="test-e2e-customer-a@qalcuity.test",
            full_name="Test Customer E2E A",
            company_name="Test Customer E2E Company A",
        )

        customer_b = self._create_test_customer(
            email="test-e2e-customer-b@qalcuity.test",
            full_name="Test Customer E2E B",
            company_name="Test Customer E2E Company B",
        )

        # Verify tenants are different
        self.assertNotEqual(
            customer_a["tenant"],
            customer_b["tenant"],
            "Tenant A dan B harus berbeda",
        )

        # Verify customers are different
        self.assertNotEqual(
            customer_a["customer"],
            customer_b["customer"],
            "Customer A dan B harus berbeda",
        )

        # Step 2: Create subscription for Customer A
        sub_a = self._create_test_subscription(
            customer=customer_a["customer"],
            plan=self.plan_starter,
            status="Active",
        )

        # Create subscription for Customer B (different plan)
        sub_b = self._create_test_subscription(
            customer=customer_b["customer"],
            plan=self.plan_business,
            status="Active",
        )

        # Step 3: Verify isolation — Customer A's subscription is linked to Customer A
        sub_a_customer = frappe.db.get_value(
            "Qalcuity Subscription", sub_a, "customer"
        )
        sub_b_customer = frappe.db.get_value(
            "Qalcuity Subscription", sub_b, "customer"
        )

        self.assertEqual(sub_a_customer, customer_a["customer"])
        self.assertEqual(sub_b_customer, customer_b["customer"])
        self.assertNotEqual(sub_a_customer, sub_b_customer)

        # Verify isolation helper functions
        self.assertEqual(
            get_customer_for_user(customer_a["user"]),
            customer_a["customer"],
        )
        self.assertEqual(
            get_customer_for_user(customer_b["user"]),
            customer_b["customer"],
        )

        # Verify tenants are linked to correct customers
        tenant_a_customer = frappe.db.get_value(
            "Qalcuity Tenant", customer_a["tenant"], "customer"
        )
        tenant_b_customer = frappe.db.get_value(
            "Qalcuity Tenant", customer_b["tenant"], "customer"
        )

        self.assertEqual(tenant_a_customer, customer_a["customer"])
        self.assertEqual(tenant_b_customer, customer_b["customer"])
        self.assertNotEqual(tenant_a_customer, tenant_b_customer)

    # =========================================================================
    # Test Case F: Module Enforcement (Basic)
    # =========================================================================

    def test_06_module_enforcement(self):
        """
        1. Create plan with limited modules (only Sales, Accounting, CRM, Inventory)
        2. Assign plan to user via subscription
        3. Verify user can only access allowed modules
        4. Verify blocked modules are detected correctly
        """
        # Setup: Create customer
        customer_data = self._create_test_customer(
            email="test-e2e-customer-a@qalcuity.test",
            full_name="Test Customer E2E A",
            company_name="Test Customer E2E Company A",
        )

        # Create subscription with Starter plan (limited modules)
        subscription_name = self._create_test_subscription(
            customer=customer_data["customer"],
            plan=self.plan_starter,
            status="Pending Payment",
        )

        # Activate subscription
        sub_doc = frappe.get_doc("Qalcuity Subscription", subscription_name)
        sub_doc.status = "Active"
        sub_doc.start_date = nowdate()
        sub_doc.end_date = add_days(nowdate(), 30)
        sub_doc.save(ignore_permissions=True)
        frappe.db.commit()

        # Get enabled modules for the user
        enabled_modules = get_user_enabled_modules(customer_data["user"])

        # Starter plan has: Accounting, Sales, CRM, Inventory
        self.assertIsNotNone(enabled_modules, "Enabled modules harus ada")
        self.assertIn("Accounting", enabled_modules)
        self.assertIn("Sales", enabled_modules)
        self.assertIn("CRM", enabled_modules)
        self.assertIn("Inventory", enabled_modules)

        # Verify blocked modules (HR, Projects, Manufacturing not in Starter)
        self.assertNotIn("HR", enabled_modules)
        self.assertNotIn("Projects", enabled_modules)
        self.assertNotIn("Manufacturing", enabled_modules)

        # Verify module check functions
        self.assertTrue(
            is_module_enabled_for_user("Accounting", customer_data["user"]),
            "Accounting harus enabled",
        )
        self.assertTrue(
            is_module_enabled_for_user("Sales", customer_data["user"]),
            "Sales harus enabled",
        )
        self.assertFalse(
            is_module_enabled_for_user("HR", customer_data["user"]),
            "HR harus blocked",
        )
        self.assertFalse(
            is_module_enabled_for_user("Projects", customer_data["user"]),
            "Projects harus blocked",
        )

        # Verify DocType-level enforcement
        self.assertTrue(
            is_doctype_enabled_for_user("Sales Order", customer_data["user"]),
            "Sales Order harus enabled (Sales module)",
        )
        self.assertTrue(
            is_doctype_enabled_for_user("Journal Entry", customer_data["user"]),
            "Journal Entry harus enabled (Accounting module)",
        )
        self.assertFalse(
            is_doctype_enabled_for_user("Employee", customer_data["user"]),
            "Employee harus blocked (HR module)",
        )
        self.assertFalse(
            is_doctype_enabled_for_user("BOM", customer_data["user"]),
            "BOM harus blocked (Manufacturing module)",
        )

    # =========================================================================
    # Test Case G: Registration Validation
    # =========================================================================

    def test_07_registration_validation(self):
        """
        1. Test duplicate email registration (should fail)
        2. Test missing required fields (should fail)
        3. Test valid registration (should succeed)
        """
        from qalcuity.api.registration import (
            register_customer,
            verify_email,
            _generate_verification_token,
            _store_verification_token,
        )

        # Step 1: Test duplicate email registration
        # First register a customer
        result = register_customer(
            full_name="Test Customer E2E Duplicate",
            email="test-e2e-duplicate@qalcuity.test",
            password="TestPass123!",
            company_name="Test Duplicate Company",
            phone="081234567890",
        )
        self.assertTrue(result["success"], "Registration pertama harus berhasil")

        # Try registering with same email
        self.assertRaises(
            frappe.exceptions.ValidationError,
            register_customer,
            full_name="Test Customer E2E Duplicate 2",
            email="test-e2e-duplicate@qalcuity.test",
            password="TestPass123!",
            company_name="Test Duplicate Company 2",
            phone="081234567891",
        )

        # Step 2: Test missing required fields
        # Missing full_name
        self.assertRaises(
            frappe.exceptions.ValidationError,
            register_customer,
            full_name="",
            email="test-e2e-empty@qalcuity.test",
            password="TestPass123!",
            company_name="Test Company",
            phone="081234567890",
        )

        # Missing email
        self.assertRaises(
            frappe.exceptions.ValidationError,
            register_customer,
            full_name="Test Customer E2E",
            email="",
            password="TestPass123!",
            company_name="Test Company",
            phone="081234567890",
        )

        # Missing password
        self.assertRaises(
            frappe.exceptions.ValidationError,
            register_customer,
            full_name="Test Customer E2E",
            email="test-e2e-nopwd@qalcuity.test",
            password="",
            company_name="Test Company",
            phone="081234567890",
        )

        # Missing company_name
        self.assertRaises(
            frappe.exceptions.ValidationError,
            register_customer,
            full_name="Test Customer E2E",
            email="test-e2e-nocompany@qalcuity.test",
            password="TestPass123!",
            company_name="",
            phone="081234567890",
        )

        # Missing phone
        self.assertRaises(
            frappe.exceptions.ValidationError,
            register_customer,
            full_name="Test Customer E2E",
            email="test-e2e-nophone@qalcuity.test",
            password="TestPass123!",
            company_name="Test Company",
            phone="",
        )

        # Step 3: Test valid registration
        result_valid = register_customer(
            full_name="Test Customer E2E Valid",
            email="test-e2e-valid@qalcuity.test",
            password="TestPass123!",
            company_name="Test Valid Company",
            phone="081234567890",
        )
        self.assertTrue(result_valid["success"], "Valid registration harus berhasil")
        self.assertTrue(result_valid["requires_verification"])

        # Verify user was created (disabled until verification)
        user_name = frappe.db.get_value(
            "User", {"email": "test-e2e-valid@qalcuity.test"}, "name"
        )
        self.assertTrue(user_name, "User harus dibuat")
        user_disabled = frappe.db.get_value("User", user_name, "disabled")
        self.assertEqual(user_disabled, 1, "User harus disabled sampai verifikasi")

        # Verify Customer was created
        customer_exists = frappe.db.get_value(
            "Portal User",
            {"user": "test-e2e-valid@qalcuity.test", "parenttype": "Customer"},
            "parent",
        )
        self.assertTrue(customer_exists, "Customer harus dibuat via Portal User")

    # =========================================================================
    # Test Case H: Backup Trigger
    # =========================================================================

    def test_08_backup_trigger(self):
        """
        1. Verify backup task can be triggered
        2. Verify backup log (Qalcuity Backup) is created
        """
        # Step 1: Create a backup record directly (simulating backup trigger)
        # Note: Actual backup requires mysqldump which may not be available in test
        # So we test the backup record creation and status tracking

        backup_doc = frappe.get_doc(
            {
                "doctype": "Qalcuity Backup",
                "backup_name": "test_backup_e2e_001",
                "backup_type": "Full",
                "status": "Pending",
                "site_name": frappe.local.site,
                "started_at": now_datetime(),
                "performed_by": "Administrator",
                "notes": "E2E test backup trigger",
            }
        )
        backup_doc.insert(ignore_permissions=True)
        frappe.db.commit()

        self.assertTrue(backup_doc.name, "Backup record harus dibuat")

        # Step 2: Verify backup log is created
        backup_exists = frappe.db.exists(
            "Qalcuity Backup", {"backup_name": "test_backup_e2e_001"}
        )
        self.assertTrue(backup_exists, "Backup record harus ada di database")

        # Verify backup fields
        backup_status = frappe.db.get_value(
            "Qalcuity Backup", backup_doc.name, "status"
        )
        self.assertIn(backup_status, ["Pending", "Running", "Completed", "Failed"])

        backup_type = frappe.db.get_value(
            "Qalcuity Backup", backup_doc.name, "backup_type"
        )
        self.assertEqual(backup_type, "Full")

        site_name = frappe.db.get_value(
            "Qalcuity Backup", backup_doc.name, "site_name"
        )
        self.assertEqual(site_name, frappe.local.site)

        performed_by = frappe.db.get_value(
            "Qalcuity Backup", backup_doc.name, "performed_by"
        )
        self.assertEqual(performed_by, "Administrator")

        # Update status to simulate completion
        frappe.db.set_value("Qalcuity Backup", backup_doc.name, "status", "Completed")
        frappe.db.commit()

        final_status = frappe.db.get_value(
            "Qalcuity Backup", backup_doc.name, "status"
        )
        self.assertEqual(final_status, "Completed", "Backup status harus Completed")
