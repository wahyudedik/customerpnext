# Qalcuity ERP — Backup Restore Procedure

> **Sprint 11 Task 4** — Documented restore procedure for Qalcuity ERP backup system.
>
> **Last Updated:** 2026-08-26

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Backup File Locations](#backup-file-locations)
4. [Restore Procedure](#restore-procedure)
   - [Full Restore (Database + Files)](#full-restore-database--files)
   - [Database Only Restore](#database-only-restore)
   - [Files Only Restore](#files-only-restore)
5. [Verification Steps](#verification-steps)
6. [Rollback Plan](#rollback-plan)
7. [Troubleshooting](#troubleshooting)
8. [Automation](#automation)

---

## Overview

Qalcuity ERP uses Frappe Framework with ERPNext as its core engine. Backup system produces:

- **Database backup:** `.sql.gz` (mysqldump + gzip)
- **Files backup:** `_files.tar.gz` (tar + gzip of private/files and public/files)
- **Backup metadata:** Qalcuity Backup DocType records (BACKUP-{YYYYMMDD}-{####})

Backup files are stored in: `sites/{site_name}/private/backups/`

---

## Prerequisites

### Required Access

- [ ] SSH access to the VPS server
- [ ] Root or sudo access
- [ ] Access to Frappe bench directory
- [ ] MySQL/MariaDB root access (or credentials from site_config.json)

### Required Tools

- [ ] `mysql` client (MariaDB/MySQL)
- [ ] `gzip` (pre-installed on most Linux)
- [ ] `tar` (pre-installed on most Linux)
- [ ] `bench` CLI (Frappe bench command)
- [ ] Sufficient disk space for restored data

### Pre-Restore Checklist

- [ ] Identify the correct backup file to restore
- [ ] Verify backup file integrity (not corrupted)
- [ ] Stop all workers before restore
- [ ] Take a current backup as safety net
- [ ] Notify team about maintenance window

---

## Backup File Locations

```
sites/{site_name}/
├── private/
│   ├── backups/
│   │   ├── backup_{site}_{timestamp}.sql.gz          # Database backup
│   │   ├── backup_{site}_{timestamp}_files.tar.gz    # Files backup
│   │   └── ...
│   └── files/                                        # Private uploaded files
└── public/
    └── files/                                        # Public uploaded files
```

### Backup Record Location (Database)

Qalcuity Backup records are stored in the `tabQalcuity Backup` table with fields:

| Field | Description |
|-------|-------------|
| `name` | Backup ID (BACKUP-{YYYYMMDD}-{####}) |
| `backup_name` | Unique backup identifier |
| `backup_type` | Full / Database / Files |
| `status` | Pending / Running / Completed / Failed |
| `file_path` | Path to backup file on disk |
| `file_size` | File size in bytes |
| `started_at` | Backup start timestamp |
| `completed_at` | Backup completion timestamp |
| `duration_seconds` | Backup duration |
| `site_name` | Site/tenant identifier |
| `performed_by` | User or "Scheduler" |
| `error_message` | Error details (if failed) |

---

## Restore Procedure

### Full Restore (Database + Files)

Complete restore of both database and uploaded files.

#### Step 1: Stop Services

```bash
# SSH into server
ssh user@qalcuity-server

# Navigate to bench directory
cd /home/user/frappe-bench

# Stop workers
bench --site {site_name} set-config maintenance_mode 1
sudo supervisorctl stop all
```

#### Step 2: Create Safety Backup

```bash
# Create a current backup before restore
bench --site {site_name} backup --with-files
```

#### Step 3: Restore Database

```bash
# Identify the database backup file
BACKUP_FILE="sites/{site_name}/private/backups/backup_{site}_{timestamp}.sql.gz"

# Decompress and restore
gunzip -c {BACKUP_FILE} | mysql -u root -p{password} {site_name}
```

Alternatively, using Frappe's built-in restore:

```bash
bench --site {site_name} restore {BACKUP_FILE}
```

#### Step 4: Restore Files

```bash
# Identify the files backup
FILES_BACKUP="sites/{site_name}/private/backups/backup_{site}_{timestamp}_files.tar.gz"

# Extract files backup
cd sites/{site_name}
tar -xzf {FILES_BACKUP} -C .
cd ../..
```

#### Step 5: Run Migrations

```bash
bench --site {site_name} migrate
bench --site {site_name} clear-cache
bench --site {site_name} build
```

#### Step 6: Restart Services

```bash
bench --site {site_name} set-config maintenance_mode 0
sudo supervisorctl start all
```

---

### Database Only Restore

When only the database needs to be restored (files are intact).

```bash
# Stop services
bench --site {site_name} set-config maintenance_mode 1
sudo supervisorctl stop all

# Restore database
BACKUP_FILE="sites/{site_name}/private/backups/backup_{site}_{timestamp}.sql.gz"
gunzip -c {BACKUP_FILE} | mysql -u root -p{password} {site_name}

# Or using bench
bench --site {site_name} restore {BACKUP_FILE}

# Run migrations
bench --site {site_name} migrate
bench --site {site_name} clear-cache

# Restart services
bench --site {site_name} set-config maintenance_mode 0
sudo supervisorctl start all
```

---

### Files Only Restore

When only uploaded files need to be restored (database is intact).

```bash
# Stop web workers only (database can remain accessible)
sudo supervisorctl stop frappe-web:*

# Extract files
FILES_BACKUP="sites/{site_name}/private/backups/backup_{site}_{timestamp}_files.tar.gz"
cd sites/{site_name}
tar -xzf {FILES_BACKUP} -C .

# Fix permissions
cd ../..
bench --site {site_name} set-permissions

# Restart workers
sudo supervisorctl start frappe-web:*
```

---

## Verification Steps

After restore, verify the following:

### 1. Database Integrity

```bash
# Check Qalcuity Backup records exist
bench --site {site_name} mariadb -e "SELECT COUNT(*) FROM \`tabQalcuity Backup\` WHERE status='Completed';"

# Check tenant records
bench --site {site_name} mariadb -e "SELECT name, status FROM \`tabQalcuity Tenant\`;"

# Check subscription records
bench --site {site_name} mariadb -e "SELECT name, status FROM \`tabQalcuity Subscription\`;"

# Check ERPNext core data
bench --site {site_name} mariadb -e "SELECT COUNT(*) FROM \`tabCustomer\`;"
bench --site {site_name} mariadb -e "SELECT COUNT(*) FROM \`tabSales Invoice\`;"
```

### 2. Application Health

```bash
# Test web access
curl -s -o /dev/null -w "%{http_code}" https://{site_name}/api/method/qalcuity.api.health_api.ping

# Check background workers
sudo supervisorctl status

# Check scheduler
bench --site {site_name} doctor
```

### 3. File Integrity

```bash
# Check private files
ls -la sites/{site_name}/private/files/ | head -20

# Check public files
ls -la sites/{site_name}/public/files/ | head -20

# Check backup directory
ls -la sites/{site_name}/private/backups/
```

### 4. Tenant Isolation

```bash
# Verify tenant data isolation
bench --site {site_name} mariadb -e "
  SELECT tenant_id, COUNT(*) as record_count
  FROM \`tabQalcuity Tenant\`
  GROUP BY tenant_id;
"
```

### 5. Functional Tests

```bash
# Run Qalcuity test suite
bench --site {site_name} run-tests --app qalcuity
```

---

## Rollback Plan

If restore fails or data is corrupted:

### Option 1: Restore from Safety Backup

```bash
# Use the safety backup created before restore
bench --site {site_name} restore sites/{site_name}/private/backups/safety_backup_{timestamp}.sql.gz
bench --site {site_name} migrate
bench --site {site_name} set-config maintenance_mode 0
sudo supervisorctl start all
```

### Option 2: Restore from Last Known Good Backup

```bash
# Find the last known good backup
ls -lt sites/{site_name}/private/backups/*.sql.gz | head -5

# Restore from the identified backup
bench --site {site_name} restore {last_good_backup}
bench --site {site_name} migrate
bench --site {site_name} set-config maintenance_mode 0
sudo supervisorctl start all
```

### Option 3: Database Point-in-Time Recovery

```bash
# If binary logs are enabled
mysqlbinlog --start-datetime="2026-08-26 00:00:00" \
            --stop-datetime="2026-08-26 12:00:00" \
            /var/log/mysql/mysql-bin.* | mysql -u root -p {site_name}
```

### Rollback Verification

```bash
# After rollback, verify
bench --site {site_name} mariadb -e "SELECT COUNT(*) FROM \`tabUser\`;"
curl -s https://{site_name}/api/method/qalcuity.api.health_api.ping
sudo supervisorctl status
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `Access denied for user 'root'` | Check MySQL password in `sites/{site_name}/site_config.json` |
| `Table doesn't exist` | Run `bench --site {site_name} migrate` |
| `File not found` | Verify backup file path and check disk space |
| `Gzip error` | Backup file may be corrupted, try another backup |
| `Workers not starting` | Check supervisor logs: `sudo supervisorctl tail frappe-web:*` |
| `Maintenance mode stuck` | Run `bench --site {site_name} set-config maintenance_mode 0` |

### Disk Space Check

```bash
# Check available disk space
df -h

# Check backup directory size
du -sh sites/{site_name}/private/backups/
```

### Log Locations

```bash
# Frappe error logs
tail -f sites/{site_name}/logs/frappe.log

# Qalcuity backup logs (in error log)
bench --site {site_name} mariadb -e "
  SELECT creation, title, message FROM \`tabError Log\`
  WHERE title LIKE '%Qalcuity Backup%'
  ORDER BY creation DESC LIMIT 10;
"
```

---

## Automation

### Automated Restore Script

Use the companion restore script:

```bash
python qalcuity/qalcuity/tests/restore_backup.py \
  --site {site_name} \
  --backup-file {path_to_backup} \
  --backup-type full \
  --verify
```

### Scheduled Backups (Already Configured)

Qalcuity runs daily backups via Frappe scheduler:

```
scheduler_events:
  daily:
    - qalcuity.tasks.run_scheduled_backup
```

This performs:
1. Full backup (database + files)
2. Cleanup of old backups (retention: 30 days default)

### Backup Retention Configuration

```bash
# Set custom retention period (in days)
export QALCUITY_BACKUP_RETENTION_DAYS=60

# Or in site_config.json
bench --site {site_name} set-config backup_retention_days 60
```

---

## Quick Reference Commands

```bash
# List available backups
ls -lt sites/{site_name}/private/backups/*.sql.gz

# Check backup records
bench --site {site_name} mariadb -e "
  SELECT name, backup_type, status, file_size, completed_at
  FROM \`tabQalcuity Backup\`
  ORDER BY creation DESC LIMIT 10;
"

# Trigger manual backup
bench --site {site_name} execute qalcuity.backup.run_backup --kwargs '{"backup_type": "Full"}'

# Trigger cleanup
bench --site {site_name} execute qalcuity.backup.cleanup_old_backups
```

---

*This document is part of Sprint 11 Task 4 — Backup & Restore Procedure for Qalcuity ERP.*
