# Qalcuity ERP — API Documentation

> **Last Updated:** 2026-08-26

---

## 1. Overview

Qalcuity ERP menyediakan dua lapisan API:

1. **Core API** — Frappe whitelisted methods, diakses via `frappe.call()` atau HTTP POST ke `/api/method/`
2. **API v1** — Versioned REST-style endpoints dengan auth middleware, rate limiting, dan standard response format

### Base URL

```
https://qalcuity.com
```

### Authentication

| Method | Scope | Description |
|--------|-------|-------------|
| Session Cookie | Semua endpoint | Login via Frappe session (default) |
| `allow_guest=True` | Public endpoints | Tidak perlu authentication |
| User Session | Customer/Admin | `frappe.session.user` must be set |

### Rate Limiting

| Scope | Limit | Window | Storage |
|-------|-------|--------|---------|
| Global (API v1) | 100 requests/min/user | Sliding window | `frappe.cache` |
| Registration | 5 requests/hour/IP | Sliding window | `frappe.cache` |
| Resend Verification | 3 requests/hour/email | Sliding window | `frappe.cache` |
| Password Reset | 3 requests/hour/email | Sliding window | `frappe.cache` |

### Standard Response Format (API v1)

**Success:**
```json
{
  "success": true,
  "message": "Success",
  "data": { ... },
  "meta": { ... }
}
```

**Error:**
```json
{
  "success": false,
  "message": "Error description",
  "code": "VALIDATION_ERROR",
  "details": { ... }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Input validation failed |
| `NOT_FOUND` | 404 | Resource not found |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `SERVER_ERROR` | 500 | Internal server error |

---

## 2. Endpoint Groups

### Table of Contents

1. [Public Endpoints](#21-public-endpoints)
2. [Registration & Auth](#22-registration--auth)
3. [Customer Profile](#23-customer-profile)
4. [Payment](#24-payment)
5. [Subscription](#25-subscription)
6. [Dashboard & Account](#26-dashboard--account)
7. [Notification](#27-notification)
8. [Admin — Payment Review](#28-admin--payment-review)
9. [Admin — Dashboard & Stats](#29-admin--dashboard--stats)
10. [Admin — Backup](#210-admin--backup)
11. [Audit Log](#211-audit-log)
12. [Two-Factor Authentication](#212-two-factor-authentication)
13. [Session Management](#213-session-management)
14. [System Health](#214-system-health)
15. [API v1 — Versioned Endpoints](#215-api-v1--versioned-endpoints)

---

## 2.1 Public Endpoints

Endpoints yang dapat diakses tanpa login.

### GET `/api/method/qalcuity.qalcuity.api.plans.get_active_plans`

Get list of active subscription plans with features.

**Auth:** Public (`allow_guest=True`)
**Rate Limit:** None

**Parameters:** None

**Response:**
```json
{
  "plans": [
    {
      "name": "Starter",
      "plan_name": "Starter",
      "price": 150000,
      "price_formatted": "Rp 150.000",
      "billing_period": "Monthly",
      "max_users": 5,
      "max_storage": "5 GB",
      "description": "Plan untuk bisnis kecil",
      "features": [
        { "feature": "Accounting", "included": true },
        { "feature": "CRM", "included": true }
      ]
    }
  ]
}
```

---

### GET `/api/method/qalcuity.qalcuity.api.plans.get_plan_by_name`

Get a specific plan by name.

**Auth:** Public (`allow_guest=True`)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_name` | string | Yes | Plan name (e.g., "Starter") |

**Response:**
```json
{
  "plan": {
    "name": "Starter",
    "price": 150000,
    "billing_period": "Monthly",
    "features": [...]
  }
}
```

---

### GET `/api/method/qalcuity.qalcuity.api.v1.endpoints.get_plans`

API v1 wrapper — Get active plans.

**Auth:** Public (`allow_guest=True`)
**Rate Limit:** None

**Response:**
```json
{
  "success": true,
  "data": { "plans": [...] }
}
```

---

### GET `/api/method/qalcuity.qalcuity.api.v1.endpoints.get_settings`

Get global Qalcuity settings (company name, branding, bank details).

**Auth:** Public (`allow_guest=True`)
**Rate Limit:** None

**Response:**
```json
{
  "success": true,
  "data": {
    "company_name": "Qalcuity",
    "payment_mode": "Manual",
    "whatsapp_number": "628123456789",
    "bank_accounts": [
      { "bank_name": "BRI", "account_number": "1234567890", "account_name": "Qalcuity" }
    ]
  }
}
```

---

## 2.2 Registration & Auth

### POST `/api/method/qalcuity.qalcuity.api.registration.register_customer`

Register a new customer account.

**Auth:** Public (`allow_guest=True`)
**Rate Limit:** 5 requests/hour/IP

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `full_name` | string | Yes | Customer full name |
| `email` | string | Yes | Valid email address |
| `password` | string | Yes | Min 8 chars, must contain letter + number |
| `company_name` | string | Yes | Company name |
| `phone` | string | Yes | Phone number |

**Request Example:**
```json
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "password": "securepass123",
  "company_name": "Doe Corp",
  "phone": "08123456789"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Registration successful. Please check your email for verification.",
  "data": {
    "email": "john@example.com",
    "verification_email_sent": true
  }
}
```

**Flow:**
1. Creates User (disabled) → Customer → Portal User → Tenant (via hook)
2. Sends verification email with HMAC-SHA256 token (TTL 24 hours)
3. User must verify email before login

---

### POST `/api/method/qalcuity.qalcuity.api.registration.verify_email`

Verify email address using token from verification email.

**Auth:** Public (`allow_guest=True`)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | string | Yes | Verification token from email |
| `email` | string | Yes | Email address to verify |

**Response:**
```json
{
  "success": true,
  "message": "Email verified successfully. You can now login."
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.registration.resend_verification_email`

Resend verification email.

**Auth:** Public (`allow_guest=True`)
**Rate Limit:** 3 requests/hour/email

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `email` | string | Yes | Email address to resend verification |

**Response:**
```json
{
  "success": true,
  "message": "Verification email sent."
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.v1.endpoints.register`

API v1 wrapper — Register a new customer.

**Auth:** Public (`allow_guest=True`)
**Rate Limit:** 5 requests/hour/IP

**Parameters:** Same as `register_customer`
**Response:** Standard v1 success response

---

### POST `/api/method/qalcuity.qalcuity.api.password_reset.request_password_reset`

Request password reset email.

**Auth:** Public (`allow_guest=True`)
**Rate Limit:** 3 requests/hour/email

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `email` | string | Yes | Email address for reset |

**Response:**
```json
{
  "success": true,
  "message": "If the email exists, a password reset link has been sent."
}
```

**Note:** Anti-enumeration — Always returns success message regardless of email existence.

---

### POST `/api/method/qalcuity.qalcuity.api.password_reset.reset_password`

Reset password using token from email.

**Auth:** Public (`allow_guest=True`)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | string | Yes | Reset token from email |
| `email` | string | Yes | Email address |
| `new_password` | string | Yes | New password (min 8 chars, letter + number) |

**Response:**
```json
{
  "success": true,
  "message": "Password reset successful. You can now login."
}
```

**Token TTL:** 1 hour

---

## 2.3 Customer Profile

### GET `/api/method/qalcuity.qalcuity.api.profile.get_profile`

Get current user's profile data.

**Auth:** Customer (Portal User)
**Rate Limit:** None

**Response:**
```json
{
  "user": {
    "name": "john@example.com",
    "full_name": "John Doe",
    "email": "john@example.com"
  },
  "customer": {
    "name": "John Doe",
    "customer_name": "John Doe",
    "customer_group": "All Customer Groups",
    "territory": "All Territories"
  },
  "tenant": {
    "name": "TENANT-20260826-0001",
    "tenant_id": "TENANT-20260826-0001",
    "company_name": "Doe Corp",
    "phone": "08123456789"
  }
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.profile.update_profile`

Update customer profile.

**Auth:** Customer (Portal User)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | JSON string | Yes | Profile data to update |

**Allowed fields:** `full_name`, `phone`, `company_name`

**Request Example:**
```json
{
  "data": "{\"full_name\": \"John Updated\", \"phone\": \"08987654321\"}"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Profile updated successfully."
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.profile.change_password`

Change user password.

**Auth:** Customer (Portal User)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `old_password` | string | Yes | Current password |
| `new_password` | string | Yes | New password (min 8 chars, letter + number) |

**Response:**
```json
{
  "success": true,
  "message": "Password changed successfully."
}
```

---

### API v1 Profile Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/method/qalcuity.qalcuity.api.v1.endpoints.get_profile` | GET | Customer | Get customer profile |
| `/api/method/qalcuity.qalcuity.api.v1.endpoints.update_profile` | POST | Customer | Update customer profile |

---

## 2.4 Payment

### POST `/api/method/qalcuity.qalcuity.api.payment.submit_payment`

Submit a payment proof.

**Auth:** Customer (Portal User)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `subscription` | string | Yes | Subscription name (docname) |
| `amount` | number | Yes | Payment amount |
| `payment_method` | string | Yes | Payment method (e.g., "Bank Transfer") |
| `payment_date` | string | Yes | Payment date (YYYY-MM-DD) |
| `proof_of_payment` | file | No | Payment proof image/file |
| `reference_number` | string | No | Bank reference number |

**Response:**
```json
{
  "success": true,
  "message": "Payment submitted successfully",
  "payment_name": "QPAY-20260826-0001"
}
```

**Side Effects:**
- Creates Qalcuity Payment record with status PENDING
- Sends email notification to superadmin
- Creates in-app notification
- Creates audit log entry

---

### POST `/api/method/qalcuity.qalcuity.api.payment.approve_payment`

Approve a payment (admin).

**Auth:** Admin/Superadmin
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `payment_name` | string | Yes | Payment document name |

**Response:**
```json
{
  "success": true,
  "message": "Payment approved",
  "subscription_created": true
}
```

**Side Effects:**
- Updates payment status to APPROVED
- Auto-creates Subscription (ACTIVE) if applicable
- Triggers ERP provisioning
- Sends approval email to customer
- Creates audit log + subscription log

---

### POST `/api/method/qalcuity.qalcuity.api.payment.reject_payment`

Reject a payment (admin).

**Auth:** Admin/Superadmin
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `payment_name` | string | Yes | Payment document name |
| `reason` | string | Yes | Rejection reason |

**Response:**
```json
{
  "success": true,
  "message": "Payment rejected"
}
```

**Side Effects:**
- Updates payment status to REJECTED
- Sends rejection email to customer
- Creates audit log entry

---

### GET `/api/method/qalcuity.qalcuity.api.payment.get_payment_status`

Get payment status and details.

**Auth:** Customer (ownership check) or Admin
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `payment_name` | string | Yes | Payment document name |

**Response:**
```json
{
  "payment": {
    "name": "QPAY-20260826-0001",
    "status": "PENDING",
    "amount": 150000,
    "payment_method": "Bank Transfer",
    "payment_date": "2026-08-26",
    "proof_of_payment": "/files/proof.png",
    "customer": "John Doe"
  }
}
```

---

### GET `/api/method/qalcuity.qalcuity.api.payment.get_my_payments`

Get paginated payment history for current user.

**Auth:** Customer (Portal User)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | int | No | Page number (default: 1) |
| `page_size` | int | No | Items per page (default: 10) |

**Response:**
```json
{
  "payments": [...],
  "total": 25,
  "page": 1,
  "page_size": 10,
  "total_pages": 3
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.payment.bulk_approve_payments`

Bulk approve multiple payments (admin).

**Auth:** Admin/Superadmin
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `payment_names` | JSON array | Yes | List of payment document names |

**Request Example:**
```json
{
  "payment_names": "[\"QPAY-20260826-0001\", \"QPAY-20260826-0002\"]"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully approved 2 payments",
  "approved": 2,
  "failed": 0
}
```

**Note:** Batch rollback on error — if any payment fails, previously approved payments are rolled back.

---

### POST `/api/method/qalcuity.qalcuity.api.payment.bulk_reject_payments`

Bulk reject multiple payments (admin).

**Auth:** Admin/Superadmin
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `payment_names` | JSON array | Yes | List of payment document names |
| `reason` | string | Yes | Rejection reason |

**Response:**
```json
{
  "success": true,
  "message": "Successfully rejected 2 payments",
  "rejected": 2,
  "failed": 0
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.plans.submit_payment_with_subscription`

Submit payment and create subscription simultaneously.

**Auth:** Customer (Portal User)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_name` | string | Yes | Plan name |
| `amount` | number | Yes | Payment amount |
| `payment_method` | string | Yes | Payment method |
| `payment_date` | string | Yes | Payment date (YYYY-MM-DD) |
| `proof_of_payment` | file | No | Payment proof file |
| `reference_number` | string | No | Bank reference number |

**Response:**
```json
{
  "success": true,
  "message": "Payment submitted with subscription",
  "subscription_name": "QSUB-20260826-0001",
  "payment_name": "QPAY-20260826-0001"
}
```

---

## 2.5 Subscription

### GET `/api/method/qalcuity.qalcuity.api.subscription_history.get_my_subscription_history`

Get paginated subscription history for current user.

**Auth:** Customer (Portal User) or Admin
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit_page_length` | int | No | Items per page (default: 20) |
| `start` | int | No | Offset (default: 0) |

**Response:**
```json
{
  "history": [
    {
      "name": "SL-20260826-0001",
      "subscription": "QSUB-20260826-0001",
      "action": "CREATE",
      "old_status": null,
      "new_status": "ACTIVE",
      "old_plan": null,
      "new_plan": "Starter",
      "timestamp": "2026-08-26 10:00:00",
      "notes": "Subscription created after payment approval"
    }
  ],
  "has_more": false
}
```

---

### GET `/api/method/qalcuity.qalcuity.api.subscription_history.get_subscription_history`

Get subscription history for a specific subscription (admin).

**Auth:** Admin (with access check)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `subscription_name` | string | Yes | Subscription document name |

**Response:** Array of subscription log entries.

---

### API v1 Subscription History

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/method/qalcuity.qalcuity.api.v1.endpoints.get_my_subscription_history` | GET | Customer | Get user's subscription history |
| `/api/method/qalcuity.qalcuity.api.v1.endpoints.get_all_subscription_history` | GET | Admin | Get all subscription history |

---

## 2.6 Dashboard & Account

### GET `/api/method/qalcuity.qalcuity.api.dashboard.get_dashboard_data`

Get dashboard data for current customer.

**Auth:** Customer (Portal User)
**Rate Limit:** None

**Response:**
```json
{
  "subscription": {
    "name": "QSUB-20260826-0001",
    "status": "ACTIVE",
    "plan": "Starter",
    "start_date": "2026-08-26",
    "end_date": "2026-09-26"
  },
  "tenant": {
    "name": "TENANT-20260826-0001",
    "tenant_id": "TENANT-20260826-0001",
    "status": "Active",
    "provisioning_status": "Completed"
  },
  "recent_payments": [
    {
      "name": "QPAY-20260826-0001",
      "status": "APPROVED",
      "amount": 150000
    }
  ]
}
```

---

### GET `/api/method/qalcuity.qalcuity.api.account_status.get_account_status`

Get comprehensive account status.

**Auth:** Customer (Portal User)
**Rate Limit:** None

**Response:**
```json
{
  "subscription": {
    "name": "QSUB-20260826-0001",
    "status": "ACTIVE",
    "plan": "Starter",
    "start_date": "2026-08-26",
    "end_date": "2026-09-26",
    "days_remaining": 30,
    "is_grace_period": false
  },
  "tenant": {
    "name": "TENANT-20260826-0001",
    "status": "Active",
    "company_name": "Doe Corp"
  },
  "payment_summary": {
    "total": 5,
    "pending": 1,
    "approved": 3,
    "rejected": 1
  },
  "usage": {
    "storage_used": "1.2 GB",
    "storage_limit": "5 GB",
    "users_active": 3,
    "users_limit": 5
  }
}
```

---

### API v1 Dashboard & Account

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/method/qalcuity.qalcuity.api.v1.endpoints.get_dashboard` | GET | Customer | Get dashboard data |
| `/api/method/qalcuity.qalcuity.api.v1.endpoints.get_account_status` | GET | Customer | Get account status |

---

## 2.7 Notification

### GET `/api/method/qalcuity.qalcuity.api.notification.get_my_notifications`

Get paginated notifications for current user.

**Auth:** Customer/Admin (Portal User)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit_page_length` | int | No | Items per page (default: 20) |
| `start` | int | No | Offset (default: 0) |

**Response:**
```json
{
  "notifications": [
    {
      "name": "NOTIF-20260826-0001",
      "title": "Payment Approved",
      "message": "Your payment has been approved.",
      "is_read": 0,
      "notification_type": "payment",
      "creation": "2026-08-26 10:00:00"
    }
  ],
  "unread_count": 3
}
```

---

### GET `/api/method/qalcuity.qalcuity.api.notification.get_unread_count`

Get unread notification count.

**Auth:** Customer/Admin (Portal User)
**Rate Limit:** None

**Response:**
```json
{
  "count": 3
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.notification.mark_as_read`

Mark a single notification as read.

**Auth:** Customer/Admin (ownership check)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `notification_name` | string | Yes | Notification document name |

**Response:**
```json
{
  "success": true,
  "message": "Notification marked as read"
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.notification.mark_all_as_read`

Mark all notifications as read for current user.

**Auth:** Customer/Admin (Portal User)
**Rate Limit:** None

**Response:**
```json
{
  "success": true,
  "message": "All notifications marked as read"
}
```

---

## 2.8 Admin — Payment Review

### GET `/api/method/qalcuity.qalcuity.api.admin.get_pending_payments`

Get pending payment reviews for admin.

**Auth:** Admin/Superadmin
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filters` | JSON string | No | Filters: `status`, `date_from`, `date_to`, `customer` |

**Request Example:**
```json
{
  "filters": "{\"status\": \"Pending\", \"date_from\": \"2026-08-01\"}"
}
```

**Response:**
```json
{
  "payments": [
    {
      "name": "QPAY-20260826-0001",
      "customer": "John Doe",
      "amount": 150000,
      "payment_method": "Bank Transfer",
      "status": "Pending",
      "creation": "2026-08-26 10:00:00"
    }
  ],
  "total": 15
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.admin.approve_payment`

Approve a payment (admin).

**Auth:** Admin/Superadmin
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `payment_name` | string | Yes | Payment document name |

**Response:**
```json
{
  "success": true,
  "message": "Payment approved successfully",
  "subscription_created": true
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.admin.reject_payment`

Reject a payment (admin).

**Auth:** Admin/Superadmin
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `payment_name` | string | Yes | Payment document name |
| `reason` | string | Yes | Rejection reason |

**Response:**
```json
{
  "success": true,
  "message": "Payment rejected successfully"
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.admin.bulk_approve_payments`

Bulk approve multiple payments (admin).

**Auth:** Admin/Superadmin
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `payment_names` | JSON array | Yes | List of payment document names |

**Response:**
```json
{
  "success": true,
  "message": "Bulk approve completed",
  "approved": 5,
  "failed": 0,
  "errors": []
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.admin.bulk_reject_payments`

Bulk reject multiple payments (admin).

**Auth:** Admin/Superadmin
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `payment_names` | JSON array | Yes | List of payment document names |
| `reason` | string | Yes | Rejection reason |

**Response:**
```json
{
  "success": true,
  "message": "Bulk reject completed",
  "rejected": 5,
  "failed": 0,
  "errors": []
}
```

---

### GET `/api/method/qalcuity.qalcuity.api.admin.get_review_stats`

Get payment review statistics (admin).

**Auth:** Admin/Superadmin
**Rate Limit:** None

**Response:**
```json
{
  "pending": 15,
  "approved_this_month": 8,
  "rejected_this_month": 2,
  "total_this_month": 10
}
```

---

## 2.9 Admin — Dashboard & Stats

### GET `/api/method/qalcuity.qalcuity.api.admin_dashboard.get_admin_dashboard_data`

Get comprehensive admin dashboard data.

**Auth:** Admin/Superadmin
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date_from` | string | No | Start date (YYYY-MM-DD) |
| `date_to` | string | No | End date (YYYY-MM-DD) |

**Response:**
```json
{
  "revenue": {
    "this_month": 1500000,
    "last_month": 1200000,
    "growth_pct": 25.0,
    "total": 12000000
  },
  "customers": {
    "total": 50,
    "new_this_month": 5,
    "active": 42,
    "inactive": 8
  },
  "subscriptions": {
    "active": 40,
    "expired": 5,
    "grace_period": 3,
    "pending": 2
  },
  "payments": {
    "pending": 15,
    "approved_this_month": 8,
    "rejected_this_month": 2
  },
  "tenants": {
    "total": 42,
    "active": 38,
    "provisioning": 2,
    "failed": 2
  },
  "revenue_trend": [
    { "month": "2026-03", "revenue": 800000 },
    { "month": "2026-04", "revenue": 950000 }
  ],
  "recent_activity": [
    {
      "action": "Payment Approved",
      "user": "admin@qalcuity.com",
      "timestamp": "2026-08-26 10:00:00"
    }
  ]
}
```

---

## 2.10 Admin — Backup

### POST `/api/method/qalcuity.qalcuity.api.backup_api.trigger_backup`

Trigger a manual backup.

**Auth:** Admin/Superadmin
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `backup_type` | string | No | "Full" (default), "Database", or "Files" |

**Response:**
```json
{
  "success": true,
  "message": "Backup triggered successfully",
  "backup_name": "BACKUP-20260826-0001"
}
```

---

### GET `/api/method/qalcuity.qalcuity.api.backup_api.get_backup_status`

Get latest backup status.

**Auth:** Admin/Superadmin
**Rate Limit:** None

**Response:**
```json
{
  "backup_name": "BACKUP-20260826-0001",
  "status": "Completed",
  "backup_type": "Full",
  "database_size": "45.2 MB",
  "files_size": "120.5 MB",
  "creation": "2026-08-26 03:00:00"
}
```

---

### GET `/api/method/qalcuity.qalcuity.api.backup_api.get_backup_list`

Get paginated backup list.

**Auth:** Admin/Superadmin
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | int | No | Page number (default: 1) |
| `limit` | int | No | Items per page (default: 20) |
| `filters` | JSON string | No | Filter options |

**Response:**
```json
{
  "backups": [...],
  "total": 30,
  "page": 1,
  "total_pages": 2
}
```

---

### GET `/api/method/qalcuity.qalcuity.api.backup_api.download_backup`

Download a backup file.

**Auth:** Admin/Superadmin
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `backup_name` | string | Yes | Backup document name |

**Response:** Binary file download (`.sql.gz` or `.tar.gz`)

---

### POST `/api/method/qalcuity.qalcuity.api.backup_api.delete_backup`

Delete a backup file.

**Auth:** Admin/Superadmin
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `backup_name` | string | Yes | Backup document name |

**Response:**
```json
{
  "success": true,
  "message": "Backup deleted successfully"
}
```

---

### GET `/api/method/qalcuity.qalcuity.api.backup_api.get_backup_stats`

Get backup statistics.

**Auth:** Admin/Superadmin
**Rate Limit:** None

**Response:**
```json
{
  "total_backups": 30,
  "total_size": "3.5 GB",
  "last_backup": "2026-08-26 03:00:00",
  "retention_days": 30
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.backup_api.trigger_cleanup`

Trigger cleanup of old backups.

**Auth:** Admin/Superadmin
**Rate Limit:** None

**Response:**
```json
{
  "success": true,
  "message": "Cleanup completed",
  "deleted_count": 5
}
```

---

## 2.11 Audit Log

### GET `/api/method/qalcuity.qalcuity.api.audit.get_audit_logs`

Get paginated audit logs (admin only).

**Auth:** Admin/Superadmin
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filters` | JSON string | No | Filters: `user`, `action`, `doc_type`, `date_from`, `date_to` |
| `limit_page_length` | int | No | Items per page (default: 20) |
| `start` | int | No | Offset (default: 0) |
| `order_by` | string | No | Sort order (default: "timestamp desc") |

**Response:**
```json
{
  "logs": [
    {
      "name": "AL-20260826-0001",
      "user": "admin@qalcuity.com",
      "action": "payment_approve",
      "doc_type": "Qalcuity Payment",
      "doc_name": "QPAY-20260826-0001",
      "details": "Payment approved for John Doe",
      "ip_address": "192.168.1.1",
      "timestamp": "2026-08-26 10:00:00"
    }
  ],
  "total": 150
}
```

---

### GET `/api/method/qalcuity.qalcuity.api.audit.get_my_audit_logs`

Get paginated audit logs for current user.

**Auth:** Customer/Admin (Portal User)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit_page_length` | int | No | Items per page (default: 20) |
| `start` | int | No | Offset (default: 0) |

**Response:** Same format as `get_audit_logs`, filtered to current user.

---

### API v1 Audit Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/method/qalcuity.qalcuity.api.v1.endpoints.get_audit_logs` | GET | Admin | Get all audit logs |
| `/api/method/qalcuity.qalcuity.api.v1.endpoints.get_my_audit_logs` | GET | Customer | Get user's own audit logs |

---

### Recorded Audit Events

| Event | Description |
|-------|-------------|
| `payment_submit` | Customer submits payment |
| `payment_approve` | Admin approves payment |
| `payment_reject` | Admin rejects payment |
| `subscription_create` | Subscription created |
| `subscription_activate` | Subscription activated |
| `subscription_expire` | Subscription expired |
| `subscription_suspend` | Subscription suspended |
| `user_register` | New user registration |
| `profile_update` | Profile updated |
| `backup_trigger` | Backup triggered |
| `backup_complete` | Backup completed |
| `backup_failed` | Backup failed |

---

## 2.12 Two-Factor Authentication

TOTP-based 2FA implementation (RFC 6238). No external dependencies — uses Python `hmac` + `hashlib`.

### GET `/api/method/qalcuity.qalcuity.api.two_factor.get_2fa_status`

Get 2FA status for current user.

**Auth:** Customer/Admin (Portal User)
**Rate Limit:** None

**Response:**
```json
{
  "enabled": false,
  "has_secret": false,
  "global_allowed": true,
  "backup_codes_remaining": 0
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.two_factor.setup_2fa`

Generate 2FA secret and QR code URL for initial setup.

**Auth:** Customer/Admin (Portal User)
**Rate Limit:** 5-minute cache per user

**Response:**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code_url": "https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=otpauth://totp/Qalcuity+ERP:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Qalcuity+ERP",
  "otpauth_uri": "otpauth://totp/Qalcuity+ERP:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Qalcuity+ERP",
  "message": "Scan QR code with your authenticator app, then verify with a code"
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.two_factor.enable_2fa`

Enable 2FA after verifying initial setup code.

**Auth:** Customer/Admin (Portal User)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `code` | string | Yes | 6-digit TOTP code from authenticator app |

**Response:**
```json
{
  "success": true,
  "message": "2FA enabled successfully",
  "backup_codes": [
    "ABCD-1234",
    "EFGH-5678",
    "IJKL-9012",
    "MNOP-3456",
    "QRST-7890",
    "UVWX-1234",
    "YZAB-5678",
    "CDEF-9012"
  ]
}
```

**Note:** Backup codes are shown only once. 8 codes in `XXXX-XXXX` format.

---

### POST `/api/method/qalcuity.qalcuity.api.two_factor.disable_2fa`

Disable 2FA after password confirmation.

**Auth:** Customer/Admin (Portal User)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `password` | string | Yes | Current password for confirmation |

**Response:**
```json
{
  "success": true,
  "message": "2FA disabled successfully"
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.two_factor.regenerate_backup_codes`

Regenerate backup codes after password confirmation.

**Auth:** Customer/Admin (Portal User)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `password` | string | Yes | Current password for confirmation |

**Response:**
```json
{
  "success": true,
  "message": "Backup codes regenerated",
  "backup_codes": [...]
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.two_factor.pre_login_check`

Pre-login validation — checks password and determines if 2FA is required.

**Auth:** Public (`allow_guest=True`)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user` | string | Yes | Username/email |
| `password` | string | Yes | Password |

**Response:**
```json
{
  "success": true,
  "requires_2fa": true,
  "token": "temp_login_token_xxx"
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.two_factor.verify_2fa_login`

Verify 2FA code during login.

**Auth:** Public (`allow_guest=True`)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | string | Yes | Temporary login token from pre_login_check |
| `code` | string | Yes | 6-digit TOTP code or backup code |

**Response:**
```json
{
  "success": true,
  "message": "Login successful"
}
```

---

### GET `/api/method/qalcuity.qalcuity.api.two_factor.get_2fa_qr_for_profile`

Get QR code URL for profile page display.

**Auth:** Customer/Admin (Portal User)
**Rate Limit:** None

**Response:**
```json
{
  "qr_code_url": "https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=..."
}
```

---

### Technical Details

| Parameter | Value |
|-----------|-------|
| Algorithm | TOTP (RFC 6238) |
| HMAC | SHA-1 |
| Time Step | 30 seconds |
| Code Length | 6 digits |
| Tolerance | ±1 time step (±30 seconds) |
| Secret Length | 20 bytes (160 bits) |
| Backup Codes | 8 codes, 8 chars each (`XXXX-XXXX`) |
| Backup Code Storage | SHA-256 hashed, stored in private files |

---

## 2.13 Session Management

### GET `/api/method/qalcuity.qalcuity.api.session_api.get_active_sessions`

Get list of active sessions with device info.

**Auth:** Customer/Admin (Portal User)
**Rate Limit:** None

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "abc123",
      "user_agent": "Mozilla/5.0 ...",
      "browser": "Chrome",
      "browser_version": "120.0",
      "os": "Windows",
      "device_type": "Desktop",
      "ip_address": "192.168.1.1",
      "last_active": "2026-08-26 10:00:00",
      "is_current": true
    }
  ],
  "total": 3
}
```

---

### POST `/api/method/qalcuity.qalcuity.api.session_api.force_logout_session`

Force logout a specific session.

**Auth:** Customer/Admin (Portal User)
**Rate Limit:** None

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Session ID to logout |

**Response:**
```json
{
  "success": true,
  "message": "Session logged out successfully"
}
```

**Note:** Cannot logout current session.

---

### POST `/api/method/qalcuity.qalcuity.api.session_api.force_logout_all_sessions`

Force logout all sessions except current.

**Auth:** Customer/Admin (Portal User)
**Rate Limit:** None

**Response:**
```json
{
  "success": true,
  "message": "All other sessions logged out",
  "logged_out_count": 2
}
```

---

## 2.14 System Health

### GET `/api/method/qalcuity.qalcuity.api.health_api.get_system_health`

Get comprehensive system health status.

**Auth:** Admin/Superadmin
**Rate Limit:** None

**Response:**
```json
{
  "system": {
    "uptime": "5 days 12:34:56",
    "disk_usage": {
      "total": "50 GB",
      "used": "35 GB",
      "free": "15 GB",
      "percent": 70
    },
    "memory_usage": {
      "total": "8192 MB",
      "used": "6144 MB",
      "free": "2048 MB",
      "percent": 75
    },
    "cpu_load": [1.5, 1.2, 0.8],
    "database_size": "45.2 MB",
    "platform": "Linux"
  },
  "application": {
    "frappe_version": "15.x.x",
    "erpnext_version": "15.x.x",
    "qalcuity_version": "0.1.0",
    "site_name": "qalcuity.com",
    "last_migrate": "2026-08-26 08:00:00",
    "scheduler_status": "Active"
  },
  "activity": {
    "active_users_24h": 15,
    "total_users": 50,
    "active_sessions": 8,
    "errors_today": 2,
    "total_customers": 42,
    "active_subscriptions": 40
  },
  "health_checks": {
    "database": { "status": "OK", "message": "Connected" },
    "redis": { "status": "OK", "message": "Connected" },
    "scheduler": { "status": "OK", "message": "Running" }
  }
}
```

---

## 2.15 API v1 — Versioned Endpoints

All API v1 endpoints use standard middleware:

- **Authentication** — Session-based auth check
- **Rate Limiting** — 100 requests/min/user sliding window
- **Standard Response** — `success_response()` / `error_response()`
- **Error Handling** — `_handle_endpoint_error()` wrapper

### Public Endpoints (No Auth)

| # | Endpoint | Method | Description |
|---|----------|--------|-------------|
| 1 | `qalcuity.qalcuity.api.v1.endpoints.get_plans` | GET | Get active plans |
| 2 | `qalcuity.qalcuity.api.v1.endpoints.register` | POST | Customer registration |
| 3 | `qalcuity.qalcuity.api.v1.endpoints.get_settings` | GET | Get global settings |

### Customer Endpoints (Portal User)

| # | Endpoint | Method | Description |
|---|----------|--------|-------------|
| 4 | `qalcuity.qalcuity.api.v1.endpoints.submit_payment` | POST | Submit payment proof |
| 5 | `qalcuity.qalcuity.api.v1.endpoints.get_my_payments` | GET | Get customer payments |
| 6 | `qalcuity.qalcuity.api.v1.endpoints.get_payment_status` | GET | Get payment status |
| 7 | `qalcuity.qalcuity.api.v1.endpoints.get_profile` | GET | Get customer profile |
| 8 | `qalcuity.qalcuity.api.v1.endpoints.update_profile` | POST | Update customer profile |
| 9 | `qalcuity.qalcuity.api.v1.endpoints.get_dashboard` | GET | Get dashboard data |
| 10 | `qalcuity.qalcuity.api.v1.endpoints.get_account_status` | GET | Get account status |
| 11 | `qalcuity.qalcuity.api.v1.endpoints.get_my_subscription_history` | GET | Get subscription history |
| 12 | `qalcuity.qalcuity.api.v1.endpoints.get_my_audit_logs` | GET | Get user audit logs |

### Admin Endpoints (Admin/Superadmin)

| # | Endpoint | Method | Description |
|---|----------|--------|-------------|
| 13 | `qalcuity.qalcuity.api.v1.endpoints.get_pending_reviews` | GET | Get pending payment reviews |
| 14 | `qalcuity.qalcuity.api.v1.endpoints.approve_payment` | POST | Approve payment |
| 15 | `qalcuity.qalcuity.api.v1.endpoints.reject_payment` | POST | Reject payment |
| 16 | `qalcuity.qalcuity.api.v1.endpoints.bulk_approve_payments` | POST | Bulk approve |
| 17 | `qalcuity.qalcuity.api.v1.endpoints.bulk_reject_payments` | POST | Bulk reject |
| 18 | `qalcuity.qalcuity.api.v1.endpoints.get_audit_logs` | GET | Get all audit logs |
| 19 | `qalcuity.qalcuity.api.v1.endpoints.get_all_subscription_history` | GET | Get all subscription history |

### Authenticated Endpoints

| # | Endpoint | Method | Description |
|---|----------|--------|-------------|
| 20 | `qalcuity.qalcuity.api.v1.endpoints.get_user_info` | GET | Get current user info |

---

## 3. Complete Endpoint Summary

### Core API Endpoints (40 total)

| Category | Count | Auth |
|----------|-------|------|
| Public | 4 | `allow_guest` |
| Registration & Auth | 4 | `allow_guest` |
| Customer Profile | 3 | Customer |
| Payment | 7 | Customer/Admin |
| Subscription | 2 | Customer/Admin |
| Dashboard & Account | 2 | Customer |
| Notification | 4 | Customer/Admin |
| Admin — Payment Review | 6 | Admin |
| Admin — Dashboard | 1 | Admin |
| Admin — Backup | 7 | Admin |
| Audit Log | 2 | Admin/Customer |
| 2FA | 7 | Customer/Admin/`allow_guest` |
| Session Management | 3 | Customer/Admin |
| System Health | 1 | Admin |
| **Total** | **53** | |

### API v1 Endpoints (20 total)

| Category | Count | Auth |
|----------|-------|------|
| Public | 3 | Public |
| Customer | 9 | Customer |
| Admin | 7 | Admin |
| Authenticated | 1 | Any |
| **Total** | **20** | |

---

## 4. Database Schema Reference

### DocTypes

| DocType | Naming | Key Fields |
|---------|--------|------------|
| Qalcuity Settings | Single | company_name, payment_mode, whatsapp_number |
| Qalcuity Plan | `PLN-####` | plan_name, price, billing_period, max_users, max_storage |
| Plan Feature | Child | feature, included |
| Qalcuity Subscription | `QSUB-{YYYYMMDD}-{####}` | customer, plan, status, start_date, end_date, tenant |
| Qalcuity Payment | `QPAY-{YYYYMMDD}-{####}` | customer, subscription, amount, status, proof_of_payment |
| Qalcuity Tenant | `TENANT-{YYYYMMDD}-{####}` | customer, company_name, status, provisioning_status |
| Qalcuity Audit Log | `AL-{YYYYMMDD}-{####}` | user, action, doc_type, doc_name, details, ip_address |
| Qalcuity Subscription Log | `SL-{YYYYMMDD}-{####}` | subscription, action, old_status, new_status |
| Qalcuity Backup | `BACKUP-{YYYYMMDD}-{####}` | status, backup_type, database_size, files_size |
| Qalcuity Bank Account | `BANK-{####}` | bank_name, account_number, account_name |
| Qalcuity Notification | `NOTIF-{YYYYMMDD}-{####}` | user, title, message, is_read, notification_type |
| Qalcuity Provisioning Log | `PROV-{YYYYMMDD}-{####}` | tenant, action, status, details |

### Subscription Status Flow

```text
PENDING → ACTIVE → EXPIRED
                  → GRACE_PERIOD → EXPIRED
ACTIVE → SUSPENDED → ACTIVE
```

### Payment Status Flow

```text
PENDING → APPROVED
PENDING → REJECTED
```

---

## 5. Security Reference

### Authentication Layers

| Layer | Implementation |
|-------|---------------|
| Session | Frappe session cookie |
| Role-based | Customer, Admin, Superadmin |
| Tenant Isolation | Row-level permission hooks |
| Company Isolation | ERPNext company-based filtering |
| API Rate Limiting | 100 req/min/user (sliding window) |
| Registration Rate Limit | 5/hour/IP |
| Password Reset Rate Limit | 3/hour/email |
| CSRF Protection | Hidden tokens in all web forms |
| Email Verification | HMAC-SHA256 tokens (24h TTL) |
| Password Reset | Token-based (1h TTL) |
| 2FA | TOTP (RFC 6238) + backup codes |
| Password Policy | Min 8 chars + letter + number |

### Permission Matrix

| Operation | Public | Customer | Admin | Superadmin |
|-----------|--------|----------|-------|------------|
| View Plans | ✅ | ✅ | ✅ | ✅ |
| Register | ✅ | — | — | — |
| Submit Payment | — | ✅ | — | — |
| View Own Payments | — | ✅ | — | — |
| View Profile | — | ✅ | — | — |
| Manage 2FA | — | ✅ | ✅ | ✅ |
| Manage Sessions | — | ✅ | ✅ | ✅ |
| Approve Payments | — | — | ✅ | ✅ |
| Reject Payments | — | — | ✅ | ✅ |
| View All Audit Logs | — | — | ✅ | ✅ |
| Trigger Backup | — | — | ✅ | ✅ |
| System Health | — | — | ✅ | ✅ |
| Admin Dashboard | — | — | ✅ | ✅ |
