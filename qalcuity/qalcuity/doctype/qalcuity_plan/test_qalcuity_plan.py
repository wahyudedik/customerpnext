# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from .qalcuity_plan import QalcuityPlan


class TestQalcuityPlan(IntegrationTestCase):
    """Test cases untuk Qalcuity Plan."""

    def setUp(self):
        """Setup test data."""
        self.plan_name = "Test Plan - Unit"

    def tearDown(self):
        """Cleanup test data."""
        frappe.db.rollback()

    def _create_plan(self, **kwargs):
        """Helper untuk membuat plan."""
        defaults = {
            "plan_name": self.plan_name,
            "price": 100000,
            "currency": "IDR",
            "billing_period": "Monthly",
            "max_users": 5,
            "max_storage_gb": 10,
            "is_active": 1,
        }
        defaults.update(kwargs)
        plan = frappe.get_doc({"doctype": "Qalcuity Plan", **defaults})
        plan.insert(ignore_permissions=True)
        return plan

    def test_create_plan(self):
        """Test membuat plan baru."""
        plan = self._create_plan()
        self.assertEqual(plan.plan_name, self.plan_name)
        self.assertEqual(plan.price, 100000)
        self.assertTrue(plan.is_active)

    def test_plan_unique_name(self):
        """Test plan name harus unique."""
        self._create_plan()
        with self.assertRaises(frappe.exceptions.DuplicateEntryError):
            self._create_plan()

    def test_plan_negative_price(self):
        """Test price tidak boleh negatif."""
        with self.assertRaises(frappe.ValidationError):
            self._create_plan(price=-1000)

    def test_plan_zero_users(self):
        """Test max_users harus > 0."""
        with self.assertRaises(frappe.ValidationError):
            self._create_plan(max_users=0)

    def test_plan_features(self):
        """Test plan dengan features."""
        plan = self._create_plan()
        plan.append("features", {"feature_name": "Accounting"})
        plan.append("features", {"feature_name": "Inventory"})
        plan.save()
        self.assertEqual(len(plan.features), 2)

    def test_plan_duplicate_features(self):
        """Test duplicate feature names."""
        plan = self._create_plan()
        plan.append("features", {"feature_name": "Accounting"})
        plan.append("features", {"feature_name": "Accounting"})
        with self.assertRaises(frappe.ValidationError):
            plan.save()
