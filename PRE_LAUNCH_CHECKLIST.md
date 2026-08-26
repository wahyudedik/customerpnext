# QALCUITY ERP — PRE-LAUNCH VALIDATION CHECKLIST

> **Sprint 11 Task 5** — Dokumen validasi komprehensif sebelum menerima customer real.
>
> **Berdasarkan:** Phase 19 ROADMAP.md
>
> **Last Updated:** 2026-08-26

---

## Status: [ ] NOT READY / [ ] READY FOR LAUNCH

---

## 1. CUSTOMER JOURNEY (End-to-End)

Referensi: [`test_customer_journey.py`](qalcuity/tests/test_customer_journey.py)

### Registration & Authentication
- [ ] Registration flow works (email, password, business info)
- [ ] Registration validation rejects invalid inputs (missing fields, duplicate email)
- [ ] Email verification works
- [ ] Login/logout works
- [ ] Forgot password flow works
- [ ] 2FA setup and verify works

### Plan Selection & Checkout
- [ ] Plan selection page shows correct plans and pricing
- [ ] Plan details (modules, limits, features) display correctly
- [ ] Checkout flow works
- [ ] Payment instructions display correctly

### Payment & Approval
- [ ] Payment proof upload works (image/PDF)
- [ ] Payment submission creates pending record
- [ ] Admin can view payment queue
- [ ] Admin can approve payment
- [ ] Admin can reject payment with reason
- [ ] Customer can resubmit rejected payment

### Activation & Access
- [ ] Subscription activates after approval
- [ ] Tenant is provisioned after approval
- [ ] Customer can access ERP desk
- [ ] Customer dashboard shows correct status
- [ ] Subscription history shows correct records
- [ ] Profile page works
- [ ] Account status page works

---

## 2. SUBSCRIPTION LIFECYCLE

### Status Transitions
- [ ] PENDING → ACTIVE transition works
- [ ] ACTIVE subscription shows correct expiry date
- [ ] Expired subscription triggers grace period
- [ ] Grace period (7 days) works correctly — [`GRACE_PERIOD_DAYS`](qalcuity/tests/test_customer_journey.py:38)
- [ ] Expired subscription restricts ERP access
- [ ] Subscription log records all changes

### Plan Changes
- [ ] Renewal flow works
- [ ] Plan upgrade works (Starter → Business)
- [ ] Plan downgrade works (Business → Starter)
- [ ] Plan change immediately updates module access
- [ ] Billing adjustment is calculated correctly on mid-cycle changes

### Expiry Handling
- [ ] [`check_subscription_expiry()`](qalcuity/tests/test_customer_journey.py:38) scheduled task runs correctly
- [ ] Expired subscriptions transition to EXPIRED status
- [ ] Grace period messages are shown to customer
- [ ] After grace period, ERP access is fully blocked

---

## 3. TENANT ISOLATION (SECURITY) 🔒

Referensi: [`test_tenant_isolation.py`](qalcuity/tests/test_tenant_isolation.py)

> **CRITICAL SECURITY AUDIT** — Setiap test harus memverifikasi bahwa akses cross-tenant GAGAL.

### Database Row-Level Isolation
- [ ] Customer A cannot see Customer B's subscriptions
- [ ] Customer A cannot see Customer B's payments
- [ ] Customer A cannot see Customer B's ERP data
- [ ] Row-level filtering works in list views
- [ ] Row-level filtering works in form views

### API-Level Isolation
- [ ] API endpoints enforce tenant isolation
- [ ] Cross-tenant API access is blocked
- [ ] Tenant ID tampering is prevented
- [ ] API authentication includes tenant context

### ERPNext Document Isolation
- [ ] ERPNext permission hooks enforce isolation
- [ ] Company-based secondary isolation layer works
- [ ] Sales Orders are isolated between tenants
- [ ] Sales Invoices are isolated between tenants

### Permission Boundary
- [ ] [`has_permission()`](qalcuity/tests/test_tenant_isolation.py:41) hook blocks cross-tenant access
- [ ] [`get_permission_query_conditions()`](qalcuity/tests/test_tenant_isolation.py:40) adds WHERE clause filtering
- [ ] Non-admin user cannot bypass isolation
- [ ] Admin user (`Qalcuity Superadmin`) can access all tenants

### Edge Cases
- [ ] Inactive tenant cannot access ERP
- [ ] Suspended subscription tenant is blocked
- [ ] Tenant with no subscription is blocked
- [ ] File attachments are isolated between tenants
- [ ] Background job isolation works

---

## 4. MODULE ENFORCEMENT

Referensi: [`test_module_enforcement.py`](qalcuity/tests/test_module_enforcement.py)

### Plan Module Configuration
- [ ] Starter plan modules are correctly limited (Accounting, Sales, CRM, Inventory)
- [ ] Business plan has correct modules (adds HR, Projects, Buying)
- [ ] Professional plan has all modules

### Module Access Enforcement
- [ ] [`get_user_enabled_modules()`](qalcuity/tests/test_module_enforcement.py:38) returns correct modules per plan
- [ ] [`is_module_enabled_for_user()`](qalcuity/tests/test_module_enforcement.py:39) correctly gates access
- [ ] [`is_doctype_enabled_for_user()`](qalcuity/tests/test_module_enforcement.py:40) correctly gates DocType access
- [ ] User cannot access unapproved modules
- [ ] User without plan cannot access modules
- [ ] Expired subscription blocks all modules

### Plan Change Impact
- [ ] Plan upgrade immediately adds modules
- [ ] Plan downgrade immediately removes modules
- [ ] Module access reflects real-time subscription status
- [ ] [`get_module_block_message()`](qalcuity/tests/test_module_enforcement.py:41) returns user-friendly message

---

## 5. SUPERADMIN

### Dashboard & Management
- [ ] Admin dashboard loads correctly
- [ ] Admin can view all customers
- [ ] Admin can view all tenants
- [ ] Admin can manage plans (create, edit, activate/deactivate)
- [ ] Admin can view subscription history for any customer
- [ ] Admin health check works

### Payment Management
- [ ] Admin can view payment queue
- [ ] Admin can approve payments
- [ ] Admin can reject payments with reason
- [ ] Payment approval triggers subscription activation
- [ ] Payment rejection notifies customer

### Audit & Monitoring
- [ ] Admin can view login logs
- [ ] Admin can view audit logs
- [ ] Admin can view system health status
- [ ] Admin role (`Qalcuity Superadmin`) is properly restricted

---

## 6. BRANDING

Referensi: [`AGENT.md` Section 3](qalcuity/AGENT.md:49)

### Visual Identity
- [ ] Qalcuity logo displays correctly (all pages)
- [ ] Favicon displays correctly in browser tab
- [ ] Application title shows "Qalcuity" (not "ERPNext")
- [ ] Browser title shows "Qalcuity" (not "ERPNext")

### Customer-Facing Pages
- [ ] Login page has Qalcuity branding
- [ ] Registration page has Qalcuity branding
- [ ] Dashboard has Qalcuity branding
- [ ] Workspace has Qalcuity branding
- [ ] Landing page has Qalcuity branding
- [ ] Pricing page has Qalcuity branding

### Templates & Notifications
- [ ] Email templates have Qalcuity branding
- [ ] Notification templates have Qalcuity branding
- [ ] Error pages (404, 500) have Qalcuity branding

### Consistency
- [ ] No unnecessary ERPNext branding visible in customer-facing areas
- [ ] Colors/theme are consistent across all pages
- [ ] Typography is consistent
- [ ] Terminology uses Qalcuity terms (not generic ERPNext terms)

---

## 7. API

### Core Endpoints
- [ ] Health API endpoint works (`/api/v1/health`)
- [ ] Registration API works
- [ ] Plans API works
- [ ] Payment API works
- [ ] Dashboard API works

### API Management
- [ ] API key management works
- [ ] API authentication works
- [ ] API versioning (`/api/v1/`) works
- [ ] API rate limiting is configured

### API Quality
- [ ] API error responses are consistent (JSON format)
- [ ] API success responses follow standard format
- [ ] API documentation is accurate
- [ ] API endpoints enforce tenant isolation

---

## 8. BACKUP & RECOVERY 🔒

Referensi: [`test_backup_restore.py`](qalcuity/tests/test_backup_restore.py), [`RESTORE_PROCEDURE.md`](qalcuity/tests/RESTORE_PROCEDURE.md)

### Backup Creation
- [ ] Database backup can be created via [`run_backup()`](qalcuity/tests/test_backup_restore.py:38)
- [ ] Full backup (Database + Files) works
- [ ] Database-only backup works
- [ ] Files-only backup works
- [ ] Backup record is tracked in `Qalcuity Backup` DocType
- [ ] Backup file is not empty
- [ ] Backup metadata is complete (name, type, status, size, timestamps)

### Backup Scheduling
- [ ] [`run_scheduled_backup()`](qalcuity/tests/test_customer_journey.py:38) task works
- [ ] Backup retention policy is defined (`QALCUITY_BACKUP_RETENTION_DAYS`, default: 30)
- [ ] [`cleanup_old_backups()`](qalcuity/tests/test_backup_restore.py:39) removes old backups correctly
- [ ] Backup status transitions work (Pending → Running → Completed/Failed)

### Restore
- [ ] Restore procedure is documented — [`RESTORE_PROCEDURE.md`](qalcuity/tests/RESTORE_PROCEDURE.md)
- [ ] Restore script exists and works
- [ ] Database restore from `.sql.gz` works
- [ ] Files restore from `_files.tar.gz` works
- [ ] Full restore (Database + Files) works
- [ ] Post-restore verification steps work

### Backup Integrity
- [ ] [`get_backup_status()`](qalcuity/tests/test_backup_restore.py:40) returns correct status
- [ ] [`get_backup_list()`](qalcuity/tests/test_backup_restore.py:41) returns correct list
- [ ] [`get_backup_stats()`](qalcuity/tests/test_backup_restore.py:42) returns correct statistics
- [ ] Backup files are stored in `sites/{site}/private/backups/`

---

## 9. PERFORMANCE

### Page Load Times
- [ ] Login page loads in < 3 seconds
- [ ] Registration page loads in < 3 seconds
- [ ] Dashboard loads in < 5 seconds
- [ ] ERP desk loads in < 5 seconds
- [ ] Plan selection page loads in < 3 seconds

### API Performance
- [ ] Health API responds in < 1 second
- [ ] Registration API responds in < 2 seconds
- [ ] Plans API responds in < 2 seconds
- [ ] Payment API responds in < 2 seconds
- [ ] Dashboard API responds in < 2 seconds

### Background Processing
- [ ] Background jobs complete in reasonable time (< 60 seconds)
- [ ] Scheduler runs without errors
- [ ] No memory leaks in长时间运行 processes
- [ ] Worker processes are stable

---

## 10. DEPLOYMENT

Referensi: [`DEPLOYMENT.md`](DEPLOYMENT.md)

### VPS Infrastructure
- [ ] VPS deployment works (git pull → migrate → build → sync)
- [ ] Docker containers are healthy
- [ ] Nginx is configured correctly
- [ ] SSL/HTTPS is working on `qalcuity.com`
- [ ] Domain DNS resolves correctly

### Services
- [ ] Email SMTP is configured and working
- [ ] Redis is running (cache + queue)
- [ ] Workers are running (default, short, long)
- [ ] Scheduler is running
- [ ] Database (MariaDB/MySQL) is running

### Data Persistence
- [ ] Database is persistent (Docker volume or host mount)
- [ ] Files directory is persistent (`sites/{site}/private/files/`)
- [ ] Backups directory is persistent
- [ ] Logs are accessible

### Deployment Process
- [ ] Git pull inside container works (`docker compose exec backend`)
- [ ] `bench migrate` completes without errors
- [ ] `bench build` completes without errors
- [ ] `bench clear-cache` works
- [ ] `bench restart` restarts all services

---

## 11. ERROR HANDLING

### User-Facing Errors
- [ ] Registration errors show user-friendly messages
- [ ] Payment errors show user-friendly messages
- [ ] Login errors show user-friendly messages
- [ ] Forgot password errors show user-friendly messages
- [ ] Plan selection errors show user-friendly messages

### API Errors
- [ ] API errors return consistent JSON format
- [ ] API errors include error code and message
- [ ] API 401 responses for unauthorized access
- [ ] API 403 responses for forbidden access
- [ ] API 404 responses for not found
- [ ] API 500 responses include request ID for debugging

### System Errors
- [ ] 404 pages show Qalcuity branding (not generic Frappe 404)
- [ ] 500 errors are logged properly
- [ ] JavaScript errors don't break the UI
- [ ] Database errors are handled gracefully
- [ ] File upload errors are handled gracefully

---

## 12. DOCUMENTATION

### Core Documentation
- [ ] [`AGENT.md`](qalcuity/AGENT.md) is up to date
- [ ] [`FEATURES.md`](qalcuity/FEATURES.md) is up to date
- [ ] [`ROADMAP.md`](qalcuity/ROADMAP.md) is up to date
- [ ] [`DEPLOYMENT.md`](DEPLOYMENT.md) is up to date

### Technical Documentation
- [ ] API documentation is accurate and complete
- [ ] Restore procedure is documented — [`RESTORE_PROCEDURE.md`](qalcuity/tests/RESTORE_PROCEDURE.md)
- [ ] Architecture documentation exists
- [ ] Code comments are adequate

### Operational Documentation
- [ ] Backup procedure is documented
- [ ] Monitoring/alerting procedure is documented
- [ ] Incident response procedure is documented
- [ ] Rollback procedure is documented

---

## 13. DATA INTEGRITY & EDGE CASES

### Data Validation
- [ ] Required fields are enforced on all DocTypes
- [ ] Unique constraints prevent duplicate records
- [ ] Foreign key relationships are valid
- [ ] Date fields validate correctly (expiry > start date)

### Concurrent Operations
- [ ] Multiple payment submissions don't create duplicates
- [ ] Concurrent plan changes are handled safely
- [ ] Race conditions in subscription activation are prevented

### State Consistency
- [ ] Subscription status matches tenant status
- [ ] Payment status reflects in subscription status
- [ ] Plan changes reflect in module access immediately
- [ ] Expired subscriptions consistently block access

---

## 14. COMPLIANCE & LICENSING

- [ ] ERPNext/GNU AGPL v3 license is respected
- [ ] Frappe license is respected
- [ ] No proprietary ERPNext trademarks misused
- [ ] Open source attributions are included
- [ ] Customer data handling complies with privacy requirements

---

## VALIDATION COMMANDS

### Run All Tests
```bash
bench --site qalcuity.com run-tests --module qalcuity.qalcuity.tests -v
```

### Run Specific Test Suites
```bash
# Customer Journey (End-to-End)
bench --site qalcuity.com run-tests --module qalcuity.qalcuity.tests.test_customer_journey -v

# Tenant Isolation (Security Audit)
bench --site qalcuity.com run-tests --module qalcuity.qalcuity.tests.test_tenant_isolation -v

# Module Enforcement
bench --site qalcuity.com run-tests --module qalcuity.qalcuity.tests.test_module_enforcement -v

# Backup & Restore
bench --site qalcuity.com run-tests --module qalcuity.qalcuity.tests.test_backup_restore -v
```

### Manual Verification
```bash
# Check site health
bench --site qalcuity.com doctor

# Check background jobs
bench --site qalcuity.com ready-for-production

# Check scheduler status
bench --site qalcuity.com scheduler status

# Check Docker container status
docker compose ps

# Check application logs
bench --site qalcuity.com mariadb console
```

### Quick Smoke Test
```bash
# Verify site is accessible
curl -s -o /dev/null -w "%{http_code}" https://qalcuity.com/

# Verify API health
curl -s https://qalcuity.com/api/v1/health | python -m json.tool
```

---

## SIGN-OFF

| Area | Verified By | Date | Status |
|------|------------|------|--------|
| Customer Journey | | | [ ] |
| Subscription Lifecycle | | | [ ] |
| Tenant Isolation | | | [ ] |
| Module Enforcement | | | [ ] |
| Superadmin | | | [ ] |
| Branding | | | [ ] |
| API | | | [ ] |
| Backup & Recovery | | | [ ] |
| Performance | | | [ ] |
| Deployment | | | [ ] |
| Error Handling | | | [ ] |
| Documentation | | | [ ] |
| Data Integrity | | | [ ] |
| Compliance | | | [ ] |

---

## FINAL DECISION

- [ ] **READY FOR LAUNCH** — All critical items verified
- [ ] **NOT READY** — Blocking issues identified (list below)

### Blocking Issues:

1.
2.
3.

---

## NOTES

### Critical Items (Must-pass before launch)
1. **Tenant Isolation** — Security audit must pass 100%
2. **Backup & Restore** — Both creation and restore must work
3. **Customer Journey** — Full happy path must work end-to-end
4. **Deployment** — Production environment must be stable

### Important Items (Should-pass before launch)
5. **Module Enforcement** — Plan-based access control must work
6. **Branding** — Customer-facing experience must be Qalcuity
7. **Error Handling** — User-facing errors must be friendly
8. **API** — Core API endpoints must be functional

### Nice-to-have (Can be addressed post-launch)
9. **Performance Optimization** — Can be tuned iteratively
10. **Comprehensive Documentation** — Can be expanded over time

---

> **Reminder:** This checklist must be completed and signed off before accepting the first real customer.
>
> Reference: [ROADMAP.md Phase 19](qalcuity/ROADMAP.md:577)
