# AGENT.md

# Qalcuity ERP — AI Engineering Agent

> **📦 GitHub Repository:** [`wahyudedik/customerpnext`](https://github.com/wahyudedik/customerpnext) · Branch: `main`

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
          └──────────────┼──────────────┘
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

## 1a. ERPNext Role (Core Engine)

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

## 1b. Qalcuity Role (Custom Layer)

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

# 3. Engineering Philosophy

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

# 4. Source of Truth

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

# 5. ERPNext/Frappe Customization Rule

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

# 6. SaaS Architecture

Qalcuity menambahkan **SaaS layer DI ATAS ERPNext**. ERPNext tetap utuh sebagai core engine. Customisasi hanya dilakukan di custom app, bukan di ERPNext core.

The system should conceptually be divided into:

## SaaS Control Layer (Qalcuity Custom App)

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

## ERP Layer (ERPNext — TIDAK DIMODIFIKASI)

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

# 7. Tenant Isolation

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

---

# 8. Subscription Model

Initial payment method:

> Manual bank transfer.

Do NOT implement a payment gateway in the MVP unless explicitly requested.

Basic flow:

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

Rejected payment:

```text
PENDING
   ↓
REJECTED
   ↓
Customer can submit again
```

Expired subscription with grace period:

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
Akses sepenuhnya dibatasi
```

---

# 9. Superadmin

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
* inspect system status
* inspect important logs

Do not expose Superadmin functions to ordinary customers.

---

# 10. Payment Rules

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

# 11. API

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

#### Notification API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `get_my_notifications` | GET | Get user notifications |
| `get_unread_count` | GET | Get unread count |
| `mark_as_read` | POST | Mark notification as read |
| `mark_all_as_read` | POST | Mark all as read |
| `create_notification` | Internal | Create notification entry |

#### API v1 (Versioned)

24 endpoints dengan auth check, rate limiting, standard response format.
Lihat [`api/v1/`](qalcuity/qalcuity/api/v1/) untuk detail lengkap.

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

# 12. UI/UX Rules

Qalcuity must look like a real SaaS product.

Do not simply install ERPNext and change the logo.

The UI should progressively become Qalcuity-specific.

### Implemented Web Pages

| Page | Route | Purpose |
|------|-------|---------|
| Registration | `/register` | Customer self-registration |
| Pricing | `/pricing` | Plan listing & selection |
| Checkout | `/checkout` | Payment submission |
| My Payments | `/my-payments` | Customer payment history |
| Admin Reviews | `/admin-reviews` | Superadmin payment review queue |
| Dashboard | `/dashboard` | Customer dashboard dengan subscription info |
| Profile | `/profile` | Edit profil dan ganti password |
| Account Status | `/account-status` | Detail status langganan dan pembayaran |
| Subscription History | `/subscription-history` | Timeline riwayat perubahan langganan |

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

# 13. Security

Security is mandatory.

At minimum:

* tenant isolation (✅ row-level permission hooks)
* authentication (✅ API v1 auth check)
* authorization (✅ role-based: public/customer/admin)
* permission checks (✅ Portal User lookup)
* secure password handling (✅ change_password API)
* secure file upload handling
* payment proof access control
* API authentication (✅ API v1 auth middleware)
* rate limiting (✅ 100 req/min/user via frappe.cache)
* input validation
* CSRF protection where applicable
* secure secrets (✅ .env, .env.example, .env.production)
* no secrets committed to Git
* audit logs for sensitive actions (✅ Qalcuity Audit Log DocType)

Never trust frontend permissions.

Every sensitive operation must be authorized server-side.

---

# 14. Deployment

## Development Strategy: Code Local → Test di VPS

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
docker compose exec backend bash -c "cd /home/frappe/frappe-bench/apps/qalcuity && git pull upstream main"
   ↓
docker compose exec backend bench --site qalcuity.com migrate
   ↓
docker compose exec backend bench --site qalcuity.com clear-cache
   ↓
docker compose exec backend bench build --force
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

---

## Production Environment

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

### Domain Configuration

* **Production Domain:** `qalcuity.com`
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

## GitHub Repository

Qalcuity custom app source code is hosted on GitHub:

* **Repository URL:** https://github.com/wahyudedik/customerpnext.git
* **Branch:** main
* **Remote Name:** origin
* **App Directory:** [`qalcuity/`](qalcuity/)

**Penting:**
* Repository Qalcuity HANYA berisi kode custom Qalcuity
* ERPNext/Frappe adalah dependency yang di-install ke bench, BUKAN bagian dari repo Qalcuity
* JANGAN pernah commit kode ERPNext ke repo Qalcuity

### Deploy dari GitHub (di VPS — Fresh Install)

```bash
# 1. Install Frappe bench (jika belum ada)
# 2. Init bench dengan ERPNext
bench init --frappe-branch version-17 erpnext
cd erpnext
bench get-app erpnext
# 3. Install Qalcuity Custom App
bench get-app https://github.com/wahyudedik/customerpnext.git
bench --site qalcuity.com install-app qalcuity
bench migrate
bench build
bench restart
```

### Update dari GitHub (di VPS — Regular Update)

> **⚠️ CRITICAL:** In this Docker setup, the host's `apps/qalcuity/` directory is NOT shared with the container. Always run `git pull` INSIDE the container via `docker compose exec backend`.

```bash
# All commands run INSIDE the container — host's apps/ directory is separate
docker compose exec backend bash -c "cd /home/frappe/frappe-bench/apps/qalcuity && git pull upstream main"
docker compose exec backend bench --site qalcuity.com migrate
docker compose exec backend bench --site qalcuity.com clear-cache
docker compose exec backend bench build --force
docker compose up -d --force-recreate frontend
```

### Update Workflow untuk AI Agent

Setelah mengedit code di lokal, agent harus:

```bash
# 1. Pastikan semua perubahan sudah di-commit
git status
git add .
git commit -m "Sprint X: description"

# 2. Push ke GitHub
git push origin main

# 3. Berikan instruksi ke user untuk update di VPS (semua command dijalankan di container)
# "Silakan jalankan di VPS:"
# docker compose exec backend bash -c "cd /home/frappe/frappe-bench/apps/qalcuity && git pull upstream main" && docker compose exec backend bench --site qalcuity.com migrate && docker compose exec backend bench --site qalcuity.com clear-cache && docker compose exec backend bench build --force && docker compose up -d --force-recreate frontend
```

---

## Do NOT

* Edit code langsung di VPS tanpa commit ke Git
* Treat VPS files sebagai canonical source
* Skip Git push setelah perubahan
* Run bench commands di lokal machine
* Install Frappe/ERPNext di local machine — gunakan VPS untuk testing
* Edit code langsung di VPS — selalu edit di lokal, push ke Git, pull di VPS

---

## Upstream Update Strategy

ERPNext/Frappe adalah dependency upstream. Update dilakukan melalui mekanisme resmi Frappe/ERPNext, bukan merge dari fork.

### Cara Update ERPNext

```bash
# Update ERPNext ke versi terbaru
pip install --upgrade erpnext

# Atau melalui bench update (update semua apps)
bench update

# Atau update hanya Frappe core
bench update --pull
```

### Cara Update Frappe Framework

```bash
# Update Frappe core
bench update --pull

# Atau update spesifik branch
bench get-app frappe --branch version-17
```

### Keamanan Custom App Qalcuity

* Custom app Qalcuity tetap aman karena terpisah dari ERPNext core
* Repository Qalcuity (`wahyudedik/customerpnext`) hanya berisi kode custom
* Update ERPNext TIDAK mempengaruhi kode Qalcuity (kecuali ada breaking changes di Frappe API)
* Selalu test update di VPS sebelum apply ke production

### Proses Update yang Aman

```text
1. Backup database (otomatis via scheduler atau manual)
2. Backup files
3. Jalankan update:
   pip install --upgrade erpnext
   bench update
4. Test di browser VPS:
   - Login berhasil
   - Subscription flow berfungsi
   - Payment flow berfungsi
   - Tenant isolation berfungsi
   - API berfungsi
5. Jika ada error, rollback:
   git checkout versi_sebelumnya
   bench migrate
```

### Kapan Update Dilakukan

* Update ERPNext: Saat ada release baru yang penting
* Update Frappe: Saat ada security patch atau bug fix
* Update Qalcuity: Setelah setiap sprint/task selesai
* JANGAN update jika tidak ada kebutuhan mendesak

---

# 15. Backup

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

# 16. Development Workflow

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

# 17. Never Do These (DO NOTs)

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

# 18. Definition of Done

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

# 19. Priority

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

# 20. Project Status (Live)

> Last Updated: 2026-08-25

## Phase 0 — Foundation: ✅ DONE

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

## Phase 1 — Base ERP: 🔄 IN PROGRESS

* Frappe/ERPNext installed and configured
* Database, Redis, scheduler operational
* Pending: reverse proxy, HTTPS, domain configuration

## Phase 2 — Custom App: ✅ DONE

* App structure established
* All DocTypes implemented
* Permission rules defined (Portal User lookup)
* API conventions established
* Branding applied
* Bug fixes completed (Batch 1 & 2)
* Email notifications implemented

## Phase 3 — SaaS Account System: ✅ DONE

* Customer registration page (`/register`)
* Registration API (`register_customer()`)
* Auto-create User + Customer + Portal User + Tenant

## Phase 4 — Subscription System: ✅ DONE

* Subscription auto-create (payment approved → subscription active)
* Grace period 7 hari
* Subscription enforcement (ERPNext access block)

## Phase 5 — Manual Payment System: ✅ DONE

* Checkout page (`/checkout`)
* My Payments page (`/my-payments`)
* Admin Reviews page (`/admin-reviews`)
* Pending reviews API (`get_pending_reviews()`)

## Phase 6 — Tenant Management: ✅ DONE

* Multi-tenant isolation via permission hooks
* Row-level isolation verified

## Sprint 1 — Foundation: ✅ DONE

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

## Sprint 2 — Bug Fixes & Improvements: ✅ DONE

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

## Sprint 3 — SaaS Flow: ✅ DONE

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

## Sprint 4 — Features & Polish: ✅ DONE

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

## Sprint 5 — Payment & Notifications: ✅ DONE

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

## Sprint 6 — ERP Provisioning: ✅ DONE

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

## Next Sprint — ERP Provisioning & Polish

* [ ] Superadmin custom dashboard
* [ ] Custom reports
* [ ] ERP module configuration per plan
* [ ] Customer-level data export
* [ ] Email verification
* [ ] Password reset automation
* [ ] Two-factor authentication
* [ ] API documentation (Swagger/OpenAPI)
* [ ] Production deployment automation

## Implemented DocTypes Summary

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

## Implemented Web Pages

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

## Implemented Patches

| Patch | File | Purpose |
|-------|------|---------|
| `add_tenant_to_subscription` | [`patches/add_tenant_to_subscription.py`](qalcuity/qalcuity/patches/add_tenant_to_subscription.py) | Menambahkan field `tenant` (Link) ke Qalcuity Subscription |
| `seed_bank_accounts` | [`patches/seed_bank_accounts.py`](qalcuity/qalcuity/patches/seed_bank_accounts.py) | Seed 4 bank accounts default (BRI, JAGO, BTN, BSI) |
| `seed_erp_user_role` | [`patches/seed_erp_user_role.py`](qalcuity/qalcuity/patches/seed_erp_user_role.py) | Seed "Qalcuity ERP User" role for tenant users |
