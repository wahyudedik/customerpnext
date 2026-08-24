# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from .qalcuity_subscription import QalcuitySubscription


class TestQalcuitySubscription(IntegrationTestCase):
    """Test cases untuk Qalcuity Subscription."""

    def setUp(self):
        """Setup test data."""
        self._create_test_plan()
        self._create_test_customer()

    def tearDown(self):
        """Cleanup test data."""
        frappe.db.rollback()

    def _create_test_plan(self):
        """Helper untuk membuat test plan."""
        if not frappe.db.exists("Qalcuity Plan", "Test Plan - Sub"):
            plan = frappe.get_doc(
                {
                    "doctype": "Qalcuity Plan",
                    "plan_name": "Test Plan - Sub",
                    "price": 100000,
                    "currency": "IDR",
                    "billing_period": "Monthly",
                    "max_users": 5,
                    "max_storage_gb": 10,
                    "is_active": 1,
                }
            )
            plan.insert(ignore_permissions=True)

    def _create_test_customer(self):
        """Helper untuk membuat test customer."""
        if not frappe.db.exists("Customer", "Test Customer - Sub"):
            customer = frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": "Test Customer - Sub",
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

    def _create_subscription(self, **kwargs):
        """Helper untuk membuat subscription."""
        defaults = {
            "customer": "Test Customer - Sub",
            "plan": "Test Plan - Sub",
            "status": "Draft",
        }
        defaults.update(kwargs)
        sub = frappe.get_doc({"doctype": "Qalcuity Subscription", **defaults})
        sub.insert(ignore_permissions=True)
        return sub

    def test_create_subscription(self):
        """Test membuat subscription baru."""
        sub = self._create_subscription()
        self.assertEqual(sub.customer, "Test Customer - Sub")
        self.assertEqual(sub.plan, "Test Plan - Sub")
        self.assertEqual(sub.status, "Draft")

    def test_trial_subscription(self):
        """Test subscription trial."""
        sub = self._create_subscription(is_trial=1)
        self.assertEqual(sub.status, "Active")
        self.assertTrue(sub.start_date)
        self.assertTrue(sub.end_date)

    def test_status_transition_draft_to_pending(self):
        """Test transisi Draft ke Pending Payment."""
        sub = self._create_subscription()
        sub.status = "Pending Payment"
        sub.save()
        self.assertEqual(sub.status, "Pending Payment")

    def test_invalid_status_transition(self):
        """Test transisi status yang tidak valid."""
        sub = self._create_subscription()
        with self.assertRaises(frappe.ValidationError):
            sub.status = "Active"  # Langsung ke Active tanpa Pending Payment
            sub.save()

    def test_plan_must_be_active(self):
        """Test plan harus aktif."""
        # Deactivate plan
        frappe.db.set_value("Qalcuity Plan", "Test Plan - Sub", "is_active", 0)
        with self.assertRaises(frappe.ValidationError):
            self._create_subscription()
