# ROADMAP.md

# Qalcuity ERP — Development Roadmap

## Product Direction

Qalcuity adalah produk SaaS ERP yang menggunakan Frappe/ERPNext sebagai core ERP engine. **ERPNext tidak dimodifikasi** — seluruh customisasi dilakukan di custom app [`qalcuity/`](qalcuity/).

### Arsitektur

```
                    QALCUITY ERP
                         │
                         ▼
              ┌─────────────────────┐
              │   ERPNext / Frappe  │  ← Core Engine (upstream, tidak dimodifikasi)
              └──────────┬──────────┘
                         │
                Qalcuity Custom App  ← Kode custom kita
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Branding      SaaS Layer      New Features
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                  qalcuity.com
```

### Deployment Strategy (Docker + AAPanel)

VPS menggunakan **Docker (frappe_docker)** untuk menjalankan Frappe/ERPNext dan **AAPanel** untuk management layer.

```text
LOCAL DEVELOPMENT (VS Code)
       │
       │ Git push
       ▼
GitHub Qalcuity (wahyudedik/customerpnext)
       │
       │ git pull di VPS
       ▼
┌─────────────────────────┐
│       VPS Production     │
│                          │
│    ┌──────────────────┐  │
│    │   AAPanel        │  │
│    │  (management)    │  │
│    │  - domain        │  │
│    │  - SSL           │  │
│    │  - nginx         │  │
│    │  - database admin│  │
│    └──────────────────┘  │
│                          │
│    ┌──────────────────┐  │
│    │   Docker         │  │
│    │  (runtime)       │  │
│    │  ┌────────────┐  │  │
│    │  │ Frappe     │  │  │
│    │  │ ERPNext    │  │  │
│    │  │ Qalcuity   │  │  │
│    │  │ MariaDB    │  │  │
│    │  │ Redis      │  │  │
│    │  │ Workers    │  │  │
│    │  │ Scheduler  │  │  │
│    │  └────────────┘  │  │
│    └──────────────────┘  │
└──────────┬───────────────┘
           │
           ▼
     qalcuity.com
```

**Constraint Penting:**
* **Local Machine = Code Only** — tidak ada Docker, tidak ada testing lokal
* **VPS = Testing + Production** — Docker menjalankan aplikasi, AAPanel manage infrastruktur
* **Repository** = [`wahyudedik/customerpnext`](https://github.com/wahyudedik/customerpnext) — HANYA berisi kode custom Qalcuity

### Upstream Update Strategy

* **Update ERPNext:** `pip install --upgrade erpnext` atau `bench update`
* **Update Frappe:** `bench update --pull`
* **Update Qalcuity:** `git pull origin main` → `bench migrate` → `bench build` → `docker compose up -d --force-recreate frontend`
* **TIDAK ADA FORK** — ERPNext adalah dependency upstream

The objective is to start lean, validate the SaaS model, obtain paying customers, and gradually replace generic ERPNext experiences with Qalcuity-specific functionality.

---

# PHASE 0 — Architecture & Validation

Status: ✅ DONE

> Last Updated: 2026-08-25

## Goals

Understand the ERPNext/Frappe architecture before heavy customization.

### Tasks

* [x] Validate supported ERPNext/Frappe versions — v17.0.0-dev confirmed
* [x] Validate deployment requirements — Environment config created
* [x] Validate VPS resource requirements
* [x] Validate AAPanel compatibility
* [x] Determine tenant architecture — Isolation via Qalcuity Tenant DocType + permission hooks
* [x] Determine backup architecture — Basic config in `.env`
* [x] Determine Git workflow — Repository structure established
* [x] Determine development/staging/production strategy
* [x] Determine how Qalcuity Custom App will be separated from ERPNext core — Separate `qalcuity/` app directory
* [ ] Document upgrade strategy

### Exit Criteria

Architecture is documented and there is a clear answer to:

> How can Qalcuity run multiple customers safely without cross-tenant data access?

**Answer:** Row-level isolation via permission hooks — customer hanya bisa akses data miliknya sendiri.

---

# PHASE 1 — Base ERP Environment

Status: 🔄 IN PROGRESS

> Last Updated: 2026-08-24

## Goals

Get a clean ERPNext environment running reliably di VPS (Docker + AAPanel).

### Infrastructure Plan

VPS managed dengan **Docker (frappe_docker)** untuk runtime dan **AAPanel** untuk management:

| Component | Technology | Management |
|-----------|------------|------------|
| Server Panel | AAPanel | Port 15252 |
| Runtime | Docker (frappe_docker) | Docker Compose |
| Framework | Frappe Framework | dalam Docker container |
| ERP | ERPNext | dalam Docker container |
| Custom App | Qalcuity | dalam Docker container (git pull + bench migrate) |
| Database | MariaDB | dalam Docker container, managed via AAPanel |
| Cache | Redis | dalam Docker container |
| Web Server | Nginx | via AAPanel (reverse proxy ke Docker) |
| Domain | qalcuity.com | via AAPanel |

### Tasks

* [x] Prepare VPS
* [x] Configure required server dependencies
* [x] Install Frappe
* [x] Install ERPNext
* [x] Configure database (MariaDB via AAPanel)
* [x] Configure Redis/background workers (via AAPanel)
* [x] Configure scheduler
* [ ] Configure reverse proxy (Nginx via AAPanel)
* [ ] Configure HTTPS (SSL via AAPanel)
* [ ] Configure domain (qalcuity.com via AAPanel)
* [x] Verify ERP functionality
* [x] Create initial Git repository

### Development Workflow

```text
Local (VS Code) → Code/Edit only (TANPA Docker)
       │
       │ git push
       ▼
GitHub (wahyudedik/customerpnext)
       │
       │ git pull di VPS
       ▼
VPS (Docker + AAPanel) → bench migrate → bench build → docker compose up -d → Testing di browser
```

### Exit Criteria

ERPNext works reliably in a controlled environment on VPS (Docker + AAPanel).

---

# PHASE 2 — Qalcuity Custom App

Status: ✅ DONE

> Last Updated: 2026-08-25

## Goals

Create the Qalcuity-specific application layer.

### Tasks

* [x] Create Qalcuity custom Frappe app — [`qalcuity/`](qalcuity/) directory
* [x] Establish app structure — Full Frappe app structure with modules
* [x] Add Qalcuity branding — CSS with light/dark mode, workspace dashboard
* [x] Create custom settings — [`Qalcuity Settings`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_settings/qalcuity_settings.py) Single DocType
* [x] Create custom roles — Defined in JSON, pending Frappe role setup
* [x] Create SaaS-related DocTypes — Plan, Subscription, Payment, Tenant (6 DocTypes total)
* [x] Establish naming conventions — Auto-naming in DocType JSON
* [x] Establish permission conventions — Permission rules in DocType JSON
* [x] Establish API conventions — [`api/customer.py`](qalcuity/qalcuity/api/customer.py), [`api/payment.py`](qalcuity/qalcuity/api/payment.py)
* [x] Bug fixes dan improvements — Portal User permission, email notifications, batch rollback, patches

### Exit Criteria

Qalcuity-specific code exists independently from ERPNext core.

---

### Sprint 1 — Foundation ✅ DONE

> Completed: 2026-08-22

- [x] Custom Frappe App `qalcuity` created at [`qalcuity/`](qalcuity/)
- [x] 6 DocTypes implemented (Settings, Plan, Plan Feature, Subscription, Payment, Tenant)
- [x] Environment configuration (`.env`, `.env.example`, `.env.production`)
- [x] Workspace with dashboard, charts, number cards, shortcuts
- [x] Seeder data: 4 Plans (Starter, Professional, Enterprise, Trial) + Settings
- [x] Permission rules defined (System Manager, Superadmin, Admin, Guest, Customer)
- [x] CSS branding with dark mode support
- [x] API: Payment submit/approve/reject/get, Customer hook
- [x] Scheduler: Daily subscription expiry check via [`tasks.py`](qalcuity/qalcuity/tasks.py)

---

### Sprint 2 — Bug Fixes & Improvements ✅ DONE

> Completed: 2026-08-24

**Bug Fixes:**
- [x] Permission check di Payment/Subscription/Tenant sekarang menggunakan Portal User lookup (bukan `customer_name`)
- [x] Hapus `override_whitelisted_methods` redundan dari [`hooks.py`](qalcuity/hooks.py)
- [x] Fix `bulk_approve_payments` rollback logic — batch rollback saat error
- [x] Hapus `seed_initial_data()` redundan dari [`tasks.py`](qalcuity/qalcuity/tasks.py)
- [x] Fix `get_settings()` — sekarang return dict (bukan doc object) dengan caching

**Improvements:**
- [x] Tambah `tenant` link field ke Subscription via patch [`add_tenant_to_subscription`](qalcuity/qalcuity/patches/add_tenant_to_subscription.py)
- [x] Tambah rejection email notification di [`Qalcuity Payment`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_payment/qalcuity_payment.py)
- [x] Tambah approval email notification di [`Qalcuity Payment`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_payment/qalcuity_payment.py)
- [x] Tenant ID auto-generation format: `TENANT-{YYYYMMDD}-{####}`
- [x] Workspace navigation diperbaiki — menu utama/sub menu terpisah, ikon profesional
- [x] Bulk reject payments API ([`bulk_reject_payments()`](qalcuity/qalcuity/api/payment.py))
- [x] Customer payment history API ([`get_my_payments()`](qalcuity/qalcuity/api/payment.py))

---

### Sprint 3 — SaaS Flow ✅ DONE

> Completed: 2026-08-24

- [x] Customer Registration Page (`/register`) — Form registrasi dengan validasi
- [x] Registration API (`register_customer()`) — Buat User + Customer + Portal User + Tenant
- [x] Multi-tenant Isolation — Row-level permission hooks ([`isolation.py`](qalcuity/qalcuity/isolation.py))
- [x] Pricing Page (`/pricing`) — Plan listing & selection
- [x] Checkout Page (`/checkout`) — Payment submission dengan proof upload
- [x] My Payments Page (`/my-payments`) — Customer payment history
- [x] Subscription Auto-Create — Payment approved → subscription active (otomatis)
- [x] Grace Period 7 hari — Subscription enforcement setelah expiry
- [x] Subscription Enforcement — ERPNext access block saat expired
- [x] Admin Reviews Page (`/admin-reviews`) — Superadmin payment review queue
- [x] Pending Reviews API (`get_pending_reviews()`) — Daftar payment untuk admin
- [x] Subscription enforcement scheduler — Daily check via [`tasks.py`](qalcuity/qalcuity/tasks.py)

---

### Sprint 4 — Features & Polish ✅ DONE

> Completed: 2026-08-24

- [x] Customer Profile Page (`/profile`) — Edit profil dan ganti password
- [x] Account Status Page (`/account-status`) — Detail status langganan dan pembayaran
- [x] Custom Login Page — Qalcuity-branded login dengan "Lupa password?" dan "Daftar"
- [x] Audit Log — DocType + API untuk track semua aksi sensitif
- [x] Plan Limits Enforcement — Enforce max_users, max_storage via [`enforcement.py`](qalcuity/qalcuity/enforcement.py)
- [x] Subscription History UI (`/subscription-history`) — Timeline riwayat perubahan langganan
- [x] API v1 Versioned — 20 endpoints dengan auth, rate limiting, standard response format
- [x] Backup Automation — Database + files backup dengan scheduler dan retention policy

---

### Sprint 5 — Payment & Notifications ✅ DONE

> Completed: 2026-08-24

- [x] Multi bank accounts (BRI, JAGO, BTN, BSI) — [`Qalcuity Bank Account`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_bank_account/) child table
- [x] Payment mode toggle (Manual/Xendit/Hybrid) — [`Qalcuity Settings`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_settings/qalcuity_settings.py) configuration
- [x] Checkout page redesign — Multiple bank accounts display + redesigned bank section
- [x] WhatsApp confirmation link — wa.me button setelah payment submit
- [x] Superadmin email notification — Email ke superadmin saat ada payment baru
- [x] Qalcuity Notification DocType — In-app notifications (`NOTIF-{YYYYMMDD}-{####}`)
- [x] Bell icon notification component — [`qalcuity.js`](qalcuity/qalcuity/qalcuity/qalcuity.js) + [`qalcuity.css`](qalcuity/qalcuity/qalcuity/qalcuity.css)
- [x] Notification API — [`api/notification.py`](qalcuity/qalcuity/api/notification.py) (get_my_notifications, get_unread_count, mark_as_read, mark_all_as_read)
- [x] .env update — Xendit, WhatsApp, notification variables

---

# PHASE 3 — SaaS Account System

Status: ✅ DONE

> Last Updated: 2026-08-24

## Goals

Allow customers to register and manage their SaaS account.

### Tasks

* [x] Customer registration page (`/register`) — Form registrasi dengan validasi
* [x] Customer registration API (`register_customer()`) — Buat User + Customer + Portal User + Tenant
* [x] Customer login (Frappe default) — Enhanced with Qalcuity branding
* [x] Customer logout (Frappe default)
* [x] Customer profile — `/profile` page + [`api/profile.py`](qalcuity/qalcuity/api/profile.py)
* [x] Account status page — `/account-status` page + [`api/account_status.py`](qalcuity/qalcuity/api/account_status.py)
* [x] Customer dashboard redirect → `/pricing` setelah login

### Exit Criteria

A customer can register, login, and understand their SaaS account status.

---

# PHASE 4 — Subscription System

Status: ✅ DONE

> Last Updated: 2026-08-24

### Tasks

* [x] Plan management — [`Qalcuity Plan`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_plan/) DocType
* [x] Subscription DocType — [`Qalcuity Subscription`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_subscription/)
* [x] Subscription lifecycle — status transitions validated
* [x] Start date — set on activation
* [x] Expiry date — calculated from billing period
* [x] Subscription status — Draft, Pending Payment, Active, Grace Period, Expired, Suspended, Cancelled
* [x] Subscription auto-create — Payment approved → subscription active (otomatis)
* [x] Grace period — 7 hari setelah expiry date
* [x] Subscription enforcement — ERPNext access block saat expired
* [x] Expiration handling — daily scheduler via [`tasks.py`](qalcuity/qalcuity/tasks.py)
* [x] Tenant link field — via patch [`add_tenant_to_subscription`](qalcuity/qalcuity/patches/add_tenant_to_subscription.py)
* [x] Plan limits — [`enforcement.py`](qalcuity/qalcuity/enforcement.py) enforce max_users, max_storage
* [x] Subscription history (UI) — `/subscription-history` page + [`api/subscription_history.py`](qalcuity/qalcuity/api/subscription_history.py)

### Exit Criteria

The system can correctly determine whether a customer is active, in grace period, or expired — and enforce access accordingly.

---

# PHASE 5 — Manual Payment System

Status: ✅ DONE

> Last Updated: 2026-08-24

## MVP Payment Method

Manual bank transfer.

### Tasks

* [x] Bank account settings — via [`Qalcuity Settings`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_settings/qalcuity_settings.py)
* [x] Payment submission — [`submit_payment()`](qalcuity/qalcuity/api/payment.py)
* [x] Payment proof upload — via Frappe file handling
* [x] Payment status — Pending → Approved/Rejected
* [x] Superadmin payment queue — bulk approve/reject APIs
* [x] Payment approval — [`approve_payment()`](qalcuity/qalcuity/api/payment.py) + email notification
* [x] Payment rejection — [`reject_payment()`](qalcuity/qalcuity/api/payment.py) + email notification + rejection reason
* [x] Rejection reason — mandatory field
* [x] Subscription activation after approval — via [`activate_subscription()`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_payment/qalcuity_payment.py) (auto-create)
* [x] Payment history — [`get_my_payments()`](qalcuity/qalcuity/api/payment.py)
* [x] Batch rollback logic — error dalam batch menyebabkan rollback semua
* [x] Checkout page (`/checkout`) — Payment form dengan proof upload
* [x] My Payments page (`/my-payments`) — Customer payment history
* [x] Admin Reviews page (`/admin-reviews`) — Superadmin review queue
* [x] Pending reviews API (`get_pending_reviews()`) — Daftar payment untuk admin
* [x] Multi bank accounts (BRI, JAGO, BTN, BSI) — [`Qalcuity Bank Account`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_bank_account/) child table + seed data
* [x] Payment mode toggle (Manual/Xendit/Hybrid) — [`Qalcuity Settings`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_settings/qalcuity_settings.py) configuration
* [x] Superadmin email notification — [`notify_superadmin_new_payment()`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_payment/qalcuity_payment.py)
* [x] WhatsApp confirmation link — wa.me button di checkout page
* [x] In-app notification — [`Qalcuity Notification`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_notification/) DocType + bell icon
* [x] Notification API — [`api/notification.py`](qalcuity/qalcuity/api/notification.py)

### Exit Criteria

Complete flow works:

```text
Plan (dari /pricing)
 ↓
Checkout (/checkout)
 ↓
Upload Proof
 ↓
Pending
 ↓
Superadmin (/admin-reviews)
 ↓
Approve
 ↓
Subscription Active (auto-create)
 ↓
Email Notification
```

---

# PHASE 6 — Tenant Management

Status: ✅ DONE

> Last Updated: 2026-08-24

### Tasks

* [x] Tenant model — [`Qalcuity Tenant`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_tenant/qalcuity_tenant.py)
* [x] Tenant creation — auto-created via [`after_customer_insert`](qalcuity/qalcuity/api/customer.py)
* [x] Tenant status — Active, Suspended, Terminated
* [x] Tenant-to-customer relationship — Link field
* [x] Tenant-to-subscription relationship — Link field (via patch)
* [x] Tenant isolation testing — Row-level isolation via permission hooks
* [x] Multi-tenant isolation — Customer hanya bisa akses data milik sendiri
* [x] Suspension — [`suspend()`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_tenant/qalcuity_tenant.py)
* [x] Reactivation — [`reactivate()`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_tenant/qalcuity_tenant.py)
* [x] Expiration handling — auto-suspend via scheduler
* [x] Tenant ID auto-generation — `TENANT-{YYYYMMDD}-{####}`
* [x] Terminate action — [`terminate()`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_tenant/qalcuity_tenant.py)

### Exit Criteria

Customers are isolated and subscription status controls tenant access correctly.

---

# PHASE 7 — Provisioning Automation

Status: ✅ DONE

> Last Updated: 2026-08-25

## Goal

Reduce manual Superadmin work.

### Tasks

* [x] Automated tenant creation — [`provision_tenant()`](qalcuity/qalcuity/provisioning.py) creates Company + assigns roles
* [x] Automated initial configuration — Company setup with Selling, Buying, Stock, Accounts, CRM modules
* [x] Automated user creation — ERP User role assignment to tenant users
* [x] Automated plan configuration — Workspace with appropriate modules
* [x] Automated access information — Dashboard ERP Access Banner (3 states: Ready/Provisioning/Failed)
* [x] Provisioning status — [`erp_provisioning_status`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_tenant/) field on Tenant
* [x] Provisioning failure handling — [`provisioning_error`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_tenant/) field + error logging
* [x] Retry mechanism — [`retry_failed_provisioning()`](qalcuity/qalcuity/provisioning.py)
* [x] Deprovisioning — [`deprovision_tenant()`](qalcuity/qalcuity/provisioning.py) on subscription expire/suspend
* [x] Reactivation provisioning — [`reactivate_tenant()`](qalcuity/qalcuity/provisioning.py) on subscription reactivation
* [x] Provisioning logging — [`Qalcuity Provisioning Log`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_provisioning_log/) DocType
* [x] ERP User role — [`erp_user.json`](qalcuity/qalcuity/roles/erp_user.json)
* [x] ERP Customer workspace — Selling, Buying, Stock, Accounts, CRM modules
* [x] Company-based isolation — [`erpnext_hooks.py`](qalcuity/qalcuity/erpnext_hooks.py) permission query conditions
* [x] Dual-layer isolation — [`isolation.py`](qalcuity/qalcuity/isolation.py) Customer + Company filtering
* [x] Subscription integration — on_update triggers provisioning/deprovisioning
* [x] seed_erp_user_role patch — [`patches/seed_erp_user_role.py`](qalcuity/qalcuity/patches/seed_erp_user_role.py)

### Provisioning Flow

```text
Payment Approved
      ↓
Subscription ACTIVE (auto-create)
      ↓
on_update hook triggers provision_tenant()
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
on_update hook triggers deprovision_tenant()
      ↓
ERP access revoked
      ↓
Tenant can be re-provisioned on reactivation
```

---

# PHASE 8 — Qalcuity UI/UX

Status: 🔄 IN PROGRESS

> Last Updated: 2026-08-25

### Tasks

* [x] Qalcuity login (custom login page) — [`login.py`](qalcuity/qalcuity/login.py) dengan branding
* [x] Qalcuity branding (CSS light/dark)
* [x] SaaS dashboard (customer-facing) — `/dashboard` page
* [x] Pricing page (`/pricing`) — Plan listing
* [x] Checkout page (`/checkout`) — Payment submission
* [x] My Payments page (`/my-payments`) — Payment history
* [x] Admin Reviews page (`/admin-reviews`) — Admin review queue
* [x] Registration page (`/register`) — Customer registration
* [x] Customer profile page (`/profile`) — Edit profil + ganti password
* [x] Account status page (`/account-status`) — Detail status langganan
* [x] Subscription history page (`/subscription-history`) — Timeline riwayat
* [x] Bell icon notification component — [`qalcuity.js`](qalcuity/qalcuity/qalcuity/qalcuity.js)
* [x] Notification CSS styling — [`qalcuity.css`](qalcuity/qalcuity/qalcuity/qalcuity.css)
* [ ] Superadmin dashboard (custom)
* [ ] Navigation redesign
* [ ] Responsive behavior
* [x] Light mode (CSS branding)
* [x] Dark mode (CSS branding)
* [x] Empty states
* [x] Loading states
* [x] Error states

### Goal

Customer experience should feel like:

> Qalcuity ERP

not:

> a generic ERPNext installation.

---

# PHASE 9 — Qalcuity API

Status: PLANNED

### Tasks

* [x] API architecture (versioned: `/api/v1/`) — [`api/v1/`](qalcuity/qalcuity/api/v1/) module
* [x] Authentication — [`auth.py`](qalcuity/qalcuity/api/v1/auth.py) dengan role-based access
* [x] API keys/tokens where appropriate — `check_api_key_authentication()` di auth.py
* [x] `/api/v1/` — Base endpoints implemented via Frappe whitelisted methods
* [x] Customer endpoints (`register_customer`)
* [x] Payment endpoints (`submit/approve/reject/bulk/get-status/get-my-payments/get-pending-reviews`)
* [x] Settings endpoint (`get_settings`)
* [x] Profile endpoints (`get_profile/update_profile/change_password`)
* [x] Account status endpoint (`get_account_status`)
* [x] Dashboard endpoint (`get_dashboard_data`)
* [x] Audit endpoints (`get_audit_logs/get_my_audit_logs`)
* [x] Subscription history endpoints (`get_subscription_history/get_my_subscription_history`)
* [x] Backup endpoints (`trigger_backup/get_backup_status/get_backup_list/download/delete/stats/cleanup`)
* [x] Notification endpoints (`get_my_notifications/get_unread_count/mark_as_read/mark_all_as_read`)
* [x] Product endpoints (`get_active_plans`)
* [ ] Invoice endpoints
* [ ] Sales endpoints
* [ ] Inventory endpoints
* [ ] Report endpoints
* [x] Subscription endpoints (via payment approval auto-create)
* [ ] Tenant endpoints
* [x] API permissions — Role-based auth check (public/customer/admin)
* [x] Rate limiting — 100 req/min/user via `frappe.cache()` sliding window
* [ ] API documentation

### Exit Criteria

External integrations can use Qalcuity APIs without depending directly on ERPNext internals.

---

# PHASE 10 — Qalcuity Differentiation

Status: PLANNED

Only start after the SaaS core works.

Potential features:

* [ ] Business dashboard
* [ ] KPI
* [ ] Sales analytics
* [ ] Financial analytics
* [ ] Automation
* [ ] Notifications
* [ ] AI features
* [ ] Custom reports
* [ ] Industry-specific workflows

Priority should be determined by customer demand.

---

# PHASE 11 — Production Hardening

Status: PLANNED

### Tasks

* [ ] Security audit
* [ ] Permission audit
* [x] Tenant isolation audit — Row-level permission hooks verified
* [x] API security audit — API v1 auth check, rate limiting implemented
* [ ] Upload security audit
* [x] Backup automation — [`backup.py`](qalcuity/qalcuity/backup.py) + scheduler
* [ ] Restore testing
* [ ] Monitoring
* [x] Error logging — Audit log system ([`api/audit.py`](qalcuity/qalcuity/api/audit.py))
* [ ] Deployment procedure (VPS Docker + AAPanel)
* [ ] Rollback procedure
* [ ] Upgrade procedure (ERPNext upstream + Qalcuity custom app)
* [ ] Disaster recovery documentation

### Exit Criteria

The system can safely serve paying customers on VPS (Docker + AAPanel).

---

# PHASE 12 — Commercial Automation

Status: FUTURE

Only after customers validate the product.

### Potential tasks

* [ ] Payment gateway
* [ ] Automatic payment verification
* [ ] Automatic renewal
* [ ] Automatic invoice
* [ ] Automatic subscription extension
* [ ] Automatic suspension
* [ ] Automatic reactivation
* [ ] Email notification
* [ ] WhatsApp notification

Manual payment remains acceptable during early validation.

---

# PHASE 13 — Scale

Status: FUTURE

Only scale after actual usage requires it.

Potential improvements:

* [ ] Resource monitoring
* [ ] Tenant resource limits
* [ ] Worker optimization
* [ ] Database optimization
* [ ] Queue optimization
* [ ] Horizontal scaling
* [ ] Separate services
* [ ] Object storage
* [ ] Advanced backup
* [ ] High availability

Do not introduce infrastructure complexity prematurely.

---

# MVP DEFINITION

Qalcuity MVP is considered commercially viable when:

* [x] Customer can register
* [x] Customer can select a plan
* [x] Customer can see payment instructions
* [x] Customer can upload payment proof
* [x] Superadmin can review payment
* [x] Superadmin can approve/reject payment
* [x] Approved payment activates subscription
* [x] Subscription has an expiry date
* [x] Expired subscription is handled correctly (grace period + access block)
* [x] Customer receives access to their ERP environment (provisioning — [`provisioning.py`](qalcuity/qalcuity/provisioning.py))
* [x] Tenant isolation is verified
* [x] Core ERP functionality works (post-provisioning — Company + Workspace + Roles)
* [x] Qalcuity branding is applied
* [x] Basic backup exists — Database + files backup dengan retention policy
* [ ] Production deployment is reproducible from Git (VPS Docker + AAPanel)

**MVP Progress: 13/15 items completed (87%)**

---

# Business Validation Target

Initial commercial target:

> **Rp1.000.000/month recurring revenue**

Do not optimize for thousands of users initially.

First objective:

```text
1 paying customer
        ↓
3 paying customers
        ↓
5 paying customers
        ↓
10 paying customers
```

The product should validate whether customers are willing to pay before major infrastructure expansion.

---

# Core Rule

Do not confuse:

> "ERPNext is installed"

with:

> "Qalcuity SaaS is working."

The actual product is the complete experience:

```text
Customer
   ↓
Account (✅ /register)
   ↓
Plan (✅ /pricing)
   ↓
Payment (✅ /checkout)
   ↓
Approval (✅ /admin-reviews)
   ↓
Subscription (✅ auto-create + grace period)
   ↓
Tenant (✅ isolation verified)
   ↓
ERP (✅ provisioning — Company, Workspace, Roles)
   ↓
Qalcuity Features
   ↓
Renewal
```

Every part of this lifecycle must eventually become reliable and increasingly automated.
