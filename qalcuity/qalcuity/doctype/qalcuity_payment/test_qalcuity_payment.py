# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from .qalcuity_payment import QalcuityPayment


class TestQalcuityPayment(IntegrationTestCase):
    """Test cases untuk Qalcuity Payment."""

    def setUp(self):
        """Setup test data."""
        self._create_test_plan()
        self._create_test_customer()

    def tearDown(self):
        """Cleanup test data."""
        frappe.db.rollback()

    def _create_test_plan(self):
        """Helper untuk membuat test plan."""
        if not frappe.db.exists("Qalcuity Plan", "Test Plan - Pay"):
            plan = frappe.get_doc(
                {
                    "doctype": "Qalcuity Plan",
                    "plan_name": "Test Plan - Pay",
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
        if not frappe.db.exists("Customer", "Test Customer - Pay"):
            customer = frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": "Test Customer - Pay",
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

    def _create_subscription(self):
        """Helper untuk membuat subscription."""
        sub = frappe.get_doc(
            {
                "doctype": "Qalcuity Subscription",
                "customer": "Test Customer - Pay",
                "plan": "Test Plan - Pay",
                "status": "Pending Payment",
                "start_date": frappe.utils.nowdate(),
            }
        )
        sub.insert(ignore_permissions=True)
        return sub

    def _create_payment(self, **kwargs):
        """Helper untuk membuat payment."""
        sub = self._create_subscription()
        defaults = {
            "subscription": sub.name,
            "amount": 100000,
            "currency": "IDR",
            "payment_method": "Bank Transfer",
            "payment_date": frappe.utils.nowdate(),
            "proof_of_payment": "https://example.com/proof.jpg",
            "status": "Pending",
        }
        defaults.update(kwargs)
        payment = frappe.get_doc({"doctype": "Qalcuity Payment", **defaults})
        payment.insert(ignore_permissions=True)
        return payment

    def test_create_payment(self):
        """Test membuat payment baru."""
        payment = self._create_payment()
        self.assertEqual(payment.status, "Pending")
        self.assertEqual(payment.amount, 100000)

    def test_payment_requires_proof(self):
        """Test payment memerlukan bukti."""
        with self.assertRaises(frappe.ValidationError):
            self._create_payment(proof_of_payment="")

    def test_approve_payment(self):
        """Test approve payment."""
        payment = self._create_payment()
        payment.approve()
        self.assertEqual(payment.status, "Approved")
        self.assertEqual(payment.reviewed_by, frappe.session.user)

    def test_reject_payment(self):
        """Test reject payment."""
        payment = self._create_payment()
        payment.reject(reason="Invalid proof")
        self.assertEqual(payment.status, "Rejected")
        self.assertEqual(payment.rejection_reason, "Invalid proof")

    def test_reject_requires_reason(self):
        """Test reject memerlukan alasan."""
        payment = self._create_payment()
        with self.assertRaises(frappe.ValidationError):
            payment.reject()

    def test_invalid_status_transition(self):
        """Test transisi status tidak valid."""
        payment = self._create_payment()
        payment.approve()
        with self.assertRaises(frappe.ValidationError):
            payment.status = "Pending"
            payment.save()
