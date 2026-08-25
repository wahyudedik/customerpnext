# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestQalcuityProvisioningLog(IntegrationTestCase):
    """Test cases untuk Qalcuity Provisioning Log."""

    def setUp(self):
        """Setup test data."""
        pass

    def tearDown(self):
        """Cleanup test data."""
        frappe.db.rollback()
