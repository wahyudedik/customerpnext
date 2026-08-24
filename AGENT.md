# AGENT.md

# Qalcuity ERP — AI Engineering Agent

> **📦 GitHub Repository:** [`wahyudedik/customerpnext`](https://github.com/wahyudedik/customerpnext) · Branch: `main`

## 1. Project Identity

Qalcuity ERP is a SaaS ERP product built on top of the Frappe Framework and ERPNext.

ERPNext is the underlying business/ERP engine. Qalcuity is the actual product presented to customers.

The objective is NOT to create a simple ERPNext installation service.

The objective is to transform the underlying ERP capabilities into a branded, customized, subscription-based SaaS product.

Core principle:

> **Use ERPNext/Frappe as the foundation. Build Qalcuity as the product layer.**

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
5. Prefer custom Frappe applications/modules over destructive core modifications.
6. Keep Qalcuity-specific logic isolated.
7. Keep the code maintainable and upgradeable.
8. Verify every important flow.
9. Never knowingly leave a broken flow.
10. Never introduce a dependency without understanding why it is required.
11. Prefer open-source/free tooling for the MVP.
12. Avoid paid licenses unless explicitly approved.
13. Do not build features simply because they are technically interesting.
14. Prioritize features that improve customer value or SaaS operation.

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

The system should conceptually be divided into:

## SaaS Control Layer

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

## ERP Layer

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
Qalcuity SaaS Layer
   │
   ├── Account
   ├── Plan
   ├── Subscription
   ├── Payment
   └── Tenant
   │
   ▼
ERPNext/Frappe
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

Before implementing the final SaaS architecture, determine the safest and most economical tenant strategy.

Possible strategies may include:

* separate Frappe sites
* controlled multi-tenancy
* another architecture supported by Frappe

Do not assume the architecture without validating it.

Tenant isolation must be tested explicitly.

---

# 8. Subscription Model

Initial payment method:

> Manual bank transfer.

Do NOT implement a payment gateway in the MVP unless explicitly requested.

Basic flow:

```text
Customer
   ↓
Choose Plan
   ↓
Create Subscription / Order
   ↓
Transfer Payment
   ↓
Upload Payment Proof
   ↓
PENDING
   ↓
Superadmin Reviews
   ↓
APPROVED
   ↓
Subscription ACTIVE
```

Rejected payment:

```text
PENDING
   ↓
REJECTED
   ↓
Customer can submit again
```

Expired subscription:

```text
ACTIVE
   ↓
Expiry Date Reached
   ↓
EXPIRED
   ↓
Access Restricted
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

* tenant isolation
* authentication
* authorization
* permission checks
* secure password handling
* secure file upload handling
* payment proof access control
* API authentication
* rate limiting where appropriate
* input validation
* CSRF protection where applicable
* secure secrets
* no secrets committed to Git
* audit logs for sensitive actions

Never trust frontend permissions.

Every sensitive operation must be authorized server-side.

---

# 14. Deployment

Production environment is expected to use a VPS managed with AAPanel where practical.

AAPanel is a server management tool, not the application architecture.

Deployment should conceptually be:

```text
Developer
   ↓
Git
   ↓
Production deployment
   ↓
VPS
   ↓
Frappe / ERPNext
   ↓
Qalcuity App
```

Do not treat files manually edited on the VPS as the canonical implementation.

### Domain Configuration

* **Production Domain:** `qalcuity.com`
* **Site Name (bench):** `qalcuity.com`
* **Production URL:** `https://qalcuity.com`

---

## GitHub Repository

Qalcuity custom app source code is hosted on GitHub:

* **Repository URL:** https://github.com/wahyudedik/customerpnext.git
* **Branch:** main
* **Remote Name:** origin
* **App Directory:** [`qalcuity/`](qalcuity/)

### Install dari GitHub (di VPS)

```bash
bench get-app https://github.com/wahyudedik/customerpnext.git
bench --site qalcuity.com install-app qalcuity
bench migrate
bench restart
```

### Update dari GitHub (di VPS)

```bash
cd apps/qalcuity
git pull origin main
cd ../..
bench migrate
bench restart
```

---

# 15. Backup

Production data must have a backup strategy.

At minimum consider:

* database backups
* uploaded files
* configuration/secrets strategy
* backup retention
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

# 17. Never Do These

Do not:

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

> Last Updated: 2026-08-22

## Phase 0 — Foundation: ✅ DONE

* Custom Frappe App `qalcuity` created at [`qalcuity/`](qalcuity/)
* 6 DocTypes: Settings, Plan, Plan Feature, Subscription, Payment, Tenant
* Environment config: `.env`, `.env.example`, `.env.production`
* Workspace with dashboard, charts, number cards
* Seeder data: 4 Plans (Starter/Professional/Enterprise/Trial)
* Permission rules: System Manager, Superadmin, Admin, Guest, Customer
* API: Payment submit/approve/reject/get ([`api/payment.py`](qalcuity/qalcuity/api/payment.py)), Customer hook ([`api/customer.py`](qalcuity/qalcuity/api/customer.py))
* Scheduler: Daily subscription expiry check ([`tasks.py`](qalcuity/qalcuity/tasks.py))
* CSS branding with light/dark mode

## Phase 1 — Base ERP: 🔄 IN PROGRESS

* Frappe/ERPNext installed and configured
* Database, Redis, scheduler operational
* Pending: reverse proxy, HTTPS, domain configuration

## Phase 2 — Custom App: ✅ DONE

* App structure established
* All DocTypes implemented
* Permission rules defined
* API conventions established
* Branding applied

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

## Next Sprint — SaaS Flow

* [ ] Customer registration page
* [ ] Plan listing & selection
* [ ] Payment submission UI
* [ ] Superadmin review queue
* [ ] Subscription management UI
* [ ] Tenant provisioning
* [ ] Notification system

## Implemented DocTypes Summary

| DocType | File | Purpose |
|---------|------|---------|
| Qalcuity Settings | [`qalcuity_settings.py`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_settings/qalcuity_settings.py) | Global configuration |
| Qalcuity Plan | [`qalcuity_plan.json`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_plan/) | Subscription plans |
| Plan Feature | (child table) | Features per plan |
| Qalcuity Subscription | [`qalcuity_subscription/`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_subscription/) | Subscription lifecycle |
| Qalcuity Payment | [`qalcuity_payment.js`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_payment/qalcuity_payment.js) | Manual payment records |
| Qalcuity Tenant | [`qalcuity_tenant.py`](qalcuity/qalcuity/qalcuity/doctype/qalcuity_tenant/qalcuity_tenant.py) | Tenant isolation |
