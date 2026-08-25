# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity ERP Provisioning Module
=================================
Handles ERP environment setup for tenants when subscription becomes ACTIVE.
Creates Company, assigns roles, configures workspace access.

Architecture:
- Single-site multi-tenant: all customers share qalcuity.com Frappe site
- Each tenant gets their own ERPNext Company for data isolation
- Row-level isolation via permission hooks + Company-level scoping
"""

import json
import frappe
from frappe import _
from frappe.utils import now_datetime, cint


# =============================================================================
# Constants
# =============================================================================

ERP_USER_ROLE = "Qalcuity ERP User"
EMPLOYEE_ROLE = "Employee"
PROVISIONING_STATUS_NOT_STARTED = "Not Started"
PROVISIONING_STATUS_IN_PROGRESS = "In Progress"
PROVISIONING_STATUS_COMPLETED = "Completed"
PROVISIONING_STATUS_FAILED = "Failed"
PROVISIONING_STATUS_SUSPENDED = "Suspended"


# =============================================================================
# Main Provisioning Entry Point
# =============================================================================

def provision_tenant(tenant_name):
    """
    Main provisioning entry point.
    Creates Company, assigns roles, configures workspace.
    Returns dict with status and details.

    Args:
        tenant_name: Name of the Qalcuity Tenant document

    Returns:
        dict: {"status": "success"|"failed", "company": ..., "details": ...}
    """
    log_entry = None
    try:
        # Set provisioning status to In Progress
        _update_provisioning_status(tenant_name, PROVISIONING_STATUS_IN_PROGRESS)

        # Get tenant document
        tenant = frappe.get_doc("Qalcuity Tenant", tenant_name)

        # Validate prerequisites
        _validate_prerequisites(tenant)

        result = {
            "status": "success",
            "company": None,
            "users_modified": 0,
            "details": [],
        }

        # Step 1: Create Company (if not exists)
        company_name = tenant.erp_company
        if not company_name:
            company_name = create_company_for_tenant(tenant)
            result["company"] = company_name
            result["details"].append("Company created: {0}".format(company_name))
        else:
            result["company"] = company_name
            result["details"].append("Company already exists: {0}".format(company_name))

        # Step 2: Assign ERP roles to all portal users
        users_modified = assign_erp_roles(tenant.customer, company_name)
        result["users_modified"] = users_modified
        result["details"].append(
            "Roles assigned to {0} user(s)".format(users_modified)
        )

        # Step 3: Update tenant record
        frappe.db.set_value(
            "Qalcuity Tenant",
            tenant_name,
            {
                "erp_provisioning_status": PROVISIONING_STATUS_COMPLETED,
                "erp_company": company_name,
                "provisioning_error": "",
                "last_provisioning_attempt": now_datetime(),
            },
        )
        frappe.db.commit()

        result["details"].append("Provisioning completed successfully")

        # Create provisioning log
        _create_provisioning_log(
            tenant=tenant_name,
            customer=tenant.customer,
            action="Provision",
            status="Success",
            details=json.dumps(result),
            company_created=company_name,
            users_modified=users_modified,
        )

        frappe.logger().info(
            "Qalcuity: Tenant {0} provisioned successfully. Company: {1}".format(
                tenant_name, company_name
            )
        )

        return result

    except Exception as e:
        error_msg = str(e)
        frappe.log_error(
            "Qalcuity Provisioning Error for {0}: {1}".format(tenant_name, error_msg),
            "Qalcuity Provisioning",
        )

        # Update tenant with error
        try:
            frappe.db.set_value(
                "Qalcuity Tenant",
                tenant_name,
                {
                    "erp_provisioning_status": PROVISIONING_STATUS_FAILED,
                    "provisioning_error": error_msg,
                    "last_provisioning_attempt": now_datetime(),
                },
            )
            frappe.db.commit()
        except Exception:
            pass

        # Create provisioning log with failure
        try:
            customer = frappe.db.get_value(
                "Qalcuity Tenant", tenant_name, "customer"
            )
            _create_provisioning_log(
                tenant=tenant_name,
                customer=customer,
                action="Provision",
                status="Failed",
                details="",
                error_message=error_msg,
            )
        except Exception:
            pass

        return {"status": "failed", "error": error_msg}


# =============================================================================
# Company Creation
# =============================================================================

def create_company_for_tenant(tenant):
    """
    Create an ERPNext Company for the tenant.
    Company name: "{customer_name} ({tenant_id})"

    Args:
        tenant: Qalcuity Tenant document

    Returns:
        str: Company name (document name)
    """
    # Get customer name
    customer_name = frappe.db.get_value("Customer", tenant.customer, "customer_name")
    if not customer_name:
        frappe.throw(
            _("Customer {0} not found.").format(tenant.customer)
        )

    # Generate company name: "{customer_name} ({tenant_id})"
    company_name = "{0} ({1})".format(customer_name, tenant.tenant_id)

    # Check if company already exists
    if frappe.db.exists("Company", company_name):
        frappe.logger().info(
            "Qalcuity: Company '{0}' already exists, skipping creation".format(
                company_name
            )
        )
        return company_name

    # Generate abbreviation (first 3 chars of each word, max 6 chars)
    abbr = _generate_company_abbr(company_name)

    # Get settings for defaults
    settings = frappe.get_single("Qalcuity Settings") if frappe.db.exists("Qalcuity Settings", "Qalcuity Settings") else None
    default_currency = "IDR"
    country = "Indonesia"

    # Create Company document
    company = frappe.get_doc(
        {
            "doctype": "Company",
            "company_name": company_name,
            "abbr": abbr,
            "default_currency": default_currency,
            "country": country,
            "domain": "Manufacturing",  # Covers all modules
        }
    )

    # Use ignore_permissions since provisioning runs as system
    company.insert(ignore_permissions=True)

    frappe.logger().info(
        "Qalcuity: Company '{0}' created with abbr '{1}'".format(
            company_name, abbr
        )
    )

    return company.name


def _generate_company_abbr(company_name):
    """
    Generate a short abbreviation from company name.
    Takes first letter of each word, max 6 characters.

    Args:
        company_name: Full company name

    Returns:
        str: Abbreviation (e.g., "PMJT21" for "PT Maju Jaya (TENANT-20260825-0001)")
    """
    import re

    # Remove special characters but keep alphanumeric and spaces
    clean_name = re.sub(r"[^a-zA-Z0-9\s]", "", company_name)

    # Take first letter of each word
    words = clean_name.split()
    abbr = "".join(word[0].upper() for word in words if word)

    # Append last 2 digits of date if from tenant_id pattern
    # Keep it max 6 chars
    if len(abbr) > 6:
        abbr = abbr[:6]

    # Ensure minimum length
    if len(abbr) < 2:
        abbr = abbr + "CO"

    # Check for uniqueness and append number if needed
    original_abbr = abbr
    counter = 1
    while frappe.db.exists("Company", {"abbr": abbr}):
        abbr = original_abbr[:4] + str(counter)
        counter += 1
        if counter > 99:
            break

    return abbr


# =============================================================================
# Role Assignment
# =============================================================================

def assign_erp_roles(customer_name, company_name=None):
    """
    Find all Portal Users linked to this Customer.
    Assign "Qalcuity ERP User" and "Employee" roles to each user.

    Args:
        customer_name: ERPNext Customer name
        company_name: Company to set as default (optional)

    Returns:
        int: Number of users modified
    """
    # Find all Portal Users linked to this Customer
    portal_users = frappe.get_all(
        "Portal User",
        filters={"parent": customer_name, "parenttype": "Customer"},
        fields=["user"],
    )

    if not portal_users:
        frappe.logger().info(
            "Qalcuity: No portal users found for customer {0}".format(customer_name)
        )
        return 0

    users_modified = 0

    for pu in portal_users:
        user_name = pu.user
        if not user_name:
            continue

        try:
            # Ensure the Qalcuity ERP User role exists
            _ensure_role_exists(ERP_USER_ROLE)

            # Add roles using frappe client
            _add_role_to_user(user_name, ERP_USER_ROLE)
            _add_role_to_user(user_name, EMPLOYEE_ROLE)

            # Set default company for the user
            if company_name:
                frappe.db.set_value("User", user_name, "default_company", company_name)

            users_modified += 1

            frappe.logger().info(
                "Qalcuity: Roles assigned to user {0} for customer {1}".format(
                    user_name, customer_name
                )
            )

        except Exception as e:
            frappe.log_error(
                "Qalcuity: Failed to assign roles to user {0}: {1}".format(
                    user_name, str(e)
                ),
                "Qalcuity Provisioning",
            )

    # Clear role cache for affected users
    _clear_role_cache([pu.user for pu in portal_users])

    return users_modified


def deprovision_tenant(tenant_name):
    """
    Remove ERP roles when subscription expires.
    Do NOT delete Company or data — only remove access.

    Args:
        tenant_name: Name of the Qalcuity Tenant document

    Returns:
        dict: {"status": "success"|"failed", "details": ...}
    """
    try:
        tenant = frappe.get_doc("Qalcuity Tenant", tenant_name)
        customer_name = tenant.customer

        result = {
            "status": "success",
            "users_modified": 0,
            "details": [],
        }

        # Find all Portal Users linked to this Customer
        portal_users = frappe.get_all(
            "Portal User",
            filters={"parent": customer_name, "parenttype": "Customer"},
            fields=["user"],
        )

        users_modified = 0
        for pu in portal_users:
            user_name = pu.user
            if not user_name:
                continue

            try:
                _remove_role_from_user(user_name, ERP_USER_ROLE)
                _remove_role_from_user(user_name, EMPLOYEE_ROLE)
                users_modified += 1
            except Exception as e:
                frappe.log_error(
                    "Qalcuity: Failed to remove roles from user {0}: {1}".format(
                        user_name, str(e)
                    ),
                    "Qalcuity Deprovisioning",
                )

        result["users_modified"] = users_modified
        result["details"].append(
            "Roles removed from {0} user(s)".format(users_modified)
        )

        # Update tenant record — keep erp_company reference (data preserved)
        frappe.db.set_value(
            "Qalcuity Tenant",
            tenant_name,
            {
                "erp_provisioning_status": PROVISIONING_STATUS_SUSPENDED,
                "provisioning_error": "",
            },
        )
        frappe.db.commit()

        # Clear role cache
        _clear_role_cache([pu.user for pu in portal_users])

        # Create provisioning log
        _create_provisioning_log(
            tenant=tenant_name,
            customer=customer_name,
            action="Deprovision",
            status="Success",
            details=json.dumps(result),
            users_modified=users_modified,
        )

        frappe.logger().info(
            "Qalcuity: Tenant {0} deprovisioned. Users: {1}".format(
                tenant_name, users_modified
            )
        )

        return result

    except Exception as e:
        error_msg = str(e)
        frappe.log_error(
            "Qalcuity Deprovisioning Error for {0}: {1}".format(
                tenant_name, error_msg
            ),
            "Qalcuity Deprovisioning",
        )

        try:
            customer = frappe.db.get_value(
                "Qalcuity Tenant", tenant_name, "customer"
            )
            _create_provisioning_log(
                tenant=tenant_name,
                customer=customer,
                action="Deprovision",
                status="Failed",
                details="",
                error_message=error_msg,
            )
        except Exception:
            pass

        return {"status": "failed", "error": error_msg}


# =============================================================================
# Status Check
# =============================================================================

def get_provisioning_status(tenant_name):
    """
    Check if tenant is provisioned, return status dict.

    Args:
        tenant_name: Name of the Qalcuity Tenant document

    Returns:
        dict: Provisioning status information
    """
    try:
        tenant = frappe.get_doc("Qalcuity Tenant", tenant_name)
        return {
            "tenant": tenant_name,
            "customer": tenant.customer,
            "erp_provisioning_status": tenant.erp_provisioning_status
            or PROVISIONING_STATUS_NOT_STARTED,
            "erp_company": tenant.erp_company,
            "provisioned_on": tenant.provisioned_on,
            "last_provisioning_attempt": tenant.last_provisioning_attempt,
            "provisioning_error": tenant.provisioning_error,
        }
    except Exception as e:
        frappe.log_error(
            "Qalcuity: Failed to get provisioning status for {0}: {1}".format(
                tenant_name, str(e)
            ),
            "Qalcuity Provisioning",
        )
        return {
            "tenant": tenant_name,
            "erp_provisioning_status": "Unknown",
            "error": str(e),
        }


# =============================================================================
# Retry Failed Provisioning
# =============================================================================

def retry_failed_provisioning():
    """
    Scheduler task — retry any tenant with provisioning_status='Failed'.
    Called from tasks.py daily.

    Returns:
        dict: Summary of retry results
    """
    failed_tenants = frappe.get_all(
        "Qalcuity Tenant",
        filters={
            "erp_provisioning_status": PROVISIONING_STATUS_FAILED,
            "status": "Active",
        },
        fields=["name", "customer", "tenant_id"],
    )

    if not failed_tenants:
        frappe.logger().info("Qalcuity: No failed provisionings to retry")
        return {"retried": 0, "succeeded": 0, "failed": 0}

    retried = 0
    succeeded = 0
    failed = 0

    for tenant in failed_tenants:
        retried += 1
        frappe.logger().info(
            "Qalcuity: Retrying provisioning for tenant {0} ({1})".format(
                tenant.name, tenant.tenant_id
            )
        )

        try:
            result = provision_tenant(tenant.name)
            if result.get("status") == "success":
                succeeded += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            frappe.log_error(
                "Qalcuity: Retry failed for tenant {0}: {1}".format(
                    tenant.name, str(e)
                ),
                "Qalcuity Provisioning Retry",
            )

    summary = {
        "retried": retried,
        "succeeded": succeeded,
        "failed": failed,
    }

    frappe.logger().info(
        "Qalcuity: Provisioning retry summary: {0}".format(json.dumps(summary))
    )

    return summary


# =============================================================================
# Reactivate Provisioning (when subscription is reactivated)
# =============================================================================

def reactivate_tenant(tenant_name):
    """
    Re-provision tenant when subscription is reactivated.
    Reuses existing Company and re-assigns roles.

    Args:
        tenant_name: Name of the Qalcuity Tenant document

    Returns:
        dict: Result of provisioning
    """
    try:
        tenant = frappe.get_doc("Qalcuity Tenant", tenant_name)

        # If already completed, just re-assign roles
        if (
            tenant.erp_provisioning_status == PROVISIONING_STATUS_COMPLETED
            and tenant.erp_company
        ):
            # Re-assign roles
            users_modified = assign_erp_roles(
                tenant.customer, tenant.erp_company
            )

            # Update status
            frappe.db.set_value(
                "Qalcuity Tenant",
                tenant_name,
                {
                    "erp_provisioning_status": PROVISIONING_STATUS_COMPLETED,
                    "provisioning_error": "",
                },
            )
            frappe.db.commit()

            # Create log
            _create_provisioning_log(
                tenant=tenant_name,
                customer=tenant.customer,
                action="Role_Assign",
                status="Success",
                details="Re-activated: roles re-assigned to {0} user(s)".format(
                    users_modified
                ),
                company_created=tenant.erp_company,
                users_modified=users_modified,
            )

            return {
                "status": "success",
                "company": tenant.erp_company,
                "users_modified": users_modified,
            }

        # If suspended, run full provisioning
        if tenant.erp_provisioning_status == PROVISIONING_STATUS_SUSPENDED:
            return provision_tenant(tenant_name)

        # If not started or failed, run full provisioning
        return provision_tenant(tenant_name)

    except Exception as e:
        frappe.log_error(
            "Qalcuity: Reactivation failed for tenant {0}: {1}".format(
                tenant_name, str(e)
            ),
            "Qalcuity Provisioning",
        )
        return {"status": "failed", "error": str(e)}


# =============================================================================
# Internal Helper Functions
# =============================================================================

def _validate_prerequisites(tenant):
    """Validate that all prerequisites for provisioning are met."""
    # Check tenant is Active
    if tenant.status != "Active":
        frappe.throw(
            _("Cannot provision tenant {0}: status is {1}").format(
                tenant.tenant_id, tenant.status
            )
        )

    # Check customer exists
    if not tenant.customer:
        frappe.throw(
            _("Cannot provision tenant {0}: no customer linked").format(
                tenant.tenant_id
            )
        )

    # Check at least one Portal User exists for this customer
    portal_user_count = frappe.db.count(
        "Portal User",
        {"parent": tenant.customer, "parenttype": "Customer"},
    )
    if portal_user_count == 0:
        frappe.throw(
            _("Cannot provision tenant {0}: no portal users linked to customer {1}").format(
                tenant.tenant_id, tenant.customer
            )
        )


def _update_provisioning_status(tenant_name, status):
    """Update provisioning status on tenant."""
    frappe.db.set_value(
        "Qalcuity Tenant",
        tenant_name,
        {
            "erp_provisioning_status": status,
            "last_provisioning_attempt": now_datetime(),
        },
    )
    frappe.db.commit()


def _ensure_role_exists(role_name):
    """Ensure a Frappe role exists. Create if not."""
    if not frappe.db.exists("Role", role_name):
        role = frappe.get_doc(
            {
                "doctype": "Role",
                "role_name": role_name,
                "desk_access": 1,
                "is_custom": 1,
                "description": "Standard ERP access for Qalcuity customers",
            }
        )
        role.insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.logger().info(
            "Qalcuity: Role '{0}' created".format(role_name)
        )


def _add_role_to_user(user_name, role_name):
    """Add a role to a user if not already assigned."""
    # Check if user already has this role
    existing = frappe.db.exists(
        "Has Role",
        {"parent": user_name, "role": role_name},
    )
    if not existing:
        frappe.get_doc(
            {
                "doctype": "Has Role",
                "parent": user_name,
                "parenttype": "User",
                "role": role_name,
            }
        ).insert(ignore_permissions=True)


def _remove_role_from_user(user_name, role_name):
    """Remove a role from a user."""
    existing = frappe.db.exists(
        "Has Role",
        {"parent": user_name, "role": role_name},
    )
    if existing:
        frappe.delete_doc("Has Role", existing, ignore_permissions=True)


def _clear_role_cache(user_list):
    """Clear Frappe role cache for affected users."""
    for user in user_list:
        try:
            frappe.clear_cache(user=user)
        except Exception:
            pass


def _create_provisioning_log(
    tenant,
    customer,
    action,
    status,
    details="",
    error_message="",
    company_created=None,
    users_modified=0,
):
    """Create a provisioning log entry."""
    try:
        log = frappe.get_doc(
            {
                "doctype": "Qalcuity Provisioning Log",
                "tenant": tenant,
                "customer": customer,
                "action": action,
                "status": status,
                "details": details,
                "error_message": error_message,
                "company_created": company_created,
                "users_modified": users_modified,
            }
        )
        log.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            "Qalcuity: Failed to create provisioning log: {0}".format(str(e)),
            "Qalcuity Provisioning",
        )

