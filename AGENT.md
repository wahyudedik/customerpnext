# AGENT.md

# Qalcuity ERP — AI Engineering Agent

> **📦 GitHub Repository:** [`wahyudedik/customerpnext`](https://github.com/wahyudedik/customerpnext) · Branch: `main`
> **Last Updated:** 2026-08-26

---

## 1. Project Identity

Qalcuity ERP adalah produk SaaS ERP yang dibangun di atas Frappe Framework dan ERPNext.

**Arsitektur:**

```
                    QALCUITY ERP
                         │
                         ▼
              ┌─────────────────────┐
              │   ERPNext / Frappe  │
              │   CORE ENGINE       │
              └──────────┬──────────┘
                         │
                Qalcuity Custom App
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              △
       Branding      SaaS Layer      New Features
          │              │              │
          └──────────────┼───────────┘
                         ▼
                  qalcuity.com
```

**Penting untuk dipahami:**

- **ERPNext/Frappe** = core ERP engine, di-install sebagai dependency ke Frappe bench. Kita TIDAK memaintain source code ERPNext.
- **Qalcuity Custom App** = kode custom kita, disimpan di repository [`wahyudedik/customerpnext`](https://github.com/wahyudedik/customerpnext). HANYA berisi kode custom Qalcuity.
- **Qalcuity BUKAN fork ERPNext** — kita tidak memaintain source code ERPNext sendiri.
- **Update ERPNext** = `pip install --upgrade erpnext` atau `bench update`, bukan merge dari fork.

Prinsip inti:

> **Gunakan ERPNext/Frappe sebagai fondasi. Bangun Qalcuity sebagai product layer.**

---

### 1a. ERPNext Role — Core Engine

ERPNext/Frappe bertanggung jawab untuk:

- **Accounting** — Jurnal, buku besar, laporan keuangan
- **CRM** — Customer relationship management
- **HR** — Human resources, payroll
- **Inventory** — Stok, gudang, batch tracking
- **Sales** — Quotation, sales order, invoice
- **Purchasing** — Purchase order, supplier management
- **Projects** — Project management, timesheet
- **Database/Business Engine** — ORM, workflow, validation
- **Update/Upstream** — Fitur ERPNext terus berkembang mengikuti release resmi Frappe

Kita TIDAK memodifikasi fitur-fitur ERPNext ini. Kita menggunakannya sebagaimana adanya.

---

### 1b. Qalcuity Role — Custom Layer

Qalcuity custom layer bertanggung jawab untuk:

- **Branding Qalcuity** — Logo, warna, CSS, UI/UX khas Qalcuity
- **Domain qalcuity.com** — Frontend dan portal kustom
- **SaaS Subscription** — Plan, billing, renewal
- **Customer Management** — Registration, profile, account status
- **Manual Payment** — Transfer bank, upload bukti, approval
- **Superadmin** — Payment review, tenant management
- **API Qalcuity** — Endpoints khusus untuk SaaS operation
- **Fitur baru milik Qalcuity** — Business features yang tidak ada di ERPNext
- **Dashboard Qalcuity** — Customer dashboard, admin dashboard
- **Automation SaaS** — Subscription enforcement, provisioning

---

## 2. Product Goals

Qalcuity must eventually provide:

* Multi-customer SaaS operation
* Subscription plans
* Customer registration
* Manual payment workflow
* Payment proof upload
* Superadmin payment approval
* Subscription activation
* Subscription expiration
* Tenant management
* Qalcuity-specific UI/UX
* Qalcuity-specific features
* Qalcuity-specific API
* Automated provisioning where practical
* Automated subscription status handling
* Automated access restrictions for expired subscriptions
* Backup and recovery strategy
* Production deployment from Git

The initial target is a lean MVP.

Do NOT build unnecessary enterprise complexity before the core SaaS flow works.

---

## 3. Engineering Philosophy

Follow these principles:

1. Understand before changing.
2. Change minimally.
3. Reuse existing ERPNext/Frappe capabilities whenever appropriate.
4. Do not unnecessarily modify ERPNext core source code.
5. **JANGAN pernah fork ERPNext** — ERPNext adalah dependency upstream, bukan source yang di-fork.
6. **JANGAN modify ERPNext core source code** — Semua customisasi dilakukan di custom app.
7. **Update ERPNext via `pip install --upgrade erpnext` atau `bench update`**, bukan merge dari fork.
8. **Gunakan hooks, custom app, DocType, API** untuk semua customisasi.
9. Prefer custom Frappe applications/modules over destructive core modifications.
10. Keep Qalcuity-specific logic isolated.
11. Keep the code maintainable and upgradeable.
12. Verify every important flow.
13. Never knowingly leave a broken flow.
14. Never introduce a dependency without understanding why it is required.
15. Prefer open-source/free tooling for the MVP.
16. Avoid paid licenses unless explicitly approved.
17. Do not build features simply because they are technically interesting.
18. Prioritize features that improve customer value or SaaS operation.

---

## 4. Source of Truth

The Git repository is the source of truth for Qalcuity custom code.

Expected conceptual structure:

```text
Repository
│
├── AGENT.md
├── FEATURES.md
├── ROADMAP.md
│
└── Qalcuity Custom App
    ├── SaaS
    ├── Subscription
    ├── Payment
    ├── Tenant
    ├── API
    ├── Custom UI
    └── Business Features
```

Production VPS must not become the primary source of code.

Never make undocumented production-only code changes.

All important changes must eventually exist in Git.

---

## 5. ERPNext/Frappe Customization Rule

Do NOT blindly edit ERPNext core.

Preferred architecture:

```text
Frappe Framework
        │
        ├── ERPNext
        │
        └── Qalcuity Custom App
                ├── SaaS
                ├── Subscription
                ├── Payments
                ├── Tenant Management
                ├── API
                ├── Custom UI
                └── Qalcuity Features
```

If a requirement can be implemented through:

* Custom App
* DocType
* hooks
* server scripts where appropriate
* client scripts where appropriate
* custom API endpoints
* custom pages
* custom reports
* custom permissions
* custom workflows

prefer those approaches over changing ERPNext core.

If core modification is unavoidable, document:

* why it is required
* which file/module is affected
* upgrade impact
* rollback strategy

---

## 6. SaaS Architecture

Qalcuity menambahkan **SaaS layer DI ATAS ERPNext**. ERPNext tetap utuh sebagai core engine. Customisasi hanya dilakukan di custom app, bukan di ERPNext core.

### 3-Area Flow

```text
┌─────────────────────────────────────────────────────────────┐
│                    QALCUITY SaaS LAYER                       │
│                                                              │
│  1. PUBLIC / SaaS Area                                       │
│     - /register (Registration)                               │
│     - /pricing (Choose Plan)                                 │
│     - /checkout (Payment - Manual Transfer)                  │
│     - /my-payments (Payment History)                         │
│     - /dashboard (Customer Dashboard)                        │
│     - /profile (Edit Profile)                                │
│     - /account-status (Subscription Status)                  │
│     - /subscription-history (Subscription Timeline)          │
│                                                              │
│  2. SUPERADMIN Area                                          │
│     - /admin-reviews (Payment Review Queue)                  │
│     - Approve/Reject Payment                                 │
│     - Auto-create Subscription + Tenant provisioning         │
│     - ERP User role assignment                               │
│     - Subscription management (extend, suspend)              │
│                                                              │
│  3. ERP WORKSPACE (Frappe/ERPNext Core)                      │
│     - Full ERP access for active subscribers                 │
│     - Accounting, CRM, HR, Inventory, Sales, Purchasing      │
│     - Company-based isolation per tenant                     │
│     - Blocked for expired subscriptions                      │
└─────────────────────────────────────────────────────────────┘
```

### SaaS Control Layer — Qalcuity Custom App

Responsible for:

* customer accounts
* plans
* subscriptions
* payments
* payment verification
* tenant status
* provisioning
* suspension
* expiration
* superadmin management
* branding & UI/UX
* Qalcuity-specific API
* Qalcuity-specific features

### ERP Layer — ERPNext — TIDAK DIMODIFIKASI

Responsible for business operations:

* accounting
* CRM
* HR
* inventory
* sales
* purchasing
* projects
* other ERP capabilities

Conceptual flow:

```text
Customer
   │
   ▼
Qalcuity SaaS Layer (Custom App)
   │
   ├── Account
   ├── Plan
   ├── Subscription
   ├── Payment
   ├── Tenant
   ├── Branding
   ├── Custom API
   └── Custom Features
   │
   ▼
ERPNext/Frappe (Core Engine — TIDAK DIMODIFIKASI)
   │
   └── Customer's business data
```

---

## 7. Tenant Isolation

Tenant isolation is a critical requirement.

Never allow:

```text
Tenant A
   ↓
Tenant B data
```

or any cross-tenant access.

### Implemented Strategy

Row-level isolation via permission hooks:

```text
Customer Login
   ↓
Portal User lookup → Customer ID
   ↓
Permission hook filter → hanya data dengan customer_id yang cocok
   ↓
Result: isolated view
```

* Customer hanya bisa melihat, membuat, dan mengubah data milik sendiri
* Superadmin bisa melihat semua data (tidak terfilter)
* Isolation diterapkan di semua SaaS DocTypes: Subscription, Payment, Tenant
* Permission hooks mengecek Portal User → Customer mapping untuk ownership validation
* Company-based isolation di ERPNext workspace ([`erpnext_hooks.py`](qalcuity/qalcuity/erpnext_hooks.py))
* Dual-layer isolation ([`isolation.py`](qalcuity/qalcuity/isolation.py))

---

## 8. Subscription Model

Initial payment method:

> Manual bank transfer.

Do NOT implement a payment gateway in the MVP unless explicitly requested.

### Complete User Lifecycle

```text
Register → Choose Plan → Payment (Manual Transfer) → PENDING
→ Superadmin Reviews → APPROVED
→ Subscription Auto-Created (ACTIVE) → Tenant Provisioned
→ ERP User Role Assigned → ERP Access GRANTED
```

### Basic Payment Flow

```text
Customer
   ↓
Choose Plan (dari /pricing)
   ↓
Checkout (/checkout)
   ↓
Transfer Payment
   ↓
Upload Proof
   ↓
PENDING
   ↓
Superadmin Reviews (/admin-reviews)
   ↓
APPROVED
   ↓
Subscription ACTIVE (auto-create)
```

### Rejected Payment

```text
PENDING
   ↓
REJECTED
   ↓
Customer can submit again
```

### Expired Subscription with Grace Period

```text
ACTIVE
   ↓
Expiry Date Reached
   ↓
GRACE PERIOD (7 hari)
   ↓
ERPNext Access DIBLOKIR
   ↓
7 hari berlalu
   ↓
EXPIRED
   ↓
Data preserved, access fully restricted, renewal required
```

### Renewal Flow

```text
EXPIRED → Choose Plan → Payment → PENDING → APPROVED
→ Subscription RENEWED (extended) → ERP Access RESTORED
```

---

## 9. Superadmin

Superadmin is responsible for operational control.

Superadmin must be able to:

* view customers
* view tenants
* view plans
* view subscriptions
* view payment submissions
* inspect payment proof
* approve payment
* reject payment
* bulk approve/reject payment
* activate subscription
* extend subscription
* suspend tenant
* reactivate tenant
* provision tenants
* assign ERP User role
* inspect system status
* inspect important logs

Do not expose Superadmin functions to ordinary customers.

---

## 10. Payment Rules

Every payment submission must have a traceable lifecycle.

Minimum conceptual states:

```text
PENDING
APPROVED
REJECTED
```

Payment records should retain:

* customer
* subscription
* amount
* payment date
* payment method
* proof
* status
* reviewer
* review timestamp
* rejection reason when applicable

Do not silently delete payment records.

---

## 11. API

Qalcuity should have its own API layer.

Do not force external customers to depend directly on internal ERPNext API structures.

Conceptual architecture:

```text
External Client
      ↓
Qalcuity API
      ↓
Qalcuity Service Layer
      ↓
Frappe / ERPNext
```

### Implemented API Endpoints

#### Core API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `register_customer` | POST | Customer self-registration |
| `submit_payment` | POST | Submit payment proof |
| `approve_payment` | POST | Approve payment (admin) |
| `reject_payment` | POST | Reject payment (admin) |
| `get_payment_status` | GET | Get payment status |
| `get_my_payments` | GET | Get customer payments |
| `get_pending_reviews` | GET | Get pending admin reviews |
| `bulk_approve_payments` | POST | Bulk approve (admin) |
| `bulk_reject_payments` | POST | Bulk reject (admin) |
| `get_settings` | GET | Get global settings |
| `get_profile` | GET | Get customer profile |
| `update_profile` | POST | Update customer profile |
| `change_password` | POST | Change customer password |
| `get_account_status` | GET | Get account status (subscription, tenant, payments) |
| `get_dashboard_data` | GET | Get dashboard data |
| `get_audit_logs` | GET | Get audit logs (admin) |
| `get_my_audit_logs` | GET | Get user's own audit logs |
| `get_subscription_history` | GET | Get subscription history (admin) |
| `get_my_subscription_history` | GET | Get user's subscription history |
| `trigger_backup` | POST | Trigger backup (admin) |
| `get_backup_status` | GET | Get backup status (admin) |
| `get_backup_list` | GET | Get backup list (admin) |
| `change_plan` | POST | Change plan (upgrade/downgrade) with prorated billing |
| `get_plan_changes` | GET | Get plan change history (admin) |
| `get_my_plan_changes` | GET | Get user's plan change history |
| `get_revenue_report` | GET | Get revenue report (admin) |
| `get_mrr_report` | GET | Get MRR report (admin) |
| `get_churn_report` | GET | Get churn rate report (admin) |
| `get_plan_distribution` | GET | Get plan distribution report (admin) |
| `get_export_data` | GET | Export data as CSV (admin) |
| `create_api_key` | POST | Create new API key |
| `list_api_keys` | GET | List user's API keys |
| `revoke_api_key` | POST | Revoke an API key |
| `get_login_logs` | GET | Get login audit trail (admin) |
| `get_my_login_logs` | GET | Get user's own login logs |
| `check_renewals` | Internal | Auto-check and trigger renewal reminders |
| `renew_subscription` | POST | Renew subscription |
| `get_renewal_status` | GET | Get renewal status for current subscription |

#### Notification API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `get_my_notifications` | GET | Get user notifications |
| `get_unread_count` | GET | Get unread count |
| `mark_as_read` | POST | Mark notification as read |
| `mark_all_as_read` | POST | Mark all as read |
| `create_notification` | Internal | Create notification entry |

#### API v1 — Versioned

20 endpoints dengan auth check, rate limiting, standard response format.
Lihat [`api/v1/`](qalcuity/qalcuity/api/v1/) untuk detail lengkap.

**Total API:** 72 core API + 20 API v1 = **92 endpoints**

Qalcuity API should eventually provide stable endpoints for:

* authentication
* customers
* products
* invoices
* sales
* inventory
* reports
* subscriptions
* tenant information

API versioning should be considered from the beginning.

Example:

```text
/api/v1/...
```

Do not expose internal implementation details unnecessarily.

---

## 12. UI/UX Rules

Qalcuity must look like a real SaaS product.

Do not simply install ERPNext and change the logo.

The UI should progressively become Qalcuity-specific.

### Implemented Web Pages

| Page | Route | Purpose |
|------|-------|---------|
| Registration | `/register` | Customer self-registration |
| Pricing | `/pricing` | Plan listing & selection |
| Checkout | `/checkout` | Payment submission (multi bank + proof upload + WhatsApp) |
| My Payments | `/my-payments` | Customer payment history |
| Admin Reviews | `/admin-reviews` | Superadmin payment review queue |
| Dashboard | `/dashboard` | Customer dashboard dengan subscription info |
| Profile | `/profile` | Edit profil dan ganti password |
| Account Status | `/account-status` | Detail status langganan dan pembayaran |
| Subscription History | `/subscription-history` | Timeline riwayat perubahan langganan |
| Admin Dashboard | `/admin-dashboard` | Superadmin dashboard dengan revenue, customer, subscription stats |
| Verify Email | `/verify-email` | Email verification page (HMAC-SHA256 token) |
| Forgot Password | `/forgot-password` | Request password reset via email |
| Reset Password | `/reset-password` | Reset password via token |

Requirements:

* consistent branding
* clear navigation
* logical information hierarchy
* responsive layout
* proper empty states
* proper loading states
* proper error states
* accessible controls
* clear buttons
* correct use of buttons vs text
* sensible menus/submenus
* no confusing duplicate navigation
* no unreadable text
* light/dark mode must remain visually coherent if supported

Never use white text on a white background or dark text on an inappropriate dark background.

UI changes must consider both light and dark themes.

---

## 13. Security

Security is mandatory.

At minimum:

* tenant isolation (✅ row-level permission hooks)
* authentication (✅ API v1 auth check)
* authorization (✅ role-based: public/customer/admin)
* permission checks (✅ Portal User lookup)
* secure password handling (✅ change_password API)
* password validation (✅ standardized: min 8 chars + letter + number di registration & profile)
* secure file upload handling
* payment proof access control
* API authentication (✅ API v1 auth middleware)
* rate limiting (✅ 100 req/min/user via frappe.cache)
* registration rate limiting (✅ max 5 registrasi per jam per IP)
* input validation
* CSRF protection (✅ hidden token di semua web forms + frappe.call() otomatis handle)
* secure secrets (✅ .env, .env.example, .env.production)
* no secrets committed to Git
* audit logs for sensitive actions (✅ Qalcuity Audit Log DocType)

Never trust frontend permissions.

Every sensitive operation must be authorized server-side.

---

## 14. Deployment

### Development Strategy: Code Local → Test di VPS

> **⚠️ PENTING — CATATAN UNTUK AI AGENT:**
> Developer lokal TIDAK memiliki Docker dan storage terbatas (~5GB).
> **Testing dan validasi dilakukan langsung di VPS**, bukan di lokal.
> Local environment HANYA untuk coding/editing.
> VPS menggunakan **Docker (frappe_docker)** untuk menjalankan Frappe/ERPNext dan **AAPanel** untuk management (domain, SSL, nginx).
> Selalu ingat constraint ini saat mengerjakan task.

### Workflow

```text
Local Machine (Coding Only — TANPA Docker)
   ↓
Edit code di VS Code
   ↓
Git commit + push ke GitHub
   ↓
VPS Production (Docker + AAPanel)
   ↓
cd apps/qalcuity && git pull origin main
   ↓
cd ../..
   ↓
bench migrate
   ↓
bench build
   ↓
docker compose up -d --force-recreate frontend
   ↓
Testing langsung di browser VPS
   ↓
Validasi flow & UI
```

### Constraint Developer

| Item | Status |
|------|--------|
| Local Docker | ❌ Tidak ada |
| Local Storage | ❌ Terbatas (~5GB) |
| Local Frappe/ERPNext | ❌ Tidak bisa install |
| Local Testing | ❌ Tidak bisa dilakukan |
| VPS Docker (Frappe/ERPNext runtime) | ✅ Tersedia |
| VPS AAPanel (management layer) | ✅ Tersedia |
| VPS Testing | ✅ Bisa langsung |
| Git Push | ✅ Bisa dari lokal |

### Peraturan untuk AI Agent

1. **JANGAN** minta user install Frappe/ERPNext di lokal
2. **JANGAN** minta user jalankan `bench` command di lokal
3. **JANGAN** suggest Docker setup di lokal
4. **HARUS** selalu assume testing dilakukan di VPS
5. **HARUS** push ke Git setelah setiap perubahan signifikan
6. **HARUS** berikan instruksi VPS update setelah push (termasuk `docker compose` commands)
7. **LOKAL = CODE ONLY** — tidak ada testing, tidak ada running server
8. **VPS = Docker + AAPanel** — Docker menjalankan aplikasi, AAPanel manage infrastructure

### Single-Site Multi-Tenant

Qalcuity menggunakan arsitektur **single-site multi-tenant**. Semua tenant berbagi `qalcuity.com`. Tenant isolation dilakukan di level aplikasi (row-level permission hooks), bukan di level site.

---

### Production Environment

Production environment menggunakan VPS managed dengan **Docker (frappe_docker)** untuk runtime aplikasi dan **AAPanel** untuk management layer (domain, SSL, nginx, database, dll).

**Dua layer utama:**
- **Docker** = Application/runtime layer — menjalankan Frappe, ERPNext, Qalcuity, MariaDB, Redis, Workers
- **AAPanel** = Management layer — manage domain, SSL, nginx, file management, database admin

### VPS Setup

* **Panel:** AAPanel (port 15252) — management layer
* **Runtime:** Docker (frappe_docker) — application layer
* **Framework:** Frappe Framework (dalam Docker container)
* **ERP:** ERPNext (dalam Docker container)
* **Custom App:** Qalcuity (dalam Docker container, via `git pull` + `bench migrate`)
* **Database:** MariaDB (dalam Docker container, managed via AAPanel)
* **Cache:** Redis (dalam Docker container)
* **Web Server:** Nginx (via AAPanel — reverse proxy ke Docker)
* **Domain:** `qalcuity.com`
* **Site Name (bench):** `qalcuity.com`
* **Production URL:** `https://qalcuity.com`

### Deployment Diagram

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

---

## 14a. VPS Deployment Architecture

> **⚠️ CATATAN PENTING:** Section ini mendokumentasikan knowledge spesifik tentang deployment VPS yang telah dipelajari dari pengalaman production. Wajib dibaca sebelum melakukan deployment atau debugging di VPS.

### VPS File Structure

```text
/opt/qalcuity/
├── frappe_docker/
│   ├── docker-compose.yml          ← Main compose file
│   └── .env                        ← Docker env
│
├── apps/                           ← via Docker named volume "apps"
│   ├── frappe/                     ← Frappe Framework source
│   ├── erpnext/                    ← ERPNext source
│   └── qalcuity/                   ← Qalcuity custom app (via git pull)
│
└── sites/                          ← via Docker named volume "sites"
    └── qalcuity.com/
        ├── site_config.json        ← Site config (scheme, host_name)
        ├── .env                    ← Qalcuity env vars
        ├── private/                ← Private files
        ├── public/                 ← Public files
        ├── logs/                   ← Log files
        └── assets/                 ← Built assets (CSS, JS, fonts, icons)
            ├── frappe/             ← Frappe bundled assets
            │   ├── dist/css/       ← Bundled CSS (desk.bundle.*, login.bundle.*, etc.)
            │   ├── dist/js/        ← Bundled JS
            │   ├── css/fonts/      ← Font files (Inter, FontAwesome)
            │   ├── icons/          ← Frappe icons (timeless, espresso)
            │   └── images/         ← UI state images
            ├── erpnext/            ← ERPNext bundled assets
            │   ├── dist/css/
            │   └── dist/js/
            └── qalcuity/           ← Qalcuity custom assets
                ├── css/            ← qalcuity.css, qalcuity-admin.css
                └── js/             ← qalcuity.js
```

**Penting:**
- Path `/opt/qalcuity/` adalah host path — di dalam container berbeda (biasanya `/home/frappe/frappe-bench/`)
- Named volumes `apps` dan `sites` adalah INDEPENDENT dari host filesystem
- Host's `apps/qalcuity/` TIDAK di-share ke container → harus `git pull` DI DALAM container

### Docker Container Architecture

```text
┌─────────────────────────────────────────┐
│              Docker Network              │
│                                          │
│  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ backend   │  │ frontend │  │ db     │ │
│  │ (8000)   │  │ (8080)   │  │(3306)  │ │
│  │ Frappe   │  │ Nginx    │  │MariaDB │ │
│  │ worker   │  │ serve    │  │        │ │
│  │ scheduler│  │ static   │  │        │ │
│  └──────────┘  └──────────┘  └────────┘ │
│       │              │                   │
│       ▼              ▼                   │
│  ┌──────────────────────────┐           │
│  │    Shared Volumes:       │           │
│  │  • apps (Frappe/ERPNext/ │           │
│  │    Qalcuity source)      │           │
│  │  • sites (assets, config,│           │
│  │    logs, files)          │           │
│  │  • bench-env (.env)      │           │
│  └──────────────────────────┘           │
└─────────────────────────────────────────┘
```

**Container roles:**
- **backend** — Menjalankan Frappe application, worker, scheduler. Port 8000.
- **frontend** — Nginx yang serve static assets dan reverse proxy ke backend. Port 8080.
- **db** — MariaDB database. Port 3306.

### Critical Docker Volume Issues

> **⚠️ INI ADALAH ISSUE YANG PALING SERING MEMBUAT BINGUNG — WAJIB DIPAHAMI**

1. **Host's `apps/qalcuity/` is NOT shared with container** — Named volume `apps` di container adalah copy terpisah. Untuk update code, harus `git pull` DI DALAM container, bukan di host.

2. **Named volumes `apps:` dan `sites:` are INDEPENDENT of host filesystem** — Tidak ada automatic sync antara host path dan named volume.

3. **`docker compose restart` does NOT update volume mounts** — Restart hanya restart container, tidak update isi volume.

4. **After `bench build`, assets are only in backend container's `sites/` volume** — Frontend container punya copy `sites/` volume yang TERPISAH. Assets harus di-sync manual.

5. **Frontend container has SEPARATE copy of `sites/` volume** — Ini karena Docker named volume behavior. Assets yang dibuat di backend tidak otomatis muncul di frontend.

### Asset Serving Architecture

```text
Browser Request
    │
    ▼
nginx (frontend container)
    │
    ├── /assets/*  → try_files $uri =404 (serve dari filesystem)
    │                  TIDAK proxy ke backend!
    │
    └── /api/*, /app/*  → proxy ke backend (port 8000)
```

**Jenis-jenis assets:**

| Type | Location | How to Build/Copy |
|------|----------|-------------------|
| **Bundled assets** | `sites/assets/frappe/dist/`, `sites/assets/erpnext/dist/` | Dibuat oleh `bench build` |
| **Static assets** (fonts, icons, images) | `sites/assets/*/css/fonts/`, `sites/assets/*/icons/` | Harus di-copy dari `apps/*/public/` ke `sites/assets/` |
| **App-specific assets** | `sites/assets/qalcuity/` | Harus di-copy dari `apps/qalcuity/qalcuity/public/` ke `sites/assets/qalcuity/` |

**Penting:** nginx config: `location /assets { try_files $uri =404; }` — hanya serve dari filesystem, TIDAK proxy ke backend. Jadi assets harus ADA di filesystem container frontend.

### Deployment Workflow — Complete

Setelah code changes di local machine:

```bash
# ============================================
# STEP 1: Local — Git push
# ============================================
cd qalcuity && git push origin main

# ============================================
# STEP 2: VPS — Pull inside container + migrate + build
# ============================================
# Pull code di DALAM backend container
docker compose exec backend bash -c "cd /home/frappe/frappe-bench/apps/qalcuity && git pull upstream main"

# Migrate database
docker compose exec backend bench --site qalcuity.com migrate

# Clear cache
docker compose exec backend bench --site qalcuity.com clear-cache

# Build assets (force rebuild)
docker compose exec backend bench build --force

# ============================================
# STEP 3: Copy static assets dari apps ke sites/assets
# ============================================
# ⚠️ HARUS dilakukan SEBELUM tar sync!
# bench build hanya copy bundled assets, bukan static files (fonts, icons, dll)

# Buat direktori tujuan
docker compose exec backend mkdir -p /home/frappe/frappe-bench/sites/assets/qalcuity/{css,js,images}

# Copy Qalcuity assets
docker compose exec backend cp /home/frappe/frappe-bench/apps/qalcuity/qalcuity/public/css/* /home/frappe/frappe-bench/sites/assets/qalcuity/css/
docker compose exec backend cp /home/frappe/frappe-bench/apps/qalcuity/qalcuity/public/js/* /home/frappe/frappe-bench/sites/assets/qalcuity/js/

# Copy Frappe static assets (fonts, icons) — jika diperlukan
docker compose exec backend cp -rn /home/frappe/frappe-bench/apps/frappe/public/css/fonts/* /home/frappe/frappe-bench/sites/assets/frappe/css/fonts/ 2>/dev/null || true
docker compose exec backend cp -rn /home/frappe/frappe-bench/apps/frappe/public/js/frappe/icons/* /home/frappe/frappe-bench/sites/assets/frappe/icons/ 2>/dev/null || true

# ============================================
# STEP 4: Sync all assets dari backend ke frontend
# ============================================
# ⚠️ KRUSIAL! Frontend container punya copy sites/ volume yang TERPISAH

# Tar semua assets di backend
docker compose exec backend tar czf /tmp/assets.tar.gz -C /home/frappe/frappe-bench/sites assets/

# Copy tar file dari backend container ke host
docker cp $(docker compose ps -q backend):/tmp/assets.tar.gz /tmp/qalcuity-assets.tar.gz

# Copy tar file dari host ke frontend container
docker cp /tmp/qalcuity-assets.tar.gz $(docker compose ps -q frontend):/tmp/

# Extract di frontend container
docker compose exec frontend tar xzf /tmp/qalcuity-assets.tar.gz -C /home/frappe/frappe-bench/sites/

# Reload nginx di frontend
docker compose exec frontend nginx -s reload

# Bersihkan tar file
rm -f /tmp/qalcuity-assets.tar.gz
docker compose exec backend rm -f /tmp/assets.tar.gz
docker compose exec frontend rm -f /tmp/qalcuity-assets.tar.gz
```

### Known Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| CSS 404 after bench build | Docker named volume tidak auto-sync antara backend/frontend | Manual copy assets via tar + docker cp (Step 4) |
| Font files 404 | Fonts di `apps/*/public/css/fonts/`, bukan di `sites/assets/` | `cp -rn apps/frappe/public/css/fonts/* sites/assets/frappe/css/fonts/` |
| Qalcuity CSS/JS 404 | `cp -rn public/*` gagal jika destination dir belum ada | `mkdir -p` dulu, lalu `cp` individual |
| Frappe icons 404 | Source path `public/js/frappe/icons/` ≠ URL path `assets/frappe/icons/` | Cari source path yang benar dan copy ke `sites/assets/frappe/icons/` |
| `git pull upstream` fails on host | Remote `upstream` hanya ada di dalam container | Gunakan `docker compose exec backend bash -c "cd ... && git pull upstream main"` |
| MandatoryError in patches | `settings.save()` trigger mandatory validation | Gunakan `settings.flags.ignore_mandatory = True` sebelum save |
| Fiscal Year error | Tidak ada fiscal year yang didefinisikan untuk tanggal saat ini | Buat fiscal year di ERPNext Setup > Fiscal Year |

### Container Management

```bash
# ============================================
# Monitoring
# ============================================
# Cek status container
docker compose ps

# View logs
docker compose logs backend
docker compose logs frontend
docker compose logs db

# View logs (follow mode)
docker compose logs -f backend

# ============================================
# Container Access
# ============================================
# Masuk ke container
docker compose exec backend bash
docker compose exec frontend bash

# ============================================
# Restart & Rebuild
# ============================================
# Restart specific service
docker compose up -d --force-recreate frontend

# Restart backend
docker compose up -d --force-recreate backend

# Full rebuild (nuclear option)
docker compose down && docker compose up -d

# ============================================
# Database Access
# ============================================
# MariaDB shell
docker compose exec db mariadb -u root -p

# ============================================
# Bench Commands (di dalam backend container)
# ============================================
docker compose exec backend bench --site qalcuity.com migrate
docker compose exec backend bench --site qalcuity.com clear-cache
docker compose exec backend bench build --force
docker compose exec backend bench restart
```

### Quick Reference: Common Deployment Commands

```bash
# Deploy biasa (code change + build)
docker compose exec backend bash -c "cd /home/frappe/frappe-bench/apps/qalcuity && git pull upstream main" && \
docker compose exec backend bench --site qalcuity.com migrate && \
docker compose exec backend bench --site qalcuity.com clear-cache && \
docker compose exec backend bench build --force

# Copy assets + sync (setelah bench build)
docker compose exec backend mkdir -p /home/frappe/frappe-bench/sites/assets/qalcuity/{css,js,images} && \
docker compose exec backend cp /home/frappe/frappe-bench/apps/qalcuity/qalcuity/public/css/* /home/frappe/frappe-bench/sites/assets/qalcuity/css/ && \
docker compose exec backend cp /home/frappe/frappe-bench/apps/qalcuity/qalcuity/public/js/* /home/frappe/frappe-bench/sites/assets/qalcuity/js/ && \
docker compose exec backend tar czf /tmp/assets.tar.gz -C /home/frappe/frappe-bench/sites assets/ && \
docker cp $(docker compose ps -q backend):/tmp/assets.tar.gz /tmp/qalcuity-assets.tar.gz && \
docker cp /tmp/qalcuity-assets.tar.gz $(docker compose ps -q frontend):/tmp/ && \
docker compose exec frontend tar xzf /tmp/qalcuity-assets.tar.gz -C /home/frappe/frappe-bench/sites/ && \
docker compose exec frontend nginx -s reload
```

### GitHub Repository

Qalcuity custom app source code is hosted on GitHub:

* **Repository URL:** https://github.com/wahyudedik/customerpnext.git
* **Branch:** main
* **Remote Name:** origin
* **App Directory:** [`qalcuity/`](qalcuity/)

**Penting:**
* Repository Qalcuity HANYA berisi kode custom Qalcuity
* ERPNext/Frappe adalah dependency yang di-install ke bench, BUKAN bagian dari repo Qalcuity
* JANGAN pernah commit kode ERPNext ke repo Qalcuity

### Update Workflow untuk AI Agent

Setelah mengedit code di lokal, agent harus:

```bash
# 1. Pastikan semua perubahan sudah di-commit
git status
git add .
git commit -m "Sprint X: description"

# 2. Push ke GitHub
git push origin main

# 3. Berikan instruksi ke user untuk update di VPS
# "Silakan jalankan di VPS:"
# cd apps/qalcuity && git pull origin main && cd ../.. && bench migrate && bench build && docker compose up -d --force-recreate frontend
```

### Upstream Update Strategy

ERPNext/Frappe adalah dependency upstream. Update dilakukan melalui mekanisme resmi Frappe/ERPNext, bukan merge dari fork.

```bash
# Update ERPNext ke versi terbaru
pip install --upgrade erpnext

# Atau melalui bench update (update semua apps)
bench update

# Atau update hanya Frappe core
bench update --pull
```

**Keamanan Custom App Qalcuity:**
* Custom app Qalcuity tetap aman karena terpisah dari ERPNext core
* Repository Qalcuity (`wahyudedik/customerpnext`) hanya berisi kode custom
* Update ERPNext TIDAK mempengaruhi kode Qalcuity (kecuali ada breaking changes di Frappe API)
* Selalu test update di VPS sebelum apply ke production

---

## 15. Backup

### Implemented

* [`Qalcuity Backup`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_backup/) DocType — Backup records dengan status tracking
* [`backup.py`](qalcuity/qalcuity/backup.py) — `run_backup()`, `cleanup_old_backups()`, `get_backup_status()`
* [`api/backup_api.py`](qalcuity/qalcuity/api/backup_api.py) — 7 API endpoints (trigger, status, list, download, delete, stats, cleanup)
* Scheduler task — `run_scheduled_backup()` via [`tasks.py`](qalcuity/qalcuity/tasks.py)
* Retention policy — Default 30 hari (configurable)

Production data must have a backup strategy.

At minimum consider:

* database backups (✅ mysqldump + gzip)
* uploaded files (✅ tar -czf)
* configuration/secrets strategy (✅ .env files)
* backup retention (✅ 30 days default)
* restore testing

A backup that has never been restored/tested must not be considered fully reliable.

---

## 16. Development Workflow

Before implementing a feature:

1. Read AGENT.md.
2. Read relevant section of FEATURES.md.
3. Read current ROADMAP.md.
4. Inspect existing implementation.
5. Identify reusable ERPNext/Frappe functionality.
6. Determine whether custom code is actually required.
7. Implement the smallest correct solution.
8. Test the complete flow.
9. Test permission boundaries.
10. Update documentation when behavior changes.

---

## 17. Never Do These — DO NOTs

Do not:

* **JANGAN fork ERPNext** — ERPNext adalah dependency upstream, bukan source yang di-fork
* **JANGAN modify ERPNext core files** — Semua customisasi di custom app
* **JANGAN commit ERPNext code ke repo Qalcuity** — Repo hanya berisi kode custom
* **JANGAN install Frappe/ERPNext di local machine** — Local = code only, testing dilakukan di VPS
* **JANGAN edit code langsung di VPS** — Selalu edit di lokal, push ke Git, pull di VPS
* **JANGAN buat custom ERP modules yang sudah ada di ERPNext** — Gunakan fitur ERPNext yang sudah ada
* **JANGAN bypass Frappe hooks system** — Gunakan hooks untuk integrasi
* rewrite ERPNext unnecessarily
* install paid licenses without approval
* add unnecessary SaaS complexity
* implement payment gateway before MVP validation
* expose ERPNext internals unnecessarily
* hardcode customer-specific logic
* hardcode secrets
* bypass permission checks
* assume tenant isolation works without testing
* modify production manually without recording the change
* create fake features just to mark roadmap progress
* declare a feature complete without testing its real flow

---

## 18. Definition of Done

A feature is NOT complete merely because code exists.

A feature is complete when:

* implementation works
* UI works
* permissions work
* relevant API works
* error states are handled
* database behavior is correct
* tenant boundaries are respected
* production implications are understood
* relevant documentation is updated
* no known critical broken flow remains

---

## 19. Priority

Always prioritize:

```text
1. SaaS foundation
2. Customer onboarding
3. Subscription
4. Payment confirmation
5. Tenant isolation
6. ERP core functionality
7. Custom Qalcuity features
8. API
9. Automation
10. Advanced features
```

Do not build advanced features before the basic SaaS lifecycle is stable.

---

## 20. Project Status — Live

> Last Updated: 2026-08-26

### Phase 0 — Foundation: ✅ DONE

* Custom Frappe App `qalcuity` created at [`qalcuity/`](qalcuity/)
* 6 DocTypes: Settings, Plan, Plan Feature, Subscription, Payment, Tenant
* Environment config: `.env`, `.env.example`, `.env.production`
* Workspace with dashboard, charts, number cards
* Seeder data: 4 Plans (Starter/Professional/Enterprise/Trial)
* Permission rules: System Manager, Superadmin, Admin, Guest, Customer (Portal User lookup)
* API: Payment submit/approve/reject/bulk/bulk-reject/get-status/get-my-payments/get-pending-reviews ([`api/payment.py`](qalcuity/qalcuity/api/payment.py)), Customer registration ([`api/customer.py`](qalcuity/qalcuity/api/customer.py)), Settings ([`api/settings.py`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_settings/qalcuity_settings.py))
* Scheduler: Daily subscription expiry check ([`tasks.py`](qalcuity/qalcuity/tasks.py))
* CSS branding with light/dark mode
* Patch: Tenant link field on Subscription ([`add_tenant_to_subscription`](qalcuity/qalcuity/patches/add_tenant_to_subscription.py))

### Phase 1 — Base ERP: 🔄 IN PROGRESS

* Frappe/ERPNext installed and configured
* Database, Redis, scheduler operational
* Pending: reverse proxy, HTTPS, domain configuration

### Phase 2 — Custom App: ✅ DONE

* App structure established
* All DocTypes implemented
* Permission rules defined (Portal User lookup)
* API conventions established
* Branding applied
* Bug fixes completed (Batch 1 & 2)
* Email notifications implemented

### Phase 3 — SaaS Account System: ✅ DONE

* Customer registration page (`/register`)
* Registration API (`register_customer()`)
* Auto-create User + Customer + Portal User + Tenant

### Phase 4 — Subscription System: ✅ DONE

* Subscription auto-create (payment approved → subscription active)
* Grace period 7 hari
* Subscription enforcement (ERPNext access block)

### Phase 5 — Manual Payment System: ✅ DONE

* Checkout page (`/checkout`)
* My Payments page (`/my-payments`)
* Admin Reviews page (`/admin-reviews`)
* Pending reviews API (`get_pending_reviews()`)

### Phase 6 — Tenant Management: ✅ DONE

* Multi-tenant isolation via permission hooks
* Row-level isolation verified

### Sprint 1 — Foundation: ✅ DONE

| Item | Status |
|------|--------|
| Custom Frappe App `qalcuity` | ✅ |
| 6 DocTypes | ✅ |
| Environment configuration | ✅ |
| Workspace + Navigation | ✅ |
| Seeder data (Plans + Settings) | ✅ |
| Permission rules | ✅ |
| CSS branding (light/dark) | ✅ |
| Payment API (submit/approve/reject) | ✅ |
| Customer hook (auto-create tenant) | ✅ |
| Subscription auto-expire scheduler | ✅ |

### Sprint 2 — Bug Fixes & Improvements: ✅ DONE

| Item | Status |
|------|--------|
| Permission check → Portal User lookup (bukan `customer_name`) | ✅ |
| Hapus `override_whitelisted_methods` redundan dari hooks.py | ✅ |
| Fix `bulk_approve_payments` rollback logic — batch rollback | ✅ |
| Hapus `seed_initial_data()` redundan dari tasks.py | ✅ |
| Fix `get_settings()` — return dict (bukan doc object) | ✅ |
| Patch: `tenant` link field ke Subscription | ✅ |
| Rejection email notification | ✅ |
| Approval email notification | ✅ |
| Tenant ID auto-generation: `TENANT-{YYYYMMDD}-{####}` | ✅ |
| Workspace navigation — menu/sub menu terpisah, ikon profesional | ✅ |
| Bulk reject payments API | ✅ |
| Customer payment history API (`get_my_payments`) | ✅ |

### Sprint 3 — SaaS Flow: ✅ DONE

| Item | Status |
|------|--------|
| Customer Registration Page (`/register`) | ✅ |
| Registration API (`register_customer()`) | ✅ |
| Multi-tenant Isolation (row-level permission hooks) | ✅ |
| Pricing Page (`/pricing`) — Plan listing & selection | ✅ |
| Checkout Page (`/checkout`) — Payment submission | ✅ |
| My Payments Page (`/my-payments`) — Payment history | ✅ |
| Subscription Auto-Create (payment approved → active) | ✅ |
| Grace Period 7 hari | ✅ |
| Subscription Enforcement (ERPNext access block) | ✅ |
| Admin Reviews Page (`/admin-reviews`) | ✅ |
| Pending Reviews API (`get_pending_reviews()`) | ✅ |
| Subscription enforcement scheduler | ✅ |

### Sprint 4 — Features & Polish: ✅ DONE

| Item | Status |
|------|--------|
| Customer Profile Page (`/profile`) | ✅ |
| Account Status Page (`/account-status`) | ✅ |
| Custom Login Page (Qalcuity-branded) | ✅ |
| Audit Log (DocType + API) | ✅ |
| Plan Limits Enforcement (`enforcement.py`) | ✅ |
| Subscription History UI (`/subscription-history`) | ✅ |
| API v1 Versioned (20 endpoints) | ✅ |
| Backup Automation (scheduler + retention) | ✅ |

### Sprint 5 — Payment & Notifications: ✅ DONE

| Item | Status |
|------|--------|
| Multi bank accounts (BRI, JAGO, BTN, BSI) | ✅ |
| Payment mode toggle (Manual/Xendit/Hybrid) | ✅ |
| Checkout page redesign (multiple bank accounts) | ✅ |
| WhatsApp confirmation link | ✅ |
| Superadmin email notification | ✅ |
| Qalcuity Notification DocType | ✅ |
| Bell icon notification component | ✅ |
| Notification API (5 endpoints) | ✅ |
| .env update (Xendit, WhatsApp, notification) | ✅ |

### Sprint 6 — ERP Provisioning: ✅ DONE

| Item | Status |
|------|--------|
| Provisioning module ([`provisioning.py`](qalcuity/qalcuity/provisioning.py)) | ✅ |
| Qalcuity Provisioning Log DocType | ✅ |
| ERP User role ([`erp_user.json`](qalcuity/qalcuity/roles/erp_user.json)) | ✅ |
| ERP Customer workspace | ✅ |
| Tenant DocType provisioning fields | ✅ |
| Subscription on_update provisioning triggers | ✅ |
| Dashboard ERP Access Banner | ✅ |
| Company-based isolation ([`erpnext_hooks.py`](qalcuity/qalcuity/erpnext_hooks.py)) | ✅ |
| Dual-layer isolation ([`isolation.py`](qalcuity/qalcuity/isolation.py)) | ✅ |
| seed_erp_user_role patch | ✅ |
| seed_bank_accounts patch | ✅ |
| patches.txt format fix | ✅ |

### Sprint 7 — Hooks Sync, Security & UI/UX Improvements: ✅ DONE

| Item | Status |
|------|--------|
| Hooks.py Sync (website_context, website_script, fixtures, retry scheduler) | ✅ |
| Grace Period Status (8 files updated) | ✅ |
| Registration Rate Limiting (max 5 per jam per IP) | ✅ |
| Password Validation Standardized (min 8 chars + letter + number) | ✅ |
| Branding Fixes ("ERPNext" → "ERP", desk branding hide) | ✅ |
| Reusable Navigation Template (`navigation.html`) | ✅ |
| UI/UX Responsive Mobile (hamburger, grid, forms, tables) | ✅ |
| Website Branding Patch (`set_website_branding`) | ✅ |

### Sprint 8 — Dashboard, Security & Auth: ✅ DONE

| Item | Status |
|------|--------|
| Superadmin Dashboard (`/admin-dashboard`) — Revenue, customer, subscription, payment, tenant stats | ✅ |
| CSRF Protection — Hidden token di semua web forms | ✅ |
| Pagination — my-payments & subscription-history | ✅ |
| Email Verification — HMAC-SHA256 token, `/verify-email`, resend (rate limit 3/jam) | ✅ |
| Password Reset — `/forgot-password` + `/reset-password`, token TTL 1 jam | ✅ |

### Sprint 9 — Security, 2FA & ERP Enhancement: ✅ DONE

| Item | Status |
|------|--------|
| Two-Factor Authentication (2FA) — TOTP-based (RFC 6238), setup/enable/disable, backup codes, QR code | ✅ |
| 2FA Login Flow — Pre-login check → 2FA verify → session creation, backup code support | ✅ |
| 2FA Backup Codes — 8 codes, `XXXX-XXXX` format, SHA-256 hashed, regenerate capability | ✅ |
| Session Management — Active sessions list, force logout single/all sessions, user-agent parsing | ✅ |
| System Health Monitoring — System, application, activity stats + health checks (database, redis, scheduler) | ✅ |
| ERP Module Config per Plan — `plan_modules` field di Qalcuity Plan, module access controls per plan tier | ✅ |
| API Documentation — [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md) — 53 core API + 20 API v1 endpoints | ✅ |
| 2FA Setup Page (`/2fa-setup`) — QR code display + verification | ✅ |
| 2FA Verify Page (`/2fa-verify`) — 2FA verification during login | ✅ |
| Sessions Page (`/sessions`) — Active sessions management | ✅ |
| Admin Health Page (`/admin-health`) — System health monitoring dashboard | ✅ |

### Sprint 10 — ERP Enhancement, Reports & Security Hardening: ✅ DONE

| Item | Status |
|------|--------|
| Plan Upgrade/Downgrade Flow — Customer bisa upgrade/downgrade plan dengan prorated billing | ✅ |
| Qalcuity Plan Change DocType — Track semua perubahan plan (`PC-{YYYYMMDD}-{####}`) | ✅ |
| Custom Reports — Revenue, MRR, Churn Rate, Plan Distribution reports | ✅ |
| API Key Management — Create, list, revoke API keys + auth middleware | ✅ |
| Qalcuity Api Key DocType — API key storage dan management (`KEY-{YYYYMMDD}-{####}`) | ✅ |
| Login Audit Trail — Track semua login attempts success/failure | ✅ |
| Qalcuity Login Log DocType — Login log records (`LOG-{YYYYMMDD}-{####}`) | ✅ |
| Subscription Renewal Automation — Auto-renewal reminder & renewal flow | ✅ |
| Data Export (CSV) — Export payments, subscriptions, customers ke CSV | ✅ |
| Upload Security Audit — File type validation, size limits, content-type check | ✅ |
| Input Validation Audit — Server-side sanitasi semua user input | ✅ |
| 7 new web pages — Plan Change, Reports, API Keys, Login Logs, Data Export, Renewal, Admin Reports | ✅ |

### Next Sprint — Advanced Analytics & Integration

* [ ] Advanced analytics dashboard
* [ ] Webhook support (event-driven notifications)
* [ ] Usage-based billing (metered billing)
* [ ] Customer onboarding wizard
* [ ] White-label customization options
* [ ] Swagger/OpenAPI documentation

### Implemented DocTypes Summary

| DocType | File | Purpose |
|---------|------|---------|
| Qalcuity Settings | [`qalcuity_settings.py`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_settings/qalcuity_settings.py) | Global configuration, `get_settings()` returns dict |
| Qalcuity Plan | [`qalcuity_plan.json`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_plan/) | Subscription plans |
| Plan Feature | (child table) | Features per plan |
| Qalcuity Subscription | [`qalcuity_subscription/`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_subscription/) | Subscription lifecycle + tenant link + grace period |
| Qalcuity Payment | [`qalcuity_payment.py`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_payment/qalcuity_payment.py) | Manual payment + email notifications + auto-create subscription |
| Qalcuity Tenant | [`qalcuity_tenant.py`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_tenant/qalcuity_tenant.py) | Tenant isolation, auto-generated ID, row-level permissions + provisioning fields |
| Qalcuity Audit Log | [`qalcuity_audit_log/`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_audit_log/) | Audit trail untuk aksi sensitif (`AL-{YYYYMMDD}-{####}`) |
| Qalcuity Subscription Log | [`qalcuity_subscription_log/`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_subscription_log/) | Riwayat perubahan subscription (`SL-{YYYYMMDD}-{####}`) |
| Qalcuity Backup | [`qalcuity_backup/`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_backup/) | Backup records dengan status tracking (`BACKUP-{YYYYMMDD}-{####}`) |
| Qalcuity Bank Account | (child table) | Multiple bank accounts per settings (`BANK-{####}`) |
| Qalcuity Notification | [`qalcuity_notification/`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_notification/) | In-app notifications (`NOTIF-{YYYYMMDD}-{####}`) |
| Qalcuity Provisioning Log | [`qalcuity_provisioning_log/`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_provisioning_log/) | ERP provisioning event tracking (`PROV-{YYYYMMDD}-{####}`) |
| Qalcuity Plan Change | [`qalcuity_plan_change/`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_plan_change/) | Plan upgrade/downgrade history (`PC-{YYYYMMDD}-{####}`) |
| Qalcuity Api Key | [`qalcuity_api_key/`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_api_key/) | API key management for external integrations (`KEY-{YYYYMMDD}-{####}`) |
| Qalcuity Login Log | [`qalcuity_login_log/`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_login_log/) | Login audit trail — success/failure tracking (`LOG-{YYYYMMDD}-{####}`) |

### Implemented Web Pages (24 + Navigation)

| Page | Route | Purpose |
|------|-------|---------|
| Registration | `/register` | Customer self-registration |
| Pricing | `/pricing` | Plan listing & selection |
| Checkout | `/checkout` | Payment submission (multi bank + proof upload + WhatsApp) |
| My Payments | `/my-payments` | Customer payment history |
| Admin Reviews | `/admin-reviews` | Superadmin payment review queue |
| Dashboard | `/dashboard` | Customer dashboard dengan subscription info |
| Profile | `/profile` | Edit profil dan ganti password |
| Account Status | `/account-status` | Detail status langganan dan pembayaran |
| Subscription History | `/subscription-history` | Timeline riwayat perubahan langganan |
| Admin Dashboard | `/admin-dashboard` | Superadmin dashboard dengan revenue, customer, subscription stats |
| Verify Email | `/verify-email` | Email verification page (HMAC-SHA256 token) |
| Forgot Password | `/forgot-password` | Request password reset via email |
| Reset Password | `/reset-password` | Reset password via token |
| 2FA Setup | `/2fa-setup` | Two-factor authentication setup page |
| 2FA Verify | `/2fa-verify` | 2FA verification during login |
| Sessions | `/sessions` | Active sessions management page |
| Admin Health | `/admin-health` | System health monitoring dashboard |
| Plan Change | `/plan-change` | Upgrade/downgrade plan page |
| Reports | `/reports` | Custom SaaS reports (revenue, MRR, churn, plan distribution) |
| API Keys | `/api-keys` | API key management page |
| Login Logs | `/login-logs` | Login audit trail page |
| Data Export | `/data-export` | Export data ke CSV |
| Renewal | `/renewal` | Subscription renewal page |
| Admin Reports | `/admin-reports` | Superadmin reports dashboard |
| Navigation | (included) | [`navigation.html`](qalcuity/qalcuity/templates/includes/navigation.html) — reusable header bar dengan hamburger menu mobile |

### Implemented Patches

| Patch | File | Purpose |
|-------|------|---------|
| `add_tenant_to_subscription` | [`patches/add_tenant_to_subscription.py`](qalcuity/qalcuity/patches/add_tenant_to_subscription.py) | Menambahkan field `tenant` (Link) ke Qalcuity Subscription |
| `seed_bank_accounts` | [`patches/seed_bank_accounts.py`](qalcuity/qalcuity/patches/seed_bank_accounts.py) | Seed 4 bank accounts default (BRI, JAGO, BTN, BSI) |
| `seed_erp_user_role` | [`patches/seed_erp_user_role.py`](qalcuity/qalcuity/patches/seed_erp_user_role.py) | Seed "Qalcuity ERP User" role for tenant users |
| `set_website_branding` | [`set_website_branding.py`](qalcuity/qalcuity/qalcuity/patches/set_website_branding.py) | Set Website Settings branding (favicon, splash, app_logo) ke Qalcuity |
