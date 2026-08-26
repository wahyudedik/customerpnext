# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity ERP — Backup Restore Script
======================================

Script Python untuk restore backup ke fresh site atau existing site.
Digunakan oleh Sprint 11 Task 4 — Backup & Restore Procedure.

Usage:
    # Full restore (database + files)
    python restore_backup.py --site my-site --backup-file /path/to/backup.sql.gz --backup-type full

    # Database only restore
    python restore_backup.py --site my-site --backup-file /path/to/backup.sql.gz --backup-type database

    # Files only restore
    python restore_backup.py --site my-site --backup-file /path/to/files.tar.gz --backup-type files

    # With verification
    python restore_backup.py --site my-site --backup-file /path/to/backup.sql.gz --backup-type full --verify

    # Dry run (validate without executing)
    python restore_backup.py --site my-site --backup-file /path/to/backup.sql.gz --backup-type full --dry-run

Requirements:
    - Frappe bench environment
    - MySQL/MariaDB access
    - SSH access to server (for remote restore)
"""

import os
import sys
import gzip
import tarfile
import subprocess
import argparse
import json
import time
from datetime import datetime


# =============================================================================
# Constants
# =============================================================================

BACKUP_TYPE_FULL = "full"
BACKUP_TYPE_DATABASE = "database"
BACKUP_TYPE_FILES = "files"

DEFAULT_BENCH_PATH = os.path.expanduser("~/frappe-bench")


# =============================================================================
# Core Restore Functions
# =============================================================================

def restore_database(site_name, backup_file, bench_path=None, dry_run=False):
    """
    Restore database from .sql.gz backup file.

    Args:
        site_name: Frappe site name
        backup_file: Path to .sql.gz backup file
        bench_path: Path to Frappe bench directory
        dry_run: If True, validate only without executing

    Returns:
        dict: {success, message, duration_seconds}
    """
    start_time = time.time()

    try:
        # Validate inputs
        if not os.path.exists(backup_file):
            return {
                "success": False,
                "message": "Backup file not found: {0}".format(backup_file),
            }

        # Validate file is valid gzip
        if not _is_valid_gzip(backup_file):
            return {
                "success": False,
                "message": "Backup file is not valid gzip: {0}".format(backup_file),
            }

        # Get file size
        file_size = os.path.getsize(backup_file)
        print("[RESTORE] Database backup file: {0} ({1} bytes)".format(
            backup_file, file_size
        ))

        if dry_run:
            return {
                "success": True,
                "message": "Dry run: database backup file is valid ({0} bytes)".format(file_size),
                "duration_seconds": time.time() - start_time,
            }

        # Method 1: Use bench restore (preferred)
        if bench_path:
            result = _run_bench_restore(site_name, backup_file, bench_path)
            if result["success"]:
                return {
                    "success": True,
                    "message": "Database restored via bench restore",
                    "duration_seconds": time.time() - start_time,
                }

        # Method 2: Direct mysql restore (fallback)
        result = _run_mysql_restore(site_name, backup_file)
        return {
            "success": result["success"],
            "message": result["message"],
            "duration_seconds": time.time() - start_time,
        }

    except Exception as e:
        return {
            "success": False,
            "message": "Database restore failed: {0}".format(str(e)),
            "duration_seconds": time.time() - start_time,
        }


def restore_files(site_name, backup_file, bench_path=None, dry_run=False):
    """
    Restore uploaded files from .tar.gz backup.

    Args:
        site_name: Frappe site name
        backup_file: Path to _files.tar.gz backup file
        bench_path: Path to Frappe bench directory
        dry_run: If True, validate only without executing

    Returns:
        dict: {success, message, duration_seconds}
    """
    start_time = time.time()

    try:
        # Validate inputs
        if not os.path.exists(backup_file):
            return {
                "success": False,
                "message": "Backup file not found: {0}".format(backup_file),
            }

        # Validate file is valid tar.gz
        if not _is_valid_tarball(backup_file):
            return {
                "success": False,
                "message": "Backup file is not valid tar.gz: {0}".format(backup_file),
            }

        # Get file size
        file_size = os.path.getsize(backup_file)
        print("[RESTORE] Files backup: {0} ({1} bytes)".format(backup_file, file_size))

        if dry_run:
            return {
                "success": True,
                "message": "Dry run: files backup is valid ({0} bytes)".format(file_size),
                "duration_seconds": time.time() - start_time,
            }

        # Determine site path
        if bench_path:
            site_path = os.path.join(bench_path, "sites", site_name)
        else:
            # Try to find bench path
            site_path = _find_site_path(site_name)

        if not site_path or not os.path.exists(site_path):
            return {
                "success": False,
                "message": "Site path not found: {0}".format(site_path or "unknown"),
            }

        # Extract tar.gz to site directory
        print("[RESTORE] Extracting files to: {0}".format(site_path))
        cmd = ["tar", "-xzf", backup_file, "-C", site_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

        if result.returncode != 0:
            return {
                "success": False,
                "message": "tar extraction failed: {0}".format(result.stderr),
            }

        # Fix permissions
        print("[RESTORE] Fixing file permissions...")
        _fix_file_permissions(site_path)

        return {
            "success": True,
            "message": "Files restored successfully to {0}".format(site_path),
            "duration_seconds": time.time() - start_time,
        }

    except Exception as e:
        return {
            "success": False,
            "message": "Files restore failed: {0}".format(str(e)),
            "duration_seconds": time.time() - start_time,
        }


def verify_restore(site_name, bench_path=None):
    """
    Verify restore was successful by checking key data.

    Args:
        site_name: Frappe site name
        bench_path: Path to Frappe bench directory

    Returns:
        dict: {success, checks: [{name, passed, message}]}
    """
    checks = []

    # Check 1: Site directory exists
    if bench_path:
        site_path = os.path.join(bench_path, "sites", site_name)
    else:
        site_path = _find_site_path(site_name)

    checks.append({
        "name": "Site directory exists",
        "passed": site_path is not None and os.path.exists(site_path),
        "message": "Site path: {0}".format(site_path or "not found"),
    })

    # Check 2: site_config.json exists
    if site_path:
        config_path = os.path.join(site_path, "site_config.json")
        checks.append({
            "name": "site_config.json exists",
            "passed": os.path.exists(config_path),
            "message": "Config: {0}".format(config_path),
        })

    # Check 3: Database connection (via bench)
    if bench_path:
        try:
            result = subprocess.run(
                ["bench", "--site", site_name, " mariadb", "-e", "SELECT 1;"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=bench_path,
            )
            checks.append({
                "name": "Database connection",
                "passed": result.returncode == 0,
                "message": "Database accessible" if result.returncode == 0 else result.stderr,
            })
        except Exception as e:
            checks.append({
                "name": "Database connection",
                "passed": False,
                "message": "Error: {0}".format(str(e)),
            })

    # Check 4: Qalcuity Backup records exist
    if bench_path:
        try:
            result = subprocess.run(
                [
                    "bench", "--site", site_name, " mariadb", "-e",
                    "SELECT COUNT(*) as cnt FROM `tabQalcuity Backup` WHERE status='Completed';"
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=bench_path,
            )
            if result.returncode == 0:
                # Parse count from output
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    count = int(lines[1].strip())
                    checks.append({
                        "name": "Qalcuity Backup records",
                        "passed": count > 0,
                        "message": "Found {0} completed backup records".format(count),
                    })
                else:
                    checks.append({
                        "name": "Qalcuity Backup records",
                        "passed": False,
                        "message": "Could not parse backup count",
                    })
            else:
                checks.append({
                    "name": "Qalcuity Backup records",
                    "passed": False,
                    "message": "Query failed: {0}".format(result.stderr),
                })
        except Exception as e:
            checks.append({
                "name": "Qalcuity Backup records",
                "passed": False,
                "message": "Error: {0}".format(str(e)),
            })

    # Check 5: Qalcuity Tenant records exist
    if bench_path:
        try:
            result = subprocess.run(
                [
                    "bench", "--site", site_name, " mariadb", "-e",
                    "SELECT COUNT(*) as cnt FROM `tabQalcuity Tenant`;"
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=bench_path,
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    count = int(lines[1].strip())
                    checks.append({
                        "name": "Qalcuity Tenant records",
                        "passed": count > 0,
                        "message": "Found {0} tenant records".format(count),
                    })
                else:
                    checks.append({
                        "name": "Qalcuity Tenant records",
                        "passed": False,
                        "message": "Could not parse tenant count",
                    })
            else:
                checks.append({
                    "name": "Qalcuity Tenant records",
                    "passed": False,
                    "message": "Query failed: {0}".format(result.stderr),
                })
        except Exception as e:
            checks.append({
                "name": "Qalcuity Tenant records",
                "passed": False,
                "message": "Error: {0}".format(str(e)),
            })

    # Check 6: Private files directory
    if site_path:
        private_files = os.path.join(site_path, "private", "files")
        checks.append({
            "name": "Private files directory",
            "passed": os.path.isdir(private_files),
            "message": "Path: {0}".format(private_files),
        })

    # Check 7: Public files directory
    if site_path:
        public_files = os.path.join(site_path, "public", "files")
        checks.append({
            "name": "Public files directory",
            "passed": os.path.isdir(public_files),
            "message": "Path: {0}".format(public_files),
        })

    # Determine overall success
    all_passed = all(c["passed"] for c in checks)
    passed_count = sum(1 for c in checks if c["passed"])
    total_count = len(checks)

    return {
        "success": all_passed,
        "checks": checks,
        "summary": "{0}/{1} checks passed".format(passed_count, total_count),
    }


# =============================================================================
# Internal Helper Functions
# =============================================================================

def _is_valid_gzip(filepath):
    """Check if file is valid gzip format."""
    try:
        with gzip.open(filepath, "rb") as f:
            f.read(1024)  # Read a small chunk to validate
        return True
    except (gzip.BadGzipFile, OSError):
        return False


def _is_valid_tarball(filepath):
    """Check if file is valid tar.gz format."""
    try:
        with tarfile.open(filepath, "r:gz") as tar:
            tar.getmembers()  # List members to validate
        return True
    except (tarfile.TarError, OSError):
        return False


def _run_bench_restore(site_name, backup_file, bench_path):
    """Run restore using Frappe bench CLI."""
    try:
        cmd = ["bench", "--site", site_name, "restore", backup_file]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=7200,  # 2 hour timeout
            cwd=bench_path,
        )

        if result.returncode != 0:
            return {
                "success": False,
                "message": "bench restore failed: {0}".format(result.stderr),
            }

        return {
            "success": True,
            "message": "bench restore completed successfully",
        }

    except Exception as e:
        return {
            "success": False,
            "message": "bench restore error: {0}".format(str(e)),
        }


def _run_mysql_restore(site_name, backup_file):
    """Run restore using direct mysql command."""
    try:
        # Get database credentials from site_config
        site_config = _get_site_config(site_name)
        if not site_config:
            return {
                "success": False,
                "message": "Could not read site_config.json",
            }

        db_password = site_config.get("db_password", "")
        db_host = site_config.get("db_host", "localhost")
        db_port = site_config.get("db_port", "3306")

        # Build mysql command
        cmd = "gunzip -c {0} | mysql -h {1} -P {2} -u root {3}".format(
            backup_file, db_host, db_port, site_name
        )

        if db_password:
            cmd = "gunzip -c {0} | mysql -h {1} -P {2} -u root -p{3} {4}".format(
                backup_file, db_host, db_port, db_password, site_name
            )

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=7200,
        )

        if result.returncode != 0:
            return {
                "success": False,
                "message": "mysql restore failed: {0}".format(result.stderr),
            }

        return {
            "success": True,
            "message": "mysql restore completed successfully",
        }

    except Exception as e:
        return {
            "success": False,
            "message": "mysql restore error: {0}".format(str(e)),
        }


def _get_site_config(site_name):
    """Read site_config.json for database credentials."""
    # Try common bench paths
    bench_paths = [
        DEFAULT_BENCH_PATH,
        os.path.expanduser("~/frappe-bench"),
        "/home/frappe/frappe-bench",
        "/opt/frappe-bench",
    ]

    for bench_path in bench_paths:
        config_path = os.path.join(bench_path, "sites", site_name, "site_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    return json.load(f)
            except Exception:
                continue

    return None


def _find_site_path(site_name):
    """Try to find the site path in common locations."""
    common_paths = [
        os.path.join(DEFAULT_BENCH_PATH, "sites", site_name),
        os.path.expanduser("~/frappe-bench/sites/{0}".format(site_name)),
        "/home/frappe/frappe-bench/sites/{0}".format(site_name),
        "/opt/frappe-bench/sites/{0}".format(site_name),
    ]

    for path in common_paths:
        if os.path.exists(path):
            return path

    return None


def _fix_file_permissions(site_path):
    """Fix file permissions after restore."""
    try:
        # Set reasonable permissions for Frappe files
        private_files = os.path.join(site_path, "private", "files")
        public_files = os.path.join(site_path, "public", "files")

        for directory in [private_files, public_files]:
            if os.path.exists(directory):
                subprocess.run(
                    ["chmod", "-R", "755", directory],
                    capture_output=True,
                    timeout=300,
                )
    except Exception:
        pass  # Non-critical


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Qalcuity ERP — Backup Restore Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full restore
  python restore_backup.py --site my-site --backup-file /path/to/backup.sql.gz --backup-type full

  # Database only
  python restore_backup.py --site my-site --backup-file /path/to/backup.sql.gz --backup-type database

  # Files only
  python restore_backup.py --site my-site --backup-file /path/to/files.tar.gz --backup-type files

  # With verification
  python restore_backup.py --site my-site --backup-file /path/to/backup.sql.gz --backup-type full --verify

  # Dry run
  python restore_backup.py --site my-site --backup-file /path/to/backup.sql.gz --backup-type full --dry-run
        """,
    )

    parser.add_argument(
        "--site", required=True, help="Frappe site name"
    )
    parser.add_argument(
        "--backup-file", required=True, help="Path to backup file"
    )
    parser.add_argument(
        "--backup-type",
        choices=["full", "database", "files"],
        default="full",
        help="Type of backup to restore (default: full)",
    )
    parser.add_argument(
        "--bench-path", default=None, help="Path to Frappe bench directory"
    )
    parser.add_argument(
        "--verify", action="store_true", help="Run verification after restore"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate only, do not execute restore"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Qalcuity ERP — Backup Restore Script")
    print("=" * 60)
    print("Site:         {0}".format(args.site))
    print("Backup file:  {0}".format(args.backup_file))
    print("Backup type:  {0}".format(args.backup_type))
    print("Bench path:   {0}".format(args.bench_path or "auto-detect"))
    print("Verify:       {0}".format(args.verify))
    print("Dry run:      {0}".format(args.dry_run))
    print("=" * 60)

    start_time = time.time()
    results = []

    # Step 1: Pre-restore checks
    print("\n[STEP 1] Pre-restore validation...")
    if not os.path.exists(args.backup_file):
        print("[ERROR] Backup file not found: {0}".format(args.backup_file))
        sys.exit(1)

    # Step 2: Restore database
    if args.backup_type in ("full", "database"):
        print("\n[STEP 2] Restoring database...")
        result = restore_database(
            site_name=args.site,
            backup_file=args.backup_file if args.backup_type == "database" else args.backup_file,
            bench_path=args.bench_path,
            dry_run=args.dry_run,
        )
        results.append(("Database restore", result))
        print("[RESULT] {0}: {1}".format(
            "PASS" if result["success"] else "FAIL",
            result["message"],
        ))

    # Step 3: Restore files
    if args.backup_type in ("full", "files"):
        print("\n[STEP 3] Restoring files...")
        result = restore_files(
            site_name=args.site,
            backup_file=args.backup_file if args.backup_type == "files" else args.backup_file,
            bench_path=args.bench_path,
            dry_run=args.dry_run,
        )
        results.append(("Files restore", result))
        print("[RESULT] {0}: {1}".format(
            "PASS" if result["success"] else "FAIL",
            result["message"],
        ))

    # Step 4: Verification
    if args.verify and not args.dry_run:
        print("\n[STEP 4] Verifying restore...")
        result = verify_restore(
            site_name=args.site,
            bench_path=args.bench_path,
        )
        results.append(("Verification", result))
        print("[RESULT] {0}: {1}".format(
            "PASS" if result["success"] else "FAIL",
            result["summary"],
        ))

        # Print individual checks
        for check in result["checks"]:
            status = "✓" if check["passed"] else "✗"
            print("  {0} {1}: {2}".format(status, check["name"], check["message"]))

    # Summary
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print("RESTORE SUMMARY")
    print("=" * 60)

    all_success = True
    for name, result in results:
        status = "SUCCESS" if result["success"] else "FAILED"
        print("  {0}: {1}".format(name, status))
        if not result["success"]:
            all_success = False

    print("\nTotal time: {0:.1f} seconds".format(total_time))

    if all_success:
        print("\n✓ Restore completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Restore completed with errors!")
        sys.exit(1)


if __name__ == "__main__":
    main()
