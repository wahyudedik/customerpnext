# FEATURES.md

# Qalcuity ERP — Feature Specification

This document is the source of truth for planned and implemented Qalcuity features.

Qalcuity adalah produk SaaS ERP berbasis Frappe/ERPNext. ERPNext tetap menjadi core engine yang tidak dimodifikasi. Seluruh customisasi dilakukan di custom app [`qalcuity/`](qalcuity/).

---

# Arsitektur Fitur

```
                    QALCUITY ERP
                         │
                         ▼
              ┌─────────────────────┐
              │   ERPNext / Frappe  │  ← Core Engine (TIDAK DIMODIFIKASI)
              └──────────┬──────────┘
                         │
                Qalcuity Custom App  ← KODE KITA
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
    SaaS Layer     Branding/UI     New Features
```

---

# 0a. ERPNext Core Features (TIDAK DIMODIFIKASI)

Fitur-fitur ERPNext berikut **KITA PAKAI SEBAGAIMANA ADANYA** tanpa modifikasi:

### Accounting & Finance
* General Ledger
* Journal Entry
* Accounts Payable / Receivable
* Financial Statements (Profit & Loss, Balance Sheet, Cash Flow)
* Bank Reconciliation
* Multi-currency support
* Tax management

### CRM
* Lead management
* Opportunity tracking
* Customer relationship management
* Communication tracking

### HR & Payroll
* Employee management
* Attendance & Leave
* Payroll processing
* Expense claims
* Appraisals

### Inventory & Stock
* Warehouse management
* Stock entries
* Batch tracking
* Serial number tracking
* Inventory valuation
* Stock reports

### Sales
* Quotation
* Sales Order
* Sales Invoice
* Delivery Note
* Customer management

### Purchasing
* Purchase Order
* Purchase Invoice
* Purchase Receipt
* Supplier management
* Request for Quotation

### Projects
* Project management
* Task management
* Timesheet
* Activity tracking

### Core Engine
* Database ORM (Frappe)
* Workflow engine
* Permission system
* Report builder
* Print formats
* Email integration
* Document versioning

> **Catatan Penting:** Kita TIDAK memodifikasi fitur-fitur ini. Semua customisasi dilakukan di custom app [`qalcuity/`](qalcuity/). Update ERPNext dilakukan via `pip install --upgrade erpnext` atau `bench update`.

---

# 0b. Qalcuity Custom Features (DI BUAT SENDIRI)

Fitur-fitur berikut **DIKEMBANGKAN SENDIRI** di custom app [`qalcuity/`](qalcuity/):

### SaaS Subscription
* [`Qalcuity Plan`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_plan/) — Subscription plans (Starter, Professional, Enterprise, Trial)
* [`Qalcuity Subscription`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_subscription/) — Subscription lifecycle management
* Grace period 7 hari dengan status `Grace Period` terpisah
* Subscription enforcement (ERPNext access block)
* Plan limits enforcement (max_users, max_storage)
* Status transitions: `Draft → Pending Payment → Active → Grace Period → Expired/Suspended/Cancelled`

### Payment System
* [`Qalcuity Payment`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_payment/) — Manual payment records
* Multi bank accounts (BRI, JAGO, BTN, BSI)
* Payment mode toggle (Manual/Xendit/Hybrid)
* Payment proof upload
* WhatsApp confirmation link
* Bulk approve/reject

### Tenant Management
* [`Qalcuity Tenant`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_tenant/) — Tenant isolation
* Row-level permission hooks
* Tenant ID auto-generation
* Tenant lifecycle (Active, Suspended, Terminated)

### Customer Account
* Customer self-registration (`/register`)
* Customer profile (`/profile`)
* Account status (`/account-status`)
* Custom login page (Qalcuity-branded)

### SaaS Dashboard
* Customer dashboard (`/dashboard`)
* Payment history (`/my-payments`)
* Subscription history (`/subscription-history`)
* Admin reviews (`/admin-reviews`)

### Notifications
* [`Qalcuity Notification`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_notification/) — In-app notifications
* Bell icon component
* Email notifications (approval, rejection, expiry, grace period)
* Superadmin email notification

### Audit & Backup
* [`Qalcuity Audit Log`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_audit_log/) — Audit trail
* [`Qalcuity Backup`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_backup/) — Backup automation
* Database backup (mysqldump + gzip)
* File backup (tar -czf)
* Retention policy (30 hari)

### Qalcuity API
* API v1 versioned endpoints
* Auth check, rate limiting, standard response format
* SaaS-specific endpoints (registration, payment, subscription)

### Branding & UI/UX
* CSS branding (light/dark mode)
* Custom workspace
* Professional navigation icons
* Responsive design
* **Reusable navigation template** ([`navigation.html`](qalcuity/qalcuity/templates/includes/navigation.html)) — Shared header bar untuk semua halaman
* **Hamburger menu** untuk mobile (< 768px)
* **Responsive grid** (1 kolom mobile, 2 kolom tablet, 3+ kolom desktop)
* **Responsive forms** (full-width di mobile, 16px font-size)
* **Responsive tables** (horizontal scroll)
* **Touch-friendly** (min 44px touch target)
* **Desk branding hide rules** — Footer, sidebar, navbar ERPNext di-hide di [`qalcuity.js`](qalcuity/qalcuity/public/js/qalcuity.js)

### Security
* **Registration rate limiting** — Max 5 registrasi per jam per IP ([`registration.py`](qalcuity/qalcuity/api/registration.py))
* **Password validation standardized** — Minimum 8 characters + letter + number di semua titik (registration, profile)
* **API v1 rate limiting** — 100 req/min/user via frappe.cache
* **Tenant isolation** — Row-level permission hooks + Company-based isolation
* **Role-based authorization** — public/customer/admin roles
* **Audit logging** — Semua aksi sensitif tercatat
* **Two-Factor Authentication (2FA)** — TOTP-based (RFC 6238), setup/enable/disable, backup codes, QR code ([`two_factor.py`](qalcuity/qalcuity/api/two_factor.py))
* **Session management** — Active sessions list, force logout, user-agent parsing ([`session_api.py`](qalcuity/qalcuity/api/session_api.py))
* **CSRF protection** — Hidden tokens di semua web forms
* **Email verification** — HMAC-SHA256 token, TTL 24 jam ([`registration.py`](qalcuity/qalcuity/api/registration.py))
* **Password reset** — Token-based, TTL 1 jam, rate limited ([`password_reset.py`](qalcuity/qalcuity/api/password_reset.py))
* **System health monitoring** — System, application, activity stats + health checks ([`health_api.py`](qalcuity/qalcuity/api/health_api.py))

---

# 0c. Integration Layer (Hubungan ERPNext ↔ Qalcuity)

Qalcuity custom app terhubung dengan ERPNext melalui mekanisme berikut:

### Frappe Hooks
* `after_customer_insert` — Auto-create Tenant saat customer baru dibuat
* `has_permission` — Row-level permission hooks untuk tenant isolation
* `get_list` — Query filtering untuk data isolation
* `before_insert` — Plan limits enforcement
* Doc event hooks — Auto-create subscription saat payment approved
* `on_update` (Subscription) — Trigger provisioning/deprovisioning via [`provisioning.py`](qalcuity/qalcuity/provisioning.py)
* `has_permission` (ERPNext) — Company-based isolation via [`erpnext_hooks.py`](qalcuity/qalcuity/erpnext_hooks.py)

### DocType Relationships
```text
Qalcuity Tenant ──→ Customer (ERPNext)
Qalcuity Subscription ──→ Qalcuity Tenant
Qalcuity Payment ──→ Qalcuity Subscription
Qalcuity Plan ──→ Qalcuity Subscription
```

### Scheduler Hooks
* Daily subscription expiry check
* Subscription enforcement (ERPNext access block)
* Backup automation
* Provisioning retry for failed attempts

### API Integration
* Qalcuity API endpoints memanggil Frappe API secara internal
* Permission checks menggunakan Portal User → Customer mapping
* Tenant isolation diterapkan di semua API endpoints

### Key Principle
```text
Custom App (Qalcuity) ──uses──→ Frappe Framework API
                                      │
                                      ▼
                                ERPNext Core Engine
                                      │
                                      ▼
                                Business Data
```

> Qalcuity memanfaatkan ERPNext sebagai business engine. Semua integrasi dilakukan melalui mekanisme resmi Frappe (hooks, API, ORM). Tidak ada hardcoding atau bypass.

---

## Implementation Status

> Last Updated: 2026-08-27

| Feature | Status | Notes |
|---------|--------|-------|
| Custom Frappe App | ✅ Done | [`qalcuity/`](qalcuity/) directory with full structure |
| Environment Config | ✅ Done | `.env`, `.env.example`, `.env.production` |
| Qalcuity Settings | ✅ Done | Single DocType for global config, `get_settings()` returns dict |
| Qalcuity Plan | ✅ Done | 4 default plans with features (Starter, Professional, Enterprise, Trial) |
| Plan Feature (Child Table) | ✅ Done | Child table for plan feature details |
| Qalcuity Subscription | ✅ Done | Status transitions, auto-expire scheduler, `tenant` link field via patch |
| Qalcuity Payment | ✅ Done | Manual payment with proof upload, submit/approve/reject APIs, email notifications |
| Qalcuity Tenant | ✅ Done | Tenant isolation model, auto-generated ID (`TENANT-{YYYYMMDD}-{####}`) |
| Qalcuity Audit Log | ✅ Done | Track semua aksi sensitif (payment, subscription, user actions) |
| Qalcuity Subscription Log | ✅ Done | Riwayat perubahan subscription (timeline-based) |
| Qalcuity Backup | ✅ Done | Backup automation dengan scheduler dan retention policy |
| Workspace/Navigation | ✅ Done | Dashboard with charts, number cards, shortcuts, menu/submenu terpisah |
| Seeder Data | ✅ Done | Auto-load via fixtures (Plans + Settings) |
| Permission Rules | ✅ Done | Portal User lookup untuk ownership check (bukan `customer_name`) |
| CSS Branding | ✅ Done | Light/dark mode support |
| API — Payment | ✅ Done | submit/approve/reject/bulk/bulk-reject payment endpoints |
| API — Customer | ✅ Done | after_customer_insert hook |
| API — Profile | ✅ Done | get_profile, update_profile, change_password |
| API — Account Status | ✅ Done | get_account_status (subscription, tenant, payment summary) |
| API — Dashboard | ✅ Done | get_dashboard_data (subscription, tenant, payment data) |
| API — Admin | ✅ Done | approve/reject/bulk operations + review stats |
| API — Audit | ✅ Done | log_action, get_audit_logs, get_my_audit_logs |
| API — Subscription History | ✅ Done | create_subscription_log, get_subscription_history |
| API — Backup | ✅ Done | trigger_backup, get_backup_status, get_backup_list, download/delete |
| API — Plans | ✅ Done | get_active_plans (public) |
| API v1 Versioned | ✅ Done | 20 endpoints dengan auth, rate limiting, standard response format |
| Scheduler | ✅ Done | Daily subscription expiry check + backup automation |
| Patch — Tenant Link | ✅ Done | [`add_tenant_to_subscription`](qalcuity/qalcuity/patches/add_tenant_to_subscription.py) |
| Email Notifications | ✅ Done | Approval, rejection, expiry warning, grace period, backup notification |
| Customer Registration Page | ✅ Done | `/register` web page + API registration endpoint |
| Customer Profile Page | ✅ Done | `/profile` — Edit profil dan ganti password |
| Account Status Page | ✅ Done | `/account-status` — Detail status langganan dan pembayaran |
| Custom Login Page | ✅ Done | Qalcuity-branded login dengan "Lupa password?" dan "Daftar" |
| Dashboard Page | ✅ Done | `/dashboard` — Customer dashboard dengan subscription info |
| Multi-tenant Isolation | ✅ Done | Row-level isolation via permission hooks |
| Plan Selection & Payment | ✅ Done | `/pricing`, `/checkout`, `/my-payments` web pages |
| Subscription Auto-Create | ✅ Done | Payment approved → subscription active (otomatis) |
| Subscription History UI | ✅ Done | `/subscription-history` — Timeline riwayat perubahan langganan |
| Superadmin Review Queue | ✅ Done | `/admin-reviews` web page + admin API |
| Subscription Enforcement | ✅ Done | Grace period 7 hari + ERPNext access block |
| Plan Limits Enforcement | ✅ Done | Enforce max_users, max_storage via before_insert hooks |
| Audit Log System | ✅ Done | DocType-based audit trail + doc_event hooks |
| Backup Automation | ✅ Done | Database + files backup, retention policy, scheduler |
| Multi Bank Accounts | ✅ Done | 4 bank accounts (BRI, JAGO, BTN, BSI) via child table |
| Payment Mode Toggle | ✅ Done | Manual Transfer / Xendit / Hybrid configuration |
| Superadmin Email Notification | ✅ Done | Email ke superadmin saat ada payment baru |
| In-app Notification (Bell Icon) | ✅ Done | Qalcuity Notification DocType + bell icon component |
| WhatsApp Confirmation | ✅ Done | Link wa.me setelah payment submit |
| Tenant Provisioning | ✅ Done | ERP environment provisioning ([`provisioning.py`](qalcuity/qalcuity/provisioning.py)) — Company, Workspace, Roles, Isolation |
| Grace Period Status | ✅ Done | Status `Grace Period` terpisah dengan state color di DocType |
| Registration Rate Limiting | ✅ Done | Max 5 registrasi per jam per IP |
| Password Validation | ✅ Done | Standardized: min 8 chars + letter + number (server & client) |
| Reusable Navigation | ✅ Done | [`navigation.html`](qalcuity/qalcuity/templates/includes/navigation.html) — shared header bar |
| Responsive Mobile UI | ✅ Done | Hamburger menu, responsive grid/forms/tables, touch-friendly |
| Hooks.py Sync | ✅ Done | Inner hooks synced: website_context, fixtures, retry_failed_provisioning |
| Branding Fixes | ✅ Done | "ERPNext" → "ERP" di user-facing text, desk branding hide rules |
| Website Branding Patch | ✅ Done | Auto-set Website Settings (favicon, splash, app_logo) via patch |
| Two-Factor Authentication (2FA) | ✅ Done | TOTP-based 2FA (RFC 6238), setup/enable/disable, backup codes, QR code |
| Session Management | ✅ Done | Active sessions list, force logout, user-agent parsing |
| System Health Monitoring | ✅ Done | System, application, activity stats + health checks (admin) |
| ERP Module Config per Plan | ✅ Done | Module access controls per plan tier (plan_modules field) |
| API Documentation | ✅ Done | Comprehensive API_DOCUMENTATION.md with all endpoints |
| Plan Upgrade/Downgrade Flow | ✅ Done | Customer bisa upgrade/downgrade plan dengan prorated billing |
| Custom Reports | ✅ Done | Revenue, MRR, Churn Rate, Plan Distribution reports |
| API Key Management | ✅ Done | Create, list, revoke API keys + auth middleware |
| Login Audit Trail | ✅ Done | Track semua login attempts (success/failure) |
| Subscription Renewal Automation | ✅ Done | Auto-renewal reminder & renewal flow |
| Data Export (CSV) | ✅ Done | Export payments, subscriptions, customers ke CSV |
| Upload Security Audit | ✅ Done | File type validation, size limits, malware check |
| Input Validation Audit | ✅ Done | Server-side sanitasi semua user input |

### Implemented DocTypes

| DocType | Type | Purpose | Status |
|---------|------|---------|--------|
| Qalcuity Settings | Single | Global configuration (company name, branding, bank details) | ✅ Done |
| Qalcuity Plan | Standard | Subscription plans (name, price, billing period, limits) | ✅ Done |
| Plan Feature | Child | Features included in each plan | ✅ Done |
| Qalcuity Subscription | Standard | Customer subscription lifecycle (PENDING → ACTIVE → EXPIRED) | ✅ Done |
| Qalcuity Payment | Standard | Manual payment records with proof upload | ✅ Done |
| Qalcuity Tenant | Standard | Tenant isolation and environment tracking + provisioning fields | ✅ Done |
| Qalcuity Audit Log | Standard | Audit trail untuk semua aksi sensitif (`AL-{YYYYMMDD}-{####}`) | ✅ Done |
| Qalcuity Subscription Log | Standard | Riwayat perubahan subscription (timeline) (`SL-{YYYYMMDD}-{####}`) | ✅ Done |
| Qalcuity Backup | Standard | Backup records dengan status tracking (`BACKUP-{YYYYMMDD}-{####}`) | ✅ Done |
| Qalcuity Bank Account | Child | Multiple bank accounts per settings (`BANK-{####}`) | ✅ Done |
| Qalcuity Notification | Standard | In-app notifications (`NOTIF-{YYYYMMDD}-{####}`) | ✅ Done |
| Qalcuity Provisioning Log | Standard | ERP provisioning event tracking (`PROV-{YYYYMMDD}-{####}`) | ✅ Done |
| Qalcuity Plan Change | Standard | Plan upgrade/downgrade history (`PC-{YYYYMMDD}-{####}`) | ✅ Done |
| Qalcuity Api Key | Standard | API key management for external integrations (`KEY-{YYYYMMDD}-{####}`) | ✅ Done |
| Qalcuity Login Log | Standard | Login audit trail — success/failure tracking (`LOG-{YYYYMMDD}-{####}`) | ✅ Done |

### Implemented API Endpoints

#### Core API (Frappe whitelisted)

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `api/payment.py::submit_payment` | POST | Customer submits payment proof | ✅ Done |
| `api/payment.py::approve_payment` | POST | Superadmin approves payment | ✅ Done |
| `api/payment.py::reject_payment` | POST | Superadmin rejects payment with reason | ✅ Done |
| `api/payment.py::get_payment_status` | GET | Get payment status and details | ✅ Done |
| `api/payment.py::get_my_payments` | GET | Get payments for current user (Customer) | ✅ Done |
| `api/payment.py::bulk_approve_payments` | POST | Bulk approve multiple payments (batch rollback) | ✅ Done |
| `api/payment.py::bulk_reject_payments` | POST | Bulk reject multiple payments with reason | ✅ Done |
| `api/payment.py::get_pending_reviews` | GET | Get pending payment reviews for Superadmin | ✅ Done |
| `api/customer.py::after_customer_insert` | Hook | Auto-create tenant on customer registration | ✅ Done |
| `api/customer.py::register_customer` | POST | Customer self-registration (name, email, password) | ✅ Done |
| `api/settings.py::get_settings` | GET | Get Qalcuity Settings (cached, returns dict) | ✅ Done |
| `api/profile.py::get_profile` | GET | Get customer profile data | ✅ Done |
| `api/profile.py::update_profile` | POST | Update customer profile | ✅ Done |
| `api/profile.py::change_password` | POST | Change customer password | ✅ Done |
| `api/account_status.py::get_account_status` | GET | Get subscription, tenant, payment summary | ✅ Done |
| `api/dashboard.py::get_dashboard_data` | GET | Get dashboard data (subscription, tenant, payments) | ✅ Done |
| `api/admin.py::get_pending_payments` | GET | Get pending payment reviews for admin | ✅ Done |
| `api/admin.py::approve_payment` | POST | Approve payment (admin) | ✅ Done |
| `api/admin.py::reject_payment` | POST | Reject payment with reason (admin) | ✅ Done |
| `api/admin.py::bulk_approve_payments` | POST | Bulk approve payments (admin) | ✅ Done |
| `api/admin.py::bulk_reject_payments` | POST | Bulk reject payments (admin) | ✅ Done |
| `api/admin.py::get_review_stats` | GET | Get review statistics (admin) | ✅ Done |
| `api/plans.py::get_active_plans` | GET | Get active plans (public, allow_guest) | ✅ Done |
| `api/audit.py::log_action` | Internal | Create audit log entry | ✅ Done |
| `api/audit.py::get_audit_logs` | GET | Get audit logs (admin only) | ✅ Done |
| `api/audit.py::get_my_audit_logs` | GET | Get user's own audit logs | ✅ Done |
| `api/subscription_history.py::create_subscription_log` | Internal | Create subscription history entry | ✅ Done |
| `api/subscription_history.py::get_subscription_history` | GET | Get subscription history (admin) | ✅ Done |
| `api/subscription_history.py::get_my_subscription_history` | GET | Get user's subscription history | ✅ Done |
| `api/backup_api.py::trigger_backup` | POST | Manual trigger backup (admin) | ✅ Done |
| `api/backup_api.py::get_backup_status` | GET | Get latest backup status (admin) | ✅ Done |
| `api/backup_api.py::get_backup_list` | GET | Get paginated backup list (admin) | ✅ Done |
| `api/backup_api.py::download_backup` | GET | Download backup file (admin) | ✅ Done |
| `api/backup_api.py::delete_backup` | POST | Delete specific backup (admin) | ✅ Done |
| `api/backup_api.py::get_backup_stats` | GET | Get backup statistics (admin) | ✅ Done |
| `api/backup_api.py::trigger_cleanup` | POST | Manual cleanup old backups (admin) | ✅ Done |
| `api/two_factor.py::get_2fa_status` | GET | Get 2FA status for current user | ✅ Done |
| `api/two_factor.py::setup_2fa` | POST | Generate 2FA secret and QR code URL | ✅ Done |
| `api/two_factor.py::enable_2fa` | POST | Enable 2FA after code verification | ✅ Done |
| `api/two_factor.py::disable_2fa` | POST | Disable 2FA with password confirmation | ✅ Done |
| `api/two_factor.py::regenerate_backup_codes` | POST | Regenerate 2FA backup codes | ✅ Done |
| `api/two_factor.py::pre_login_check` | POST | Pre-login 2FA validation | ✅ Done |
| `api/two_factor.py::verify_2fa_login` | POST | Verify 2FA code during login | ✅ Done |
| `api/session_api.py::get_active_sessions` | GET | Get active sessions with device info | ✅ Done |
| `api/session_api.py::force_logout_session` | POST | Force logout specific session | ✅ Done |
| `api/session_api.py::force_logout_all_sessions` | POST | Force logout all other sessions | ✅ Done |
| `api/health_api.py::get_system_health` | GET | Get comprehensive system health (admin) | ✅ Done |
| `api/admin_dashboard.py::get_admin_dashboard_data` | GET | Get admin dashboard with revenue/customer/subscription stats | ✅ Done |
| `api/plans.py::submit_payment_with_subscription` | POST | Submit payment and create subscription | ✅ Done |
| `api/plans.py::get_plan_by_name` | GET | Get specific plan by name (public) | ✅ Done |
| `api/plan_change.py::change_plan` | POST | Change plan (upgrade/downgrade) with prorated billing | ✅ Done |
| `api/plan_change.py::get_plan_changes` | GET | Get plan change history (admin) | ✅ Done |
| `api/plan_change.py::get_my_plan_changes` | GET | Get user's plan change history | ✅ Done |
| `api/reports.py::get_revenue_report` | GET | Get revenue report (admin) | ✅ Done |
| `api/reports.py::get_mrr_report` | GET | Get Monthly Recurring Revenue report (admin) | ✅ Done |
| `api/reports.py::get_churn_report` | GET | Get churn rate report (admin) | ✅ Done |
| `api/reports.py::get_plan_distribution` | GET | Get plan distribution report (admin) | ✅ Done |
| `api/reports.py::get_export_data` | GET | Export data (payments, subscriptions, customers) as CSV | ✅ Done |
| `api/api_key_api.py::create_api_key` | POST | Create new API key | ✅ Done |
| `api/api_key_api.py::list_api_keys` | GET | List user's API keys | ✅ Done |
| `api/api_key_api.py::revoke_api_key` | POST | Revoke an API key | ✅ Done |
| `api/api_key_api.py::validate_api_key` | Internal | Validate API key (auth middleware) | ✅ Done |
| `api/login_log.py::get_login_logs` | GET | Get login audit trail (admin) | ✅ Done |
| `api/login_log.py::get_my_login_logs` | GET | Get user's own login logs | ✅ Done |
| `api/renewal.py::check_renewals` | Internal | Auto-check and trigger renewal reminders | ✅ Done |
| `api/renewal.py::renew_subscription` | POST | Renew subscription | ✅ Done |
| `api/renewal.py::get_renewal_status` | GET | Get renewal status for current subscription | ✅ Done |

#### Notification API

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `api/notification.py::get_my_notifications` | GET | Get user notifications | ✅ Done |
| `api/notification.py::get_unread_count` | GET | Get unread notification count | ✅ Done |
| `api/notification.py::mark_as_read` | POST | Mark notification as read | ✅ Done |
| `api/notification.py::mark_all_as_read` | POST | Mark all notifications as read | ✅ Done |
| `api/notification.py::create_notification` | Internal | Create notification entry | ✅ Done |

#### API v1 (Versioned — [`api/v1/`](qalcuity/qalcuity/api/v1/))

| Endpoint | Method | Auth | Purpose | Status |
|----------|--------|------|---------|--------|
| `api/v1/endpoints.py::get_plans` | GET | Public | Get active plans | ✅ Done |
| `api/v1/endpoints.py::register` | POST | Public | Customer registration | ✅ Done |
| `api/v1/endpoints.py::get_settings` | GET | Public | Get global settings | ✅ Done |
| `api/v1/endpoints.py::submit_payment` | POST | Customer | Submit payment proof | ✅ Done |
| `api/v1/endpoints.py::get_my_payments` | GET | Customer | Get customer payments | ✅ Done |
| `api/v1/endpoints.py::get_payment_status` | GET | Customer | Get payment status | ✅ Done |
| `api/v1/endpoints.py::get_profile` | GET | Customer | Get customer profile | ✅ Done |
| `api/v1/endpoints.py::update_profile` | POST | Customer | Update customer profile | ✅ Done |
| `api/v1/endpoints.py::get_dashboard` | GET | Customer | Get dashboard data | ✅ Done |
| `api/v1/endpoints.py::get_account_status` | GET | Customer | Get account status | ✅ Done |
| `api/v1/endpoints.py::get_my_subscription_history` | GET | Customer | Get subscription history | ✅ Done |
| `api/v1/endpoints.py::get_my_audit_logs` | GET | Customer | Get user audit logs | ✅ Done |
| `api/v1/endpoints.py::get_user_info` | GET | Authenticated | Get current user info | ✅ Done |
| `api/v1/endpoints.py::get_pending_reviews` | GET | Admin | Get pending reviews | ✅ Done |
| `api/v1/endpoints.py::approve_payment` | POST | Admin | Approve payment | ✅ Done |
| `api/v1/endpoints.py::reject_payment` | POST | Admin | Reject payment | ✅ Done |
| `api/v1/endpoints.py::bulk_approve_payments` | POST | Admin | Bulk approve | ✅ Done |
| `api/v1/endpoints.py::bulk_reject_payments` | POST | Admin | Bulk reject | ✅ Done |
| `api/v1/endpoints.py::get_audit_logs` | GET | Admin | Get all audit logs | ✅ Done |
| `api/v1/endpoints.py::get_all_subscription_history` | GET | Admin | Get all subscription history | ✅ Done |
| `api/v1/endpoints.py::get_user_info` | GET | Authenticated | Get current user info | ✅ Done |

### Implemented Web Pages

| Page | Route | Purpose | Status |
|------|-------|---------|--------|
| Registration | `/register` | Customer self-registration page | ✅ Done |
| Pricing | `/pricing` | Plan listing & selection page | ✅ Done |
| Checkout | `/checkout` | Payment submission page (multi bank + proof upload + WhatsApp) | ✅ Done |
| My Payments | `/my-payments` | Customer payment history page | ✅ Done |
| Admin Reviews | `/admin-reviews` | Superadmin payment review queue | ✅ Done |
| Dashboard | `/dashboard` | Customer dashboard dengan subscription info | ✅ Done |
| Profile | `/profile` | Edit profil dan ganti password | ✅ Done |
| Account Status | `/account-status` | Detail status langganan dan pembayaran | ✅ Done |
| Subscription History | `/subscription-history` | Timeline riwayat perubahan langganan | ✅ Done |
| Admin Dashboard | `/admin-dashboard` | Superadmin dashboard dengan revenue, customer, subscription stats | ✅ Done |
| Verify Email | `/verify-email` | Email verification page (HMAC-SHA256 token) | ✅ Done |
| Forgot Password | `/forgot-password` | Request password reset via email | ✅ Done |
| Reset Password | `/reset-password` | Reset password via token | ✅ Done |
| 2FA Setup | `/2fa-setup` | Two-factor authentication setup page | ✅ Done |
| 2FA Verify | `/2fa-verify` | 2FA verification during login | ✅ Done |
| Sessions | `/sessions` | Active sessions management page | ✅ Done |
| Admin Health | `/admin-health` | System health monitoring dashboard | ✅ Done |
| Plan Change | `/plan-change` | Upgrade/downgrade plan page | ✅ Done |
| Reports | `/reports` | Custom SaaS reports (revenue, MRR, churn, plan distribution) | ✅ Done |
| API Keys | `/api-keys` | API key management page | ✅ Done |
| Login Logs | `/login-logs` | Login audit trail page | ✅ Done |
| Data Export | `/data-export` | Export data ke CSV | ✅ Done |
| Subscription Renewal | `/renewal` | Subscription renewal page | ✅ Done |
| Admin Reports | `/admin-reports` | Superadmin reports dashboard | ✅ Done |

### Implemented Patches

| Patch | Purpose | Status |
|-------|---------|--------|
| `add_tenant_to_subscription` | Menambahkan field `tenant` (Link) ke Qalcuity Subscription | ✅ Done |
| `seed_bank_accounts` | Seed 4 bank accounts default (BRI, JAGO, BTN, BSI) ke Qalcuity Settings | ✅ Done |
| `seed_erp_user_role` | Seed "Qalcuity ERP User" role for tenant users | ✅ Done |
| `set_website_branding` | Set Website Settings branding (favicon, splash_image, app_logo) ke Qalcuity | ✅ Done |

### Implemented Security Features (Sprint 10 Updates)

| Feature | Status | Notes |
|---------|--------|-------|
| Upload Security | ✅ Done | File type whitelist, size limits (5MB), content-type validation |
| Input Validation | ✅ Done | Server-side sanitasi untuk semua user input (XSS, SQL injection prevention) |
| API Key Authentication | ✅ Done | API key generation, validation, middleware auth |
| Login Audit Trail | ✅ Done | Track semua login attempts dengan IP, user-agent, timestamp |

### Implemented Email Notifications

| Notification | Trigger | Status |
|-------------|---------|--------|
| Approval email | Saat payment di-approve | ✅ Done |
| Rejection email | Saat payment di-reject | ✅ Done |
| Expiry warning | Saat subscription akan expired (daily scheduler) | ✅ Done |
| Subscription activated | Saat payment approved & subscription active | ✅ Done |
| Grace period warning | Saat memasuki grace period (7 hari setelah expired) | ✅ Done |

---

# 1. SaaS Core

## 1.1 Customer Account

### Implemented

* `after_customer_insert` hook — Auto-creates [`Qalcuity Tenant`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_tenant/qalcuity_tenant.py) when new customer is created via [`api/customer.py`](qalcuity/qalcuity/api/customer.py)
* Customer registration page (`/register`) — Form with name, email, password, confirm password
* API `register_customer()` — Validates unique email, creates Frappe User + Customer + Portal User + Tenant otomatis
* After registration, customer langsung bisa login dan melihat pricing page
* **Registration rate limiting** — Max 5 registrasi per jam per IP ([`registration.py`](qalcuity/qalcuity/api/registration.py))
* **Password validation** — Minimum 8 characters + letter + number, diterapkan di server dan client

### MVP

* ~~Customer registration~~ ✅
* ~~Login~~ ✅ — Enhanced with Qalcuity branding via [`login.py`](qalcuity/qalcuity/login.py)
* ~~Logout~~ ✅
* ~~Password management~~ ✅ — via [`profile.py::change_password()`](qalcuity/qalcuity/api/profile.py)
* ~~Customer profile~~ ✅ — `/profile` page + [`api/profile.py`](qalcuity/qalcuity/api/profile.py)
* ~~Account status~~ ✅ — `/account-status` page + [`api/account_status.py`](qalcuity/qalcuity/api/account_status.py)

### Future

* Email verification
* Password reset automation
* Account security settings
* Login history
* Two-factor authentication

---

# 2. Subscription

## 2.1 Plans

### Implemented

* [`Qalcuity Plan`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_plan/) DocType with fields: plan_name, description, price, billing_period, is_active, max_users, max_storage_gb
* [`Plan Feature`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_plan/) child table for feature list per plan
* 4 default plans seeded via fixtures: Starter (Rp99K), Professional (Rp199K), Enterprise (Rp499K), Trial (Free)
* Plans loaded automatically on app installation via [`fixtures configuration`](qalcuity/hooks.py)
* Pricing page (`/pricing`) — Menampilkan semua active plans dengan harga, fitur, dan tombol "Pilih Plan"
* Plans hanya ditampilkan jika `is_active = 1`

### Specification

Each plan should support configurable:

* name
* description
* price
* billing period
* limits
* included features
* status

Example:

```text
Starter
Rp99.000/month

Business
Rp199.000/month

Professional
Rp399.000/month
```

These are examples only and must remain configurable.

---

## 2.2 Subscription

### Implemented

* [`Qalcuity Subscription`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_subscription/) DocType with full lifecycle management
* Status transitions validated via [`validate_status_transitions()`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_subscription/qalcuity_subscription.py) — enforces allowed state changes
* Auto-expire scheduler via [`tasks.py`](qalcuity/qalcuity/tasks.py) — daily task checks expired subscriptions
* **Subscription Auto-Create** — Saat payment di-approve, subscription otomatis dibuat/di-update ke status ACTIVE
* **Grace Period** — 7 hari setelah expiry date, subscription masuk status GRACE_PERIOD sebelum EXPIRED
* **Subscription Enforcement** — ERPNext access diblokir saat subscription EXPIRED (bukan hanya GRACE_PERIOD)
* Field `tenant` (Link → Qalcuity Tenant) ditambahkan via patch [`add_tenant_to_subscription`](qalcuity/qalcuity/patches/add_tenant_to_subscription.py) untuk kemudahan querying
* Tenant link otomatis diupdate saat subscription di-save via [`update_tenant_link()`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_subscription/qalcuity_subscription.py)
* Permission check menggunakan Portal User lookup untuk ownership validation
* Statuses: `Draft → Pending Payment → Active → Grace Period → Expired/Suspended/Cancelled`

### Specification

Subscription contains at minimum:

* customer
* tenant
* plan
* start date
* expiry date
* status
* price
* billing period
* created timestamp
* updated timestamp

Statuses:

```text
DRAFT
PENDING PAYMENT
ACTIVE
GRACE PERIOD    ← 7 hari setelah expiry
EXPIRED
SUSPENDED
CANCELLED
```

Grace Period Flow:

```text
ACTIVE
   ↓
Expiry Date Reached
   ↓
GRACE PERIOD (7 hari)
   ↓
Akses ERPNext DIBLOKIR
   ↓
Customer masih bisa lihat subscription info
   ↓
7 hari berlalu
   ↓
EXPIRED
   ↓
Akses sepenuhnya dibatasi
```

---

# 3. Manual Payment

### Implemented

* [`Qalcuity Payment`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_payment/) DocType with proof upload support
* Status transitions validated via [`validate_status_transitions()`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_payment/qalcuity_payment.py)
* Email notifications: approval email ([`send_approval_email()`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_payment/qalcuity_payment.py)) dan rejection email ([`send_rejection_email()`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_payment/qalcuity_payment.py))
* Email customer diambil via [`get_customer_email()`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_payment/qalcuity_payment.py) — fallback chain: Customer.email_id → Customer Email → Portal User
* **Superadmin email notification** — [`notify_superadmin_new_payment()`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_payment/qalcuity_payment.py) — Email ke superadmin saat ada payment baru
* **In-app notification** — Bell icon notification untuk superadmin, menggunakan [`Qalcuity Notification`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_notification/) DocType
* **WhatsApp confirmation** — Link wa.me dikirim ke customer setelah payment submit
* **Multi bank accounts** — Checkout page menampilkan multiple bank accounts dari [`Qalcuity Settings`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_settings/qalcuity_settings.py) (child table [`Qalcuity Bank Account`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_bank_account/))
* **Payment mode toggle** — Konfigurasi mode pembayaran: Manual Transfer / Xendit / Hybrid
* Permission check menggunakan Portal User lookup untuk ownership validation
* Batch rollback logic di `bulk_approve_payments()` dan `bulk_reject_payments()` — jika error, semua approval/rejection dalam batch di-rollback
* **Checkout page** (`/checkout`) — Form payment submission dengan plan info, multi bank detail, proof upload, WhatsApp button
* **My Payments page** (`/my-payments`) — Customer payment history dengan status badges
* **Admin Reviews page** (`/admin-reviews`) — Superadmin payment review queue dengan bulk approve/reject
* API endpoints in [`api/payment.py`](qalcuity/qalcuity/api/payment.py):
  * `submit_payment()` — Customer submits payment with proof
  * `approve_payment()` — Superadmin approves, activates subscription
  * `reject_payment()` — Superadmin rejects with mandatory reason
  * `get_payment_status()` — Retrieve payment status and details
  * `get_my_payments()` — Customer retrieves their own payment history
  * `bulk_approve_payments()` — Bulk approve with batch rollback on error
  * `bulk_reject_payments()` — Bulk reject with batch rollback on error
  * `get_pending_reviews()` — Get pending payment reviews for admin queue
* Payment proof stored securely via Frappe file handling

### Specification

Initial payment system uses manual bank transfer.

## Customer Flow

```text
Select Plan (dari /pricing)
   ↓
Redirect ke /checkout
   ↓
Isi form: amount, payment date, bank, notes
   ↓
Upload bukti transfer
   ↓
Submit → Payment PENDING
   ↓
Lihat status di /my-payments
```

## Superadmin Flow

```text
Buka /admin-reviews
   ↓
Lihat daftar payment PENDING
   ↓
Klik payment untuk detail
   ↓
Lihat bukti transfer
   ↓
Approve / Reject
```

Approval:

```text
Payment APPROVED
      ↓
Subscription otomatis ACTIVE (auto-create)
      ↓
Expiry calculated (billing period)
      ↓
Email notification ke customer
```

Rejection:

```text
Payment REJECTED
      ↓
Reason shown
      ↓
Email notification ke customer
      ↓
Customer can resubmit
```

---

# 4. Payment Proof

Customer must be able to:

* upload payment proof
* see submission status
* see rejection reason
* resubmit when allowed

Superadmin must be able to:

* view proof
* verify amount
* verify payment date
* approve
* reject
* provide rejection reason
* bulk approve/reject

Security requirement:

Payment proof must not be publicly accessible.

---

# 4a. Bank Account Configuration

### Implemented

* [`Qalcuity Bank Account`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_bank_account/) child table DocType — Multiple bank accounts dalam satu Settings
* 4 default bank accounts seeded via patch [`seed_bank_accounts`](qalcuity/qalcuity/patches/seed_bank_accounts.py):
  * **BRI** — Bank Rakyat Indonesia
  * **JAGO** — Bank Jago
  * **BTN** — Bank Tabungan Negara
  * **BSI** — Bank Syariah Indonesia
* Bank accounts ditampilkan di checkout page sebagai pilihan transfer
* Setiap bank account memiliki: bank_name, account_number, account_name, is_active
* Seed data otomatis di-load saat app installation

### Specification

Bank account configuration should support:

* multiple bank accounts
* bank name
* account number
* account holder name
* active/inactive status
* display order

---

# 4b. Payment Mode

### Implemented

* **Payment mode toggle** di [`Qalcuity Settings`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_settings/qalcuity_settings.py) — Konfigurasi mode pembayaran:
  * **Manual Transfer** — Customer transfer bank manual, upload bukti
  * **Xendit** — Payment gateway (belum diimplementasi, hanya config ready)
  * **Hybrid** — Keduanya tersedia
* Validation di [`qalcuity_settings.py`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_settings/qalcuity_settings.py) — Mode harus valid
* Dynamic help text di [`qalcuity_settings.js`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_settings/qalcuity_settings.js) — Field hints berubah sesuai mode

### Specification

Payment mode determines which payment methods are available to customers:

```text
MANUAL_TRANSFER
   → Customer sees bank accounts
   → Customer uploads proof
   → Superadmin reviews

XENDIT
   → Customer redirected to Xendit payment page
   → Auto-verification

HYBRID
   → Both options available
   → Customer chooses
```

---

# 4c. Superadmin Notifications

### Implemented

* **Email notification** — [`notify_superadmin_new_payment()`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_payment/qalcuity_payment.py) — Email ke superadmin saat ada payment baru
* **In-app notification** — [`Qalcuity Notification`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_notification/) DocType — Bell icon notification
* **Bell icon component** — [`qalcuity.js`](qalcuity/qalcuity/qalcuity/qalcuity.js) — Menampilkan jumlah unread notifications di navbar
* **Notification API** — [`api/notification.py`](qalcuity/qalcuity/api/notification.py) — CRUD notifications
* **Configuration** di Qalcuity Settings:
  * `notify_superadmin_on_payment` — Toggle email notification
  * `superadmin_notification_email` — Target email address

### Notification Types

```text
NEW_PAYMENT        → Saat customer submit payment
PAYMENT_APPROVED   → Saat payment di-approve
PAYMENT_REJECTED   → Saat payment di-reject
SUBSCRIPTION_EXPIRED → Saat subscription expired
```

### Bell Icon Flow

```text
Customer submits payment
   ↓
Superadmin receives:
   ├── Email notification (if enabled)
   └── In-app notification (bell icon)
         ↓
   Unread count shown on bell icon
         ↓
   Click bell → view notifications
         ↓
   Mark as read / mark all as read
```

---

# 4d. WhatsApp Confirmation

### Implemented

* **WhatsApp link** — [`checkout.py`](qalcuity/qalcuity/templates/pages/checkout.py) — Generate wa.me URL setelah payment submit
* **WhatsApp button** — [`checkout.html`](qalcuity/qalcuity/templates/pages/checkout.html) — Tombol "Konfirmasi via WhatsApp" di checkout success
* **Configuration** di Qalcuity Settings:
  * `whatsapp_number` — Nomor WhatsApp (format: 62xxx)
  * `whatsapp_message_template` — Template pesan (dengan {amount}, {plan}, {name} placeholders)

### Flow

```text
Customer submit payment
   ↓
Payment PENDING
   ↓
Checkout page shows:
   ├── Payment status
   ├── WhatsApp confirmation button (wa.me link)
   └── Link to /my-payments
```

---

# 5. Superadmin

### Implemented

* **Admin Reviews page** (`/admin-reviews`) — Payment review queue dengan:
  * Daftar payment PENDING
  * Detail payment dengan bukti transfer
  * Single approve/reject
  * Bulk approve/reject
  * Filter by status
* **API `get_pending_reviews()`** — Mendapatkan daftar payment yang perlu di-review

Superadmin dashboard should provide:

```text
Dashboard
├── Customers
├── Tenants
├── Plans
├── Subscriptions
├── Payments
├── Payment Verification ← /admin-reviews
├── System Status
├── Logs
└── Settings
```

Superadmin actions:

* activate customer
* suspend customer
* reactivate customer
* approve payment
* reject payment
* bulk approve/reject payment
* extend subscription
* change plan where permitted
* inspect tenant
* inspect subscription history

---

# 6. Tenant Management

### Implemented

* [`Qalcuity Tenant`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_tenant/) DocType with fields: customer, tenant_name, tenant_id, status, plan, site_name
* Auto-created on customer registration via [`api/customer.py`](qalcuity/qalcuity/api/customer.py)
* Tenant ID auto-generation: `TENANT-{YYYYMMDD}-{####}` via [`generate_tenant_id()`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_tenant/qalcuity_tenant.py) — sequential per hari
* Status values: `ACTIVE`, `SUSPENDED`, `TERMINATED`
* Linked to customer and subscription for isolation tracking
* Actions: suspend, reactivate, terminate
* Permission check menggunakan Portal User lookup untuk ownership validation
* Validasi unique tenant per customer (hanya 1 active tenant per customer)
* **Multi-tenant Isolation** — Row-level isolation via permission hooks, customer hanya bisa lihat data miliknya sendiri

### Specification

Tenant represents an isolated customer ERP environment.

Tenant data:

* tenant ID
* customer
* site/environment
* status
* plan
* created date
* subscription status

Tenant lifecycle:

```text
CREATED
   ↓
PROVISIONING
   ↓
ACTIVE
   ↓
SUSPENDED / EXPIRED
   ↓
ACTIVE
```

Possible final architecture must be validated before implementation.

---

# 7. Tenant Isolation

### Implemented

* **Row-level isolation via permission hooks** — Setiap DocType yang memiliki field `customer` akan otomatis di-filter berdasarkan customer yang sedang login
* Customer hanya bisa melihat, membuat, dan mengubah data milik sendiri
* Superadmin bisa melihat semua data (tidak terfilter)
* Isolation diterapkan di semua SaaS DocTypes: Subscription, Payment, Tenant
* Permission hooks mengecek Portal User → Customer mapping untuk ownership validation

### Specification

Tenant isolation is a critical requirement.

Never allow:

```text
Tenant A
   ↓
Tenant B data
```

or any cross-tenant access.

### Isolation Strategy

```text
Customer Login
   ↓
Portal User lookup → Customer ID
   ↓
Permission hook filter → hanya data dengan customer_id yang cocok
   ↓
Result: isolated view
```

Implementation approach:

* Frappe permission hooks for row-level filtering
* `has_permission` hook on each DocType
* `get_list` hook for query filtering
* Server-side validation on all write operations

---

# 8. Subscription Enforcement

### Implemented

* **Grace period 7 hari** — Setelah expiry date, subscription masuk status GRACE_PERIOD selama 7 hari
* **ERPNext access block** — Saat subscription EXPIRED (setelah grace period), akses ERPNext diblokir
* **Scheduler enforcement** — Daily task mengecek status semua subscriptions dan mengupdate status berdasarkan expiry date
* **Warning notifications** — Email warning saat memasuki grace period

### Enforcement Flow

```text
Subscription ACTIVE
   ↓
Expiry Date Reached
   ↓
Status → GRACE_PERIOD
   ↓
Email warning dikirim
   ↓
ERPNext access: DIBLOKIR (read-only mode)
   ↓
7 hari berlalu
   ↓
Status → EXPIRED
   ↓
Akses sepenuhnya dibatasi
   ↓
Customer harus bayar untuk reaktivasi
```

### Configuration

* Grace period: 7 hari (default, configurable via Qalcuity Settings)
* Block behavior: ERPNext modules diblokir, hanya halaman subscription info yang bisa diakses
* Reactivation: Payment baru → approval → subscription active kembali

---

# 9. Automated Provisioning

### Implemented

* [`provisioning.py`](qalcuity/qalcuity/provisioning.py) — Core provisioning module:
  * `provision_tenant()` — Create Company + assign ERP User role + setup workspace
  * `deprovision_tenant()` — Revoke ERP access on subscription expire/suspend
  * `reactivate_tenant()` — Re-provision on subscription reactivation
  * `retry_failed_provisioning()` — Retry mechanism for failed provisioning attempts
* [`Qalcuity Provisioning Log`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_provisioning_log/) — DocType for tracking provisioning events (`PROV-{YYYYMMDD}-{####}`)
* [`ERP User role`](qalcuity/qalcuity/roles/erp_user.json) — Custom "Qalcuity ERP User" role for tenant users
* ERP Customer workspace — Selling, Buying, Stock, Accounts, CRM modules
* [`Qalcuity Tenant`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_tenant/) provisioning fields — `erp_provisioning_status`, `erp_company`, `last_provisioning_attempt`, `provisioning_error`
* Subscription [`on_update`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_subscription/qalcuity_subscription.py) hooks — Trigger provisioning/deprovisioning automatically
* Dashboard ERP Access Banner — 3 states: Ready, Provisioning, Failed
* Company-based isolation — [`erpnext_hooks.py`](qalcuity/qalcuity/erpnext_hooks.py) for ERPNext permission query conditions
* Dual-layer isolation — [`isolation.py`](qalcuity/qalcuity/isolation.py) Customer + Company filtering

### Provisioning Flow

```text
Payment Approved
       ↓
Subscription ACTIVE (auto-create)
       ↓
on_update hook → provision_tenant()
       ↓
Company created + ERP User role assigned
       ↓
ERP Customer workspace available
       ↓
Dashboard shows ERP Access Banner (Ready)
       ↓
Customer can access ERP environment
```

### Deprovisioning Flow

```text
Subscription EXPIRED/SUSPENDED
       ↓
on_update hook → deprovision_tenant()
       ↓
ERP access revoked
       ↓
Tenant can be re-provisioned on reactivation
```

### Provisioning Status Values

```text
NOT_PROVISIONED  — Tenant created but no ERP environment yet
PROVISIONING     — ERP environment being set up
PROVISIONED      — ERP environment ready for use
FAILED           — Provisioning failed, retry available
DEPROVISIONED    — ERP access revoked (subscription expired/suspended)
```

Do not sacrifice reliability merely to achieve automation.

---

# 10. ERP Modules

Initial ERP capabilities should leverage ERPNext.

Potential modules:

* Accounting
* CRM
* Sales
* Purchase
* Inventory
* HR
* Projects
* Customer management
* Supplier management
* Products
* Quotations
* Sales orders
* Purchase orders
* Invoices
* Payments
* Reports

Only expose modules that are appropriate for the selected plan.

### Implemented — ERP Module Config per Plan

* **Plan modules field** — `plan_modules` field di Qalcuity Plan DocType
* **Module access controls** — Setiap plan bisa configure modul ERP mana yang diakses
* **Provisioning integration** — Module config diterapkan saat ERP provisioning
* **Default modules** — Accounting, CRM, Selling, Buying, Stock, HR, Projects, Manufacturing

---

# 11. Qalcuity Custom Features

Qalcuity must eventually differentiate itself from standard ERPNext.

Potential custom layer:

```text
Qalcuity Intelligence
├── Business Dashboard
├── KPI
├── Sales Analytics
├── Financial Insights
├── Automation
├── Notifications
└── AI-assisted features
```

Custom features should be developed based on actual customer needs.

Do not add features merely to make the product appear larger.

---

# 12. Qalcuity UI/UX

### Implemented

* Workspace dashboard at [`qalcuity/workspace/`](qalcuity/qalcuity/qalcuity/workspace/qalcuity/qalcuity.json) with charts, number cards, and shortcuts
* CSS branding with light/dark mode support
* Navigation integrated into Frappe workspace sidebar — menu utama dan sub menu terpisah dengan ikon profesional
* [`Qalcuity Settings`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_settings/qalcuity_settings.py) Single DocType for global branding config
* [`get_settings()`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_settings/qalcuity_settings.py) dengan caching, mengembalikan dict (bukan doc object)
* **Registration page** (`/register`) — Form registrasi dengan Qalcuity branding
* **Pricing page** (`/pricing`) — Plan cards dengan harga, fitur, tombol "Pilih Plan"
* **Checkout page** (`/checkout`) — Payment form dengan bank detail, proof upload
* **My Payments page** (`/my-payments`) — Payment history dengan status badges
* **Admin Reviews page** (`/admin-reviews`) — Admin review queue dengan bulk actions
* **Dashboard page** (`/dashboard`) — Customer dashboard dengan subscription info, expiry warnings, quick actions
* **Profile page** (`/profile`) — Edit profil dan ganti password
* **Account Status page** (`/account-status`) — Detail status langganan, tenant, pembayaran, usage bars
* **Subscription History page** (`/subscription-history`) — Timeline riwayat perubahan langganan
* **Custom Login** — Qalcuity-branded login dengan "Lupa password?" dan "Daftar" links
* **Reusable navigation template** ([`navigation.html`](qalcuity/qalcuity/templates/includes/navigation.html)) — Shared header bar untuk semua halaman dengan hamburger menu mobile
* **Desk branding** — ERPNext footer, sidebar, navbar di-hide untuk user experience yang bersih ([`qalcuity.js`](qalcuity/qalcuity/public/js/qalcuity.js))
* **"ERPNext" → "ERP" branding** — Semua user-facing text menggunakan "ERP" bukan "ERPNext"
* **Admin Dashboard page** (`/admin-dashboard`) — Revenue, customer, subscription, payment, tenant stats
* **2FA Setup page** (`/2fa-setup`) — Two-factor authentication setup
* **2FA Verify page** (`/2fa-verify`) — 2FA verification during login
* **Sessions page** (`/sessions`) — Active sessions management
* **Admin Health page** (`/admin-health`) — System health monitoring dashboard

### Specification

Qalcuity should have its own product identity.

Required:

* Qalcuity branding
* custom login experience
* custom navigation
* custom dashboard
* custom terminology where appropriate
* custom landing pages
* SaaS account area
* ~~subscription page~~ ✅
* ~~payment page~~ ✅
* ~~payment history~~ ✅
* customer settings

ERPNext default UI may remain underneath where practical, but the customer-facing experience should progressively become Qalcuity.

---

# 13. API

### Implemented — Core API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/method/qalcuity.qalcuity.api.customer.register_customer` | POST | Customer self-registration |
| `/api/method/qalcuity.qalcuity.api.payment.submit_payment` | POST | Submit payment proof |
| `/api/method/qalcuity.qalcuity.api.payment.approve_payment` | POST | Approve payment (admin) |
| `/api/method/qalcuity.qalcuity.api.payment.reject_payment` | POST | Reject payment (admin) |
| `/api/method/qalcuity.qalcuity.api.payment.get_payment_status` | GET | Get payment status |
| `/api/method/qalcuity.qalcuity.api.payment.get_my_payments` | GET | Get customer payments |
| `/api/method/qalcuity.qalcuity.api.payment.get_pending_reviews` | GET | Get pending admin reviews |
| `/api/method/qalcuity.qalcuity.api.payment.bulk_approve_payments` | POST | Bulk approve (admin) |
| `/api/method/qalcuity.qalcuity.api.payment.bulk_reject_payments` | POST | Bulk reject (admin) |
| `/api/method/qalcuity.qalcuity.api.settings.get_settings` | GET | Get global settings |
| `/api/method/qalcuity.qalcuity.api.profile.get_profile` | GET | Get customer profile |
| `/api/method/qalcuity.qalcuity.api.profile.update_profile` | POST | Update customer profile |
| `/api/method/qalcuity.qalcuity.api.profile.change_password` | POST | Change password |
| `/api/method/qalcuity.qalcuity.api.account_status.get_account_status` | GET | Get account status |
| `/api/method/qalcuity.qalcuity.api.dashboard.get_dashboard_data` | GET | Get dashboard data |
| `/api/method/qalcuity.qalcuity.api.admin.approve_payment` | POST | Approve payment (admin) |
| `/api/method/qalcuity.qalcuity.api.admin.reject_payment` | POST | Reject payment (admin) |
| `/api/method/qalcuity.qalcuity.api.admin.get_pending_payments` | GET | Get pending reviews (admin) |
| `/api/method/qalcuity.qalcuity.api.plans.get_active_plans` | GET | Get active plans (public) |
| `/api/method/qalcuity.qalcuity.api.audit.get_audit_logs` | GET | Get audit logs (admin) |
| `/api/method/qalcuity.qalcuity.api.audit.get_my_audit_logs` | GET | Get user audit logs |
| `/api/method/qalcuity.qalcuity.api.subscription_history.get_subscription_history` | GET | Get subscription history (admin) |
| `/api/method/qalcuity.qalcuity.api.subscription_history.get_my_subscription_history` | GET | Get user subscription history |
| `/api/method/qalcuity.qalcuity.api.backup_api.trigger_backup` | POST | Trigger backup (admin) |
| `/api/method/qalcuity.qalcuity.api.backup_api.get_backup_status` | GET | Get backup status (admin) |

### Implemented — API v1 (Versioned)

```text
/api/v1/ → qalcuity.qalcuity.api.v1.endpoints.*
```

24 endpoints dengan auth check, rate limiting (100 req/min/user), dan standard response format.
Lihat [`api/v1/`](qalcuity/qalcuity/api/v1/) untuk detail lengkap.

Potential resources:

```text
/auth
/customers
/companies
/products
/suppliers
/invoices
/orders
/payments
/inventory
/reports
/subscriptions
/tenants
```

Requirements:

* authentication
* authorization
* validation
* tenant isolation
* consistent response format
* error handling
* versioning
* documentation

External consumers should depend on Qalcuity API contracts rather than internal ERPNext implementation details.

---

# 14. Notifications

### Implemented — Email Notifications

* Approval email — saat payment di-approve
* Rejection email — saat payment di-reject
* Expiry warning — saat subscription akan expired (daily scheduler)
* Subscription activated — saat payment approved & subscription active
* Grace period warning — saat memasuki grace period
* **Superadmin email** — saat ada payment baru ([`notify_superadmin_new_payment()`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_payment/qalcuity_payment.py))

### Implemented — In-app Notifications

* [`Qalcuity Notification`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_notification/) DocType — `NOTIF-{YYYYMMDD}-{####}`
* Bell icon component di navbar ([`qalcuity.js`](qalcuity/qalcuity/qalcuity/qalcuity.js))
* Notification API ([`api/notification.py`](qalcuity/qalcuity/api/notification.py)):
  * `get_my_notifications()` — Get user notifications
  * `get_unread_count()` — Get unread count
  * `mark_as_read()` — Mark single notification as read
  * `mark_all_as_read()` — Mark all as read
* Unread count injected via [`boot.py`](qalcuity/qalcuity/boot.py)
* Notification CSS styling ([`qalcuity.css`](qalcuity/qalcuity/qalcuity/qalcuity.css))

Potential automated notifications:

* ~~payment received~~ ✅
* ~~payment approved~~ ✅
* ~~payment rejected~~ ✅
* ~~subscription activated~~ ✅
* ~~subscription expiring~~ ✅
* subscription expired
* ~~grace period warning~~ ✅
* ~~superadmin payment notification~~ ✅
* tenant provisioning completed

Notifications should eventually be automated.

---

# 15. Audit Log

### Implemented

* [`Qalcuity Audit Log`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_audit_log/) DocType — Naming: `AL-{YYYYMMDD}-{####}`
* [`api/audit.py`](qalcuity/qalcuity/api/audit.py) — `log_action()`, `get_audit_logs()` (admin), `get_my_audit_logs()` (customer)
* Doc event hooks — Auto-log saat Payment dan Subscription di-update
* IP address tracking — Setiap log entry mencatat IP address
* Filterable by: user, action, doc_type, date range

### Recorded Events

* payment_submit, payment_approve, payment_reject
* subscription_create, subscription_activate, subscription_expire, subscription_suspend
* user_register, profile_update
* backup_trigger, backup_complete, backup_failed

### Specification

Important SaaS operations must be auditable.

Record events such as:

* payment approval
* payment rejection
* subscription changes
* plan changes
* tenant creation
* tenant suspension
* tenant reactivation
* administrator actions

---

# 16. Backup

### Implemented

* [`Qalcuity Backup`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_backup/) DocType — Naming: `BACKUP-{YYYYMMDD}-{####}`
* [`backup.py`](qalcuity/qalcuity/backup.py) — `run_backup()`, `cleanup_old_backups()`, `get_backup_status()`, `get_backup_list()`
* [`api/backup_api.py`](qalcuity/qalcuity/api/backup_api.py) — 7 API endpoints (trigger, status, list, download, delete, stats, cleanup)
* Scheduler task — `run_scheduled_backup()` di [`tasks.py`](qalcuity/qalcuity/tasks.py)
* Database backup — via `mysqldump` dengan gzip compression
* File backup — `tar -czf` untuk private/files + public/files
* Retention policy — Default 30 hari (configurable via env `QALCUITY_BACKUP_RETENTION_DAYS`)
* Email notification — Saat backup selesai/gagal

### Backup Locations

* Database: `sites/{site}/private/backups/backup_{site}_{YYYYMMDD}_{HHMMSS}.sql.gz`
* Files: `sites/{site}/private/backups/backup_{site}_{YYYYMMDD}_{HHMMSS}_files.tar.gz`

### Specification

Required production capability:

* ~~scheduled database backup~~ ✅
* ~~file backup~~ ✅
* ~~retention policy~~ ✅
* restore procedure (manual via bench)
* ~~backup automation~~ ✅

Future:

* automated backup verification
* backup health monitoring
* customer-level restore strategy

---

# 17. Integrations

### Partially Implemented

* **WhatsApp** — Confirmation link (wa.me) setelah payment submit, configurable via Qalcuity Settings
* **Banking** — Multi bank accounts (BRI, JAGO, BTN, BSI) via child table DocType

Future possibilities:

* payment gateway (Xendit — config ready, implementation pending)
* email (sudah diimplementasi untuk notifications)
* marketplace
* e-commerce
* external accounting systems
* Qalcuity API integrations

Do not implement these until the core SaaS is stable.

---

# 18. Feature Status

Use these statuses:

```text
PLANNED
IN_PROGRESS
TESTING
COMPLETED
DEPRECATED
```

Never mark a feature COMPLETED unless its complete flow has been tested.
