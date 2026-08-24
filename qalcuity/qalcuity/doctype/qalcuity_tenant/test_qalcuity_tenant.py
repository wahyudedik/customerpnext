# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from .qalcuity_tenant import QalcuityTenant


class TestQalcuityTenant(IntegrationTestCase):
    """Test cases untuk Qalcuity Tenant."""

    def setUp(self):
        """Setup test data."""
        self._create_test_customer()

    def tearDown(self):
        """Cleanup test data."""
        frappe.db.rollback()

    def _create_test_customer(self):
        """Helper untuk membuat test customer."""
        if not frappe.db.exists("Customer", "Test Customer - Tenant"):
            customer = frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": "Test Customer - Tenant",
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

    def _create_tenant(self, **kwargs):
        """Helper untuk membuat tenant."""
        defaults = {
            "customer": "Test Customer - Tenant",
            "tenant_id": "test-tenant-0001",
            "status": "Active",
        }
        defaults.update(kwargs)
        tenant = frappe.get_doc({"doctype": "Qalcuity Tenant", **defaults})
        tenant.insert(ignore_permissions=True)
        return tenant

    def test_create_tenant(self):
        """Test membuat tenant baru."""
        tenant = self._create_tenant()
        self.assertEqual(tenant.tenant_id, "test-tenant-0001")
        self.assertEqual(tenant.status, "Active")
        self.assertTrue(tenant.provisioned_on)

    def test_duplicate_tenant_id(self):
        """Test tenant_id harus unique."""
        self._create_tenant()
        with self.assertRaises(frappe.ValidationError):
            self._create_tenant(tenant_id="test-tenant-0001")

    def test_suspend_tenant(self):
        """Test suspend tenant."""
        tenant = self._create_tenant()
        tenant.suspend()
        self.assertEqual(tenant.status, "Suspended")

    def test_suspend_already_suspended(self):
        """Test suspend tenant yang sudah suspended."""
        tenant = self._create_tenant()
        tenant.suspend()
        with self.assertRaises(frappe.ValidationError):
            tenant.suspend()

    def test_reactivate_tenant(self):
        """Test reactivate tenant."""
        tenant = self._create_tenant()
        tenant.suspend()
        tenant.reactivate()
        self.assertEqual(tenant.status, "Active")

    def test_auto_generate_tenant_id(self):
        """Test auto generate tenant_id."""
        tenant = frappe.get_doc(
            {
                "doctype": "Qalcuity Tenant",
                "customer": "Test Customer - Tenant",
            }
        )
        tenant.insert(ignore_permissions=True)
        self.assertTrue(tenant.tenant_id)
        self.assertIn("test-customer-tenant", tenant.tenant_id)
