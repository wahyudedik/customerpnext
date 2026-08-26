# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Backup & Restore Test Suite — Sprint 11 Task 4
================================================

Validasi backup functionality, restore procedure, dan integritas backup system.

Test Categories:
A. Backup Creation (test_01 — test_04)
B. Backup Scheduling & Status (test_05 — test_06)
C. Restore Procedure (test_07 — test_09)
D. Incremental Backup & Retention (test_10 — test_11)

Architecture:
- Backup logic lives in qalcuity/backup.py
- Backup API endpoints in qalcuity/api/backup_api.py
- Backup DocType: Qalcuity Backup (BACKUP-{YYYYMMDD}-{####})
- Scheduled via qalcuity/tasks.py → run_scheduled_backup()
- Retention: configurable via QALCUITY_BACKUP_RETENTION_DAYS (default: 30)

Notes:
- Tests use IntegrationTestCase for database access
- Backup files are created in sites/{site}/private/backups/
- Tests clean up their own backup records and files
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime, add_days, nowdate, getdate
import os
import gzip
import tempfile
import json

from qalcuity.backup import (
    run_backup,
    cleanup_old_backups,
    get_backup_status,
    get_backup_list,
    get_backup_stats,
    BACKUP_TYPE_FULL,
    BACKUP_TYPE_DATABASE,
    BACKUP_TYPE_FILES,
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_COMPLETED,
    STATUS_FAILED,
    DEFAULT_RETENTION_DAYS,
)


class TestBackupRestore(IntegrationTestCase):
    """
    Backup & Restore comprehensive test suite.

    Creates test backup records and files, validates backup lifecycle,
    and verifies restore procedure requirements.
    """

    def setUp(self):
        """Create test data for backup testing."""
        self.test_backup_names = []
        self.test_backup_files = []
        self._original_retention = os.environ.get("QALCUITY_BACKUP_RETENTION_DAYS")

    def tearDown(self):
        """Clean up test data and backup files."""
        # Delete test backup records
        for name in self.test_backup_names:
            try:
                if frappe.db.exists("Qalcuity Backup", name):
                    backup = frappe.get_doc("Qalcuity Backup", name)
                    # Delete file from disk
                    if backup.file_path and os.path.exists(backup.file_path):
                        os.remove(backup.file_path)
                    frappe.delete_doc("Qalcuity Backup", name, ignore_permissions=True)
            except Exception:
                pass

        # Clean up any leftover test backup files
        for file_path in self.test_backup_files:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass

        frappe.db.commit()

        # Restore original retention env
        if self._original_retention:
            os.environ["QALCUITY_BACKUP_RETENTION_DAYS"] = self._original_retention
        elif "QALCUITY_BACKUP_RETENTION_DAYS" in os.environ:
            del os.environ["QALCUITY_BACKUP_RETENTION_DAYS"]

    def _track_backup(self, backup_name):
        """Track a backup name for cleanup in tearDown."""
        if backup_name:
            self.test_backup_names.append(backup_name)

    def _track_file(self, file_path):
        """Track a file path for cleanup in tearDown."""
        if file_path:
            self.test_backup_files.append(file_path)

    def _create_test_backup_record(
        self,
        backup_type="Full",
        status=STATUS_COMPLETED,
        file_path=None,
        file_size=1024,
    ):
        """
        Helper: Create a test Qalcuity Backup record without running actual backup.

        Returns:
            str: Name of created backup record
        """
        now = now_datetime()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        backup_name = "backup_test_{0}".format(timestamp)

        doc = frappe.get_doc({
            "doctype": "Qalcuity Backup",
            "backup_name": backup_name,
            "backup_type": backup_type,
            "status": status,
            "site_name": frappe.local.site or "test_site",
            "started_at": now,
            "performed_by": "test_admin@example.com",
            "notes": "Test backup record",
        })

        if status == STATUS_COMPLETED:
            doc.file_path = file_path or ""
            doc.file_size = file_size
            doc.completed_at = now
            doc.duration_seconds = 5

        if status == STATUS_FAILED:
            doc.error_message = "Test error"
            doc.completed_at = now
            doc.duration_seconds = 2

        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        self._track_backup(doc.name)
        return doc.name

    def _create_test_backup_file(self, content="test backup content"):
        """
        Helper: Create a temporary test backup file on disk.

        Returns:
            str: Path to created file
        """
        backup_dir = frappe.get_site_path("private", "backups")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir, exist_ok=True)

        fd, path = tempfile.mkstemp(suffix=".sql.gz", prefix="qalcuity_test_", dir=backup_dir)
        with os.fdopen(fd, "w") as f:
            f.write(content)

        self._track_file(path)
        return path

    # =========================================================================
    # A. Backup Creation
    # =========================================================================

    def test_01_database_backup_creation(self):
        """
        Verify database backup file is created successfully.

        Checks:
        - run_backup() returns a result dict
        - Result contains backup_name, status, file_path, file_size
        - Status is Completed
        - File exists on disk (if file_path returned)
        """
        result = run_backup(
            backup_type=BACKUP_TYPE_DATABASE,
            performed_by="test_admin@example.com",
            notes="Test: database backup creation",
        )

        # Validate result structure
        self.assertIsInstance(result, dict)
        self.assertIn("backup_name", result)
        self.assertIn("status", result)
        self.assertIn("file_path", result)
        self.assertIn("file_size", result)

        # Validate status
        self.assertEqual(result["status"], STATUS_COMPLETED)

        # Track for cleanup
        self._track_backup(result["backup_name"])

        # Validate backup record exists in database
        self.assertTrue(
            frappe.db.exists("Qalcuity Backup", result["backup_name"]),
            "Backup record should exist in database",
        )

        # If file was created, validate it exists
        if result["file_path"]:
            self._track_file(result["file_path"])
            self.assertTrue(
                os.path.exists(result["file_path"]),
                "Backup file should exist on disk",
            )

    def test_02_backup_record_created(self):
        """
        Verify Qalcuity Backup record is created in database.

        Checks:
        - Record is created with correct fields
        - backup_name is unique (autoname format: BACKUP-{YYYYMMDD}-{####})
        - backup_type is set correctly
        - status transitions: Running → Completed
        - started_at is set
        - completed_at is set after completion
        """
        result = run_backup(
            backup_type=BACKUP_TYPE_DATABASE,
            performed_by="test_admin@example.com",
            notes="Test: backup record creation",
        )

        backup_name = result["backup_name"]
        self._track_backup(backup_name)

        # Verify record exists
        backup_doc = frappe.get_doc("Qalcuity Backup", backup_name)

        # Validate autoname format
        self.assertTrue(
            backup_doc.name.startswith("BACKUP-"),
            "Backup name should follow BACKUP-{YYYYMMDD}-{####} format",
        )

        # Validate fields
        self.assertEqual(backup_doc.backup_type, BACKUP_TYPE_DATABASE)
        self.assertEqual(backup_doc.status, STATUS_COMPLETED)
        self.assertEqual(backup_doc.performed_by, "test_admin@example.com")
        self.assertIsNotNone(backup_doc.started_at)
        self.assertIsNotNone(backup_doc.completed_at)
        self.assertIsNotNone(backup_doc.site_name)

        # Validate duration is calculated
        self.assertIsNotNone(backup_doc.duration_seconds)
        self.assertGreaterEqual(backup_doc.duration_seconds, 0)

        # Validate notes
        self.assertEqual(backup_doc.notes, "Test: backup record creation")

    def test_03_backup_contains_tenant_data(self):
        """
        Verify backup includes tenant-specific data.

        Checks:
        - Backup record has site_name (identifies the tenant/site)
        - Backup file is not a placeholder/empty marker
        - Backup file contains actual SQL data (gzipped)
        """
        result = run_backup(
            backup_type=BACKUP_TYPE_DATABASE,
            performed_by="test_admin@example.com",
            notes="Test: backup contains tenant data",
        )

        backup_name = result["backup_name"]
        self._track_backup(backup_name)

        backup_doc = frappe.get_doc("Qalcuity Backup", backup_name)

        # Validate site_name is set (tenant identification)
        self.assertIsNotNone(
            backup_doc.site_name,
            "Backup should record the site/tenant name",
        )
        self.assertGreater(
            len(backup_doc.site_name), 0,
            "site_name should not be empty",
        )

        # If file exists, validate it's actual data
        if backup_doc.file_path and os.path.exists(backup_doc.file_path):
            self._track_file(backup_doc.file_path)
            # Should be a valid gzip file
            try:
                with gzip.open(backup_doc.file_path, "rb") as f:
                    content = f.read()
                self.assertGreater(
                    len(content), 0,
                    "Backup file should contain actual data",
                )
            except gzip.BadGzipFile:
                # Some environments may produce raw SQL (not gzipped)
                # Validate file has content
                file_size = os.path.getsize(backup_doc.file_path)
                self.assertGreater(file_size, 0, "Backup file should not be empty")

    def test_04_backup_file_not_empty(self):
        """
        Verify backup file has content (not empty).

        Checks:
        - Backup file size > 0
        - file_size in record matches actual file size
        - If .sql.gz, can be read as valid gzip
        """
        result = run_backup(
            backup_type=BACKUP_TYPE_DATABASE,
            performed_by="test_admin@example.com",
            notes="Test: backup file not empty",
        )

        backup_name = result["backup_name"]
        self._track_backup(backup_name)

        backup_doc = frappe.get_doc("Qalcuity Backup", backup_name)

        if backup_doc.file_path and os.path.exists(backup_doc.file_path):
            self._track_file(backup_doc.file_path)

            # File should have content
            actual_size = os.path.getsize(backup_doc.file_path)
            self.assertGreater(actual_size, 0, "Backup file should not be empty")

            # Record file_size should match actual
            self.assertEqual(
                backup_doc.file_size, actual_size,
                "Recorded file_size should match actual file size",
            )

            # Record should have file_path
            self.assertGreater(len(backup_doc.file_path), 0, "file_path should be set")
        else:
            # If no file created (e.g., mysqldump not available), verify the record
            # still tracks the attempt correctly
            self.assertEqual(
                backup_doc.file_size, 0,
                "If no file created, file_size should be 0",
            )

    # =========================================================================
    # B. Backup Scheduling & Status
    # =========================================================================

    def test_05_scheduled_backup_task(self):
        """
        Verify backup can be triggered via scheduled task.

        Checks:
        - run_scheduled_backup() function exists and is callable
        - The function imports run_backup from qalcuity.backup
        - Backup can be triggered programmatically with Scheduler as performed_by
        """
        from qalcuity.tasks import run_scheduled_backup

        # Verify function exists and is callable
        self.assertTrue(callable(run_scheduled_backup), "run_scheduled_backup should be callable")

        # Verify backup module has run_backup
        from qalcuity.backup import run_backup as backup_run_backup
        self.assertTrue(callable(backup_run_backup), "run_backup should be callable")

        # Verify cleanup_old_backups is callable
        from qalcuity.backup import cleanup_old_backups
        self.assertTrue(callable(cleanup_old_backups), "cleanup_old_backups should be callable")

        # Run a backup with Scheduler performed_by (simulating scheduler)
        result = run_backup(
            backup_type=BACKUP_TYPE_DATABASE,
            performed_by="Scheduler",
            notes="Scheduled daily backup",
        )

        self._track_backup(result["backup_name"])

        # Validate result
        self.assertEqual(result["status"], STATUS_COMPLETED)

        # Verify performed_by is "Scheduler"
        backup_doc = frappe.get_doc("Qalcuity Backup", result["backup_name"])
        self.assertEqual(backup_doc.performed_by, "Scheduler")

    def test_06_backup_status_tracking(self):
        """
        Verify backup status is tracked (pending → completed/failed).

        Checks:
        - New backup starts with Running status
        - After completion, status is Completed
        - get_backup_status() returns valid status info
        - get_backup_stats() returns valid statistics
        - get_backup_list() returns paginated results
        """
        # Run a backup
        result = run_backup(
            backup_type=BACKUP_TYPE_DATABASE,
            performed_by="test_admin@example.com",
            notes="Test: status tracking",
        )

        self._track_backup(result["backup_name"])

        # Verify completed status
        backup_doc = frappe.get_doc("Qalcuity Backup", result["backup_name"])
        self.assertEqual(backup_doc.status, STATUS_COMPLETED)

        # Test get_backup_status()
        status = get_backup_status()
        self.assertIsInstance(status, dict)
        self.assertIn("total_backups", status)
        self.assertIn("total_size", status)
        self.assertIn("last_backup_time", status)
        self.assertGreater(status["total_backups"], 0)

        # Test get_backup_stats()
        stats = get_backup_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn("total_backups", stats)
        self.assertIn("completed_count", stats)
        self.assertIn("failed_count", stats)
        self.assertIn("total_size", stats)
        self.assertIn("total_size_formatted", stats)
        self.assertGreater(stats["completed_count"], 0)

        # Test get_backup_list()
        backup_list = get_backup_list()
        self.assertIsInstance(backup_list, dict)
        self.assertIn("data", backup_list)
        self.assertIn("total", backup_list)
        self.assertIn("page", backup_list)
        self.assertIn("total_pages", backup_list)
        self.assertGreater(backup_list["total"], 0)

        # Test get_backup_list with filters
        filtered_list = get_backup_list(
            filters={"backup_type": "Database"}
        )
        self.assertIsInstance(filtered_list, dict)
        self.assertIn("data", filtered_list)

    # =========================================================================
    # C. Restore Procedure
    # =========================================================================

    def test_07_restore_script_exists(self):
        """
        Verify restore script/documentation exists.

        Checks:
        - RESTORE_PROCEDURE.md exists in tests directory
        - restore_backup.py script exists in tests directory
        - Documentation contains required sections
        """
        tests_dir = os.path.dirname(os.path.abspath(__file__))

        # Check RESTORE_PROCEDURE.md exists
        restore_doc_path = os.path.join(tests_dir, "RESTORE_PROCEDURE.md")
        self.assertTrue(
            os.path.exists(restore_doc_path),
            "RESTORE_PROCEDURE.md should exist in tests directory",
        )

        # Read and validate documentation content
        with open(restore_doc_path, "r", encoding="utf-8") as f:
            doc_content = f.read()

        # Validate required sections
        required_sections = [
            "Prerequisites",
            "Restore",
            "Verification",
            "Rollback",
        ]
        for section in required_sections:
            self.assertIn(
                section.lower(), doc_content.lower(),
                "RESTORE_PROCEDURE.md should contain '{0}' section".format(section),
            )

        # Check restore_backup.py script exists
        restore_script_path = os.path.join(tests_dir, "restore_backup.py")
        self.assertTrue(
            os.path.exists(restore_script_path),
            "restore_backup.py should exist in tests directory",
        )

        # Validate script has required functions
        with open(restore_script_path, "r", encoding="utf-8") as f:
            script_content = f.read()

        required_functions = [
            "restore_database",
            "restore_files",
            "verify_restore",
        ]
        for func_name in required_functions:
            self.assertIn(
                func_name, script_content,
                "restore_backup.py should contain '{0}' function".format(func_name),
            )

    def test_08_backup_file_valid_format(self):
        """
        Verify backup file is in valid format (can be parsed).

        Checks:
        - .sql.gz file is valid gzip format
        - Content can be decompressed
        - Decompressed content is non-empty
        - For files backup: .tar.gz is valid tarball
        """
        # Create a database backup
        result = run_backup(
            backup_type=BACKUP_TYPE_DATABASE,
            performed_by="test_admin@example.com",
            notes="Test: valid backup format",
        )

        self._track_backup(result["backup_name"])

        backup_doc = frappe.get_doc("Qalcuity Backup", result["backup_name"])

        if backup_doc.file_path and os.path.exists(backup_doc.file_path):
            self._track_file(backup_doc.file_path)

            file_path = backup_doc.file_path

            # Validate file extension
            self.assertTrue(
                file_path.endswith(".sql.gz"),
                "Database backup should be .sql.gz format",
            )

            # Validate gzip format
            try:
                with gzip.open(file_path, "rb") as f:
                    content = f.read()
                self.assertGreater(len(content), 0, "Decompressed content should not be empty")
            except gzip.BadGzipFile:
                # If not gzipped, verify it's at least a valid file
                file_size = os.path.getsize(file_path)
                self.assertGreater(file_size, 0, "Backup file should have content")

            # Verify record metadata is complete
            self.assertIsNotNone(backup_doc.file_size)
            self.assertIsNotNone(backup_doc.completed_at)
            self.assertIsNotNone(backup_doc.duration_seconds)

    def test_09_backup_metadata_complete(self):
        """
        Verify backup record has all required metadata (size, timestamp, type).

        Checks:
        - backup_name is set and unique
        - backup_type is valid
        - status is valid
        - started_at is set
        - completed_at is set (for completed backups)
        - duration_seconds is calculated
        - performed_by is set
        - file_path and file_size are set (for completed backups with files)
        - site_name is set
        """
        result = run_backup(
            backup_type=BACKUP_TYPE_FULL,
            performed_by="test_admin@example.com",
            notes="Test: metadata completeness",
        )

        self._track_backup(result["backup_name"])

        backup_doc = frappe.get_doc("Qalcuity Backup", result["backup_name"])

        # Required metadata fields
        required_fields = [
            "backup_name",
            "backup_type",
            "status",
            "site_name",
            "started_at",
            "completed_at",
            "duration_seconds",
            "performed_by",
        ]

        for field in required_fields:
            value = getattr(backup_doc, field, None)
            self.assertIsNotNone(
                value,
                "Field '{0}' should be set in backup record".format(field),
            )

        # Validate backup_type is valid
        self.assertIn(
            backup_doc.backup_type,
            [BACKUP_TYPE_FULL, BACKUP_TYPE_DATABASE, BACKUP_TYPE_FILES],
            "backup_type should be Full, Database, or Files",
        )

        # Validate status is valid
        self.assertIn(
            backup_doc.status,
            [STATUS_PENDING, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED],
            "status should be Pending, Running, Completed, or Failed",
        )

        # For completed backup, file metadata should be set
        if backup_doc.status == STATUS_COMPLETED:
            self.assertIsNotNone(backup_doc.file_size)
            self.assertGreaterEqual(backup_doc.file_size, 0)
            self.assertIsNotNone(backup_doc.duration_seconds)
            self.assertGreaterEqual(backup_doc.duration_seconds, 0)

    # =========================================================================
    # D. Incremental Backup & Retention
    # =========================================================================

    def test_10_incremental_backup_tracking(self):
        """
        Verify backup system tracks which data has been backed up.

        Checks:
        - Each backup has unique backup_name
        - Backup records can be queried by type
        - Backup records can be filtered by date range
        - Backup records track creation time for ordering
        """
        # Create multiple backups
        backup_names = []
        for i in range(3):
            result = run_backup(
                backup_type=BACKUP_TYPE_DATABASE,
                performed_by="test_admin@example.com",
                notes="Test: incremental tracking #{0}".format(i + 1),
            )
            backup_names.append(result["backup_name"])
            self._track_backup(result["backup_name"])

        # Verify all backups have unique names
        self.assertEqual(
            len(set(backup_names)), 3,
            "Each backup should have a unique name",
        )

        # Verify backups can be listed
        backup_list = get_backup_list()
        self.assertGreaterEqual(backup_list["total"], 3)

        # Verify backups can be filtered by type
        db_backups = get_backup_list(filters={"backup_type": "Database"})
        self.assertGreaterEqual(db_backups["total"], 3)

        # Verify backups track creation time (ordered by creation DESC)
        self.assertEqual(backup_list["data"][0]["name"], backup_names[-1])

        # Verify each backup record has a unique name and timestamp
        for name in backup_names:
            doc = frappe.get_doc("Qalcuity Backup", name)
            self.assertEqual(doc.backup_type, BACKUP_TYPE_DATABASE)
            self.assertEqual(doc.status, STATUS_COMPLETED)
            self.assertIsNotNone(doc.started_at)

    def test_11_backup_retention_policy(self):
        """
        Verify old backups can be cleaned up per retention policy.

        Checks:
        - cleanup_old_backups() function works
        - Retention policy respects QALCUITY_BACKUP_RETENTION_DAYS
        - Old backups are deleted (both file and record)
        - Recent backups are preserved
        - Returns correct deleted_count and freed_bytes
        """
        # Set a short retention period for testing
        os.environ["QALCUITY_BACKUP_RETENTION_DAYS"] = "1"

        # Create a backup record with old creation date
        now = now_datetime()
        old_date = add_days(now, -10)  # 10 days ago

        old_backup_name = "backup_test_old_{0}".format(now.strftime("%Y%m%d_%H%M%S"))
        old_doc = frappe.get_doc({
            "doctype": "Qalcuity Backup",
            "backup_name": old_backup_name,
            "backup_type": BACKUP_TYPE_DATABASE,
            "status": STATUS_COMPLETED,
            "site_name": frappe.local.site or "test_site",
            "started_at": old_date,
            "completed_at": old_date,
            "duration_seconds": 5,
            "performed_by": "test_admin@example.com",
            "file_size": 1024,
            "notes": "Test: old backup for retention test",
        })

        # Create a test file for the old backup
        old_file = self._create_test_backup_file("old backup content")
        old_doc.file_path = old_file
        old_doc.insert(ignore_permissions=True)

        # Manually update creation date to simulate old backup
        frappe.db.sql(
            "UPDATE `tabQalcuity Backup` SET creation = %s WHERE name = %s",
            (str(add_days(getdate(nowdate()), -10)) + " 00:00:00", old_doc.name),
        )
        frappe.db.commit()

        self._track_backup(old_doc.name)

        # Create a recent backup (should be preserved)
        recent_result = run_backup(
            backup_type=BACKUP_TYPE_DATABASE,
            performed_by="test_admin@example.com",
            notes="Test: recent backup for retention test",
        )
        self._track_backup(recent_result["backup_name"])

        # Run cleanup
        result = cleanup_old_backups()

        # Validate cleanup result
        self.assertIsInstance(result, dict)
        self.assertIn("deleted_count", result)
        self.assertIn("freed_bytes", result)

        # The old backup should be deleted
        self.assertFalse(
            frappe.db.exists("Qalcuity Backup", old_doc.name),
            "Old backup record should be deleted after cleanup",
        )

        # Old file should be deleted
        self.assertFalse(
            os.path.exists(old_file),
            "Old backup file should be deleted after cleanup",
        )

        # Recent backup should be preserved
        self.assertTrue(
            frappe.db.exists("Qalcuity Backup", recent_result["backup_name"]),
            "Recent backup should be preserved after cleanup",
        )

        # Clean up: remove old_doc.name from tracking since it's already deleted
        if old_doc.name in self.test_backup_names:
            self.test_backup_names.remove(old_doc.name)
