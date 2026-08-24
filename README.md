# Qalcuity ERP

SaaS ERP Platform built on top of ERPNext/Frappe Framework.

## Overview

Qalcuity ERP is a multi-tenant SaaS layer that provides:

- Subscription-based access to ERPNext capabilities
- Manual payment workflow with proof upload
- Superadmin payment approval
- Tenant management and isolation
- Custom API layer

## Architecture

```
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
            └── Custom UI
```

## Installation

```bash
bench get-app qalcuity
bench --site site-name install-app qalcuity
```

## Configuration

1. Setup Qalcuity Settings from the Desk
2. Create Subscription Plans
3. Configure payment bank accounts
4. Assign Qalcuity roles to users

## Roles

- **Qalcuity Superadmin**: Full access to all Qalcuity doctypes
- **Qalcuity Admin**: Read/Write access to plans, subscriptions, payments, tenants
- **Customer**: Read plans, create/read own subscriptions and payments

## Seeding Data

Default data will be automatically loaded via Frappe fixtures:

- **Qalcuity Plans**: Starter (Rp 99.000/mo), Professional (Rp 299.000/mo), Enterprise (Rp 799.000/mo), Trial (Gratis 14 hari)
- **Qalcuity Settings**: Default configuration with BCA bank account

To manually seed data, run:
```bash
bench --site [site-name] execute qalcuity.qalcuity.tasks.seed_initial_data
```

## Branding

Qalcuity ERP uses custom branding applied through the qalcuity app:

- **Light mode logo**: `public/images/logo-dark.png` (dark text for light backgrounds)
- **Dark mode logo**: `public/images/logo-light.png` (light text for dark backgrounds)
- **Primary color**: `#2490EF` (Frappe blue)
- **Login page**: Custom Qalcuity branding with logo
- **Desk**: Custom app title "Qalcuity ERP" and logo via boot session override
- **Navbar**: Qalcuity branding injected via `boot_session` hook
- **CSS overrides**: Applied via `qalcuity.css` without modifying ERPNext core

### Branding Implementation

| Component | Mechanism | File |
|-----------|-----------|------|
| Desk logo/title | `override_boot_session` | [`boot.py`](qalcuity/qalcuity/boot.py) |
| Login page | `override_website_page_render_context` | [`login.py`](qalcuity/qalcuity/login.py) |
| CSS overrides | `app_include_css` | [`qalcuity.css`](qalcuity/qalcuity/public/css/qalcuity.css) |
| JS overrides | `app_include_js` | [`qalcuity.js`](qalcuity/qalcuity/public/js/qalcuity.js) |
| Logo assets | `public/images/` | `logo-dark.png`, `logo-light.png` |
| Property setters | Frappe fixtures | [`hooks.py`](hooks.py) |

## License

MIT License
