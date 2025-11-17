"""
Comprehensive tests for backup and recovery system.

Tests cover AC #1-8 from US-API-006:
- Backup service (create, compress, checksum, upload)
- Encryption service (encrypt/decrypt)
- Celery tasks (daily backup, retention policy)
- Recovery service (list, download, restore)
- BackupStatus model
"""

import gzip
import hashlib
import os
import tempfile
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from unittest.mock import patch

import pytest
from moto import mock_kms
from moto import mock_s3

from backend.core.exceptions import IntegrityCheckFailedError
from backend.core.models import BackupStatus
from backend.core.services.backup import BackupService
from backend.core.services.encryption import EncryptionService
from backend.core.services.recovery import RecoveryService

# =============================================================================
# Backup Service Tests (AC #1, #2, #4)
# =============================================================================


@pytest.mark.django_db
class TestBackupService:
    """Test BackupService for database backups."""

    def test_compress_backup_reduces_size(self):
        """Test that gzip compression reduces file size significantly."""
        service = BackupService()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file with repeatable data (highly compressible)
            test_file = os.path.join(temp_dir, "test.sql")
            with open(test_file, "w") as f:
                f.write("SELECT * FROM users;\n" * 1000)  # Repeatable data

            original_size = os.path.getsize(test_file)

            # Compress the file
            compressed_file = service.compress_backup(test_file)
            compressed_size = os.path.getsize(compressed_file)

            # Verify compression worked
            assert compressed_file.endswith(".gz")
            assert compressed_size < original_size
            # Should achieve at least 50% compression on repetitive data
            assert compressed_size < (original_size * 0.5)

    def test_calculate_checksum_sha256(self):
        """Test SHA-256 checksum calculation."""
        service = BackupService()

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            test_data = b"test backup data"
            temp_file.write(test_data)
            temp_file.flush()

            # Calculate checksum
            checksum = service.calculate_checksum(temp_file.name)

            # Verify checksum format and correctness
            assert len(checksum) == 64  # SHA-256 produces 64 hex characters
            expected_checksum = hashlib.sha256(test_data).hexdigest()
            assert checksum == expected_checksum

            os.unlink(temp_file.name)

    def test_get_backup_metadata(self):
        """Test backup metadata collection."""
        service = BackupService()

        metadata = service.get_backup_metadata()

        # Verify metadata structure
        assert "db_name" in metadata
        assert "db_version" in metadata
        assert "timestamp" in metadata
        assert "environment" in metadata

        # Verify timestamp format (ISO 8601)
        assert "T" in metadata["timestamp"]
        assert "Z" in metadata["timestamp"]

    @mock_s3
    def test_upload_to_s3_success(self):
        """Test successful S3 upload with metadata."""
        service = BackupService()

        # Create mock S3 bucket
        import boto3

        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-backups")

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test backup data")
            temp_file.flush()

            # Upload to S3
            s3_key = "production/2025-11-06/db_backup.sql.gz.enc"
            metadata = {"db_name": "postgres", "timestamp": "2025-11-06T00:00:00Z"}
            checksum = "abc123"

            success = service.upload_to_s3(
                local_file=temp_file.name,
                s3_key=s3_key,
                metadata=metadata,
                checksum=checksum,
            )

            assert success is True

            # Verify upload
            objects = s3.list_objects_v2(Bucket="test-backups")
            assert objects["KeyCount"] == 1
            assert objects["Contents"][0]["Key"] == s3_key

            os.unlink(temp_file.name)

    @mock_s3
    def test_verify_upload_integrity_matches(self):
        """Test successful integrity verification."""
        service = BackupService()

        # Create mock S3 bucket
        import boto3

        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-backups")

        # Upload file with checksum metadata
        s3_key = "production/2025-11-06/db_backup.sql.gz.enc"
        expected_checksum = "abc123"

        s3.put_object(
            Bucket="test-backups",
            Key=s3_key,
            Body=b"test data",
            Metadata={"checksum": expected_checksum},
        )

        # Verify integrity
        result = service.verify_upload_integrity(s3_key, expected_checksum)

        assert result is True

    @mock_s3
    def test_verify_upload_integrity_fails_on_mismatch(self):
        """Test integrity verification fails on checksum mismatch."""
        service = BackupService()

        # Create mock S3 bucket
        import boto3

        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-backups")

        # Upload file with checksum metadata
        s3_key = "production/2025-11-06/db_backup.sql.gz.enc"
        stored_checksum = "abc123"

        s3.put_object(
            Bucket="test-backups",
            Key=s3_key,
            Body=b"test data",
            Metadata={"checksum": stored_checksum},
        )

        # Verify with different checksum (should fail)
        with pytest.raises(IntegrityCheckFailedError):
            service.verify_upload_integrity(s3_key, "different_checksum")


# =============================================================================
# Encryption Service Tests (AC #3)
# =============================================================================


@pytest.mark.django_db
class TestEncryptionService:
    """Test EncryptionService for file encryption/decryption."""

    @mock_kms
    def test_encrypt_file_with_kms(self):
        """Test file encryption produces different output."""
        service = EncryptionService()

        # Create mock KMS key
        import boto3

        kms = boto3.client("kms", region_name="us-east-1")
        key_response = kms.create_key(Description="Test backup key")
        key_id = key_response["KeyMetadata"]["KeyId"]

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            original_data = b"sensitive backup data"
            temp_file.write(original_data)
            temp_file.flush()

            # Encrypt file
            encrypted_file = service.encrypt_file(temp_file.name, key_id)

            # Verify encrypted file exists and is different
            assert os.path.exists(encrypted_file)
            assert encrypted_file.endswith(".enc")

            with open(encrypted_file, "rb") as f:
                encrypted_data = f.read()

            assert encrypted_data != original_data

            os.unlink(temp_file.name)
            os.unlink(encrypted_file)

    @mock_kms
    def test_decrypt_file_restores_original(self):
        """Test round-trip encrypt/decrypt restores original data."""
        service = EncryptionService()

        # Create mock KMS key
        import boto3

        kms = boto3.client("kms", region_name="us-east-1")
        key_response = kms.create_key(Description="Test backup key")
        key_id = key_response["KeyMetadata"]["KeyId"]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            original_data = b"sensitive backup data"
            temp_file.write(original_data)
            temp_file.flush()

            # Encrypt file
            encrypted_file = service.encrypt_file(temp_file.name, key_id)

            # Decrypt file
            decrypted_file = service.decrypt_file(encrypted_file, key_id)

            # Verify decrypted data matches original
            with open(decrypted_file, "rb") as f:
                decrypted_data = f.read()

            assert decrypted_data == original_data

            os.unlink(temp_file.name)
            os.unlink(encrypted_file)
            os.unlink(decrypted_file)


# =============================================================================
# Recovery Service Tests (AC #5, #8)
# =============================================================================


@pytest.mark.django_db
class TestRecoveryService:
    """Test RecoveryService for database restoration."""

    @mock_s3
    def test_list_available_backups(self):
        """Test listing available backups from S3."""
        service = RecoveryService()

        # Create mock S3 bucket with backups
        import boto3

        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-backups")

        # Upload test backups
        for i in range(5):
            date = (datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
            s3_key = f"production/{date}/db_backup.sql.gz.enc"
            s3.put_object(Bucket="test-backups", Key=s3_key, Body=b"test data")

        # List backups
        backups = service.list_available_backups(days=7)

        # Verify
        assert len(backups) == 5
        assert all("date" in b for b in backups)
        assert all("size_mb" in b for b in backups)
        assert all("s3_key" in b for b in backups)

        # Verify sorted by date (newest first)
        dates = [b["date"] for b in backups]
        assert dates == sorted(dates, reverse=True)

    @mock_s3
    def test_download_backup(self):
        """Test downloading backup from S3."""
        service = RecoveryService()

        # Create mock S3 bucket
        import boto3

        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-backups")

        # Upload test backup
        s3_key = "production/2025-11-06/db_backup.sql.gz.enc"
        test_data = b"test backup data"
        s3.put_object(Bucket="test-backups", Key=s3_key, Body=test_data)

        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = os.path.join(temp_dir, "downloaded_backup.enc")

            # Download backup
            result_path = service.download_backup(s3_key, local_path)

            # Verify
            assert result_path == local_path
            assert os.path.exists(local_path)

            with open(local_path, "rb") as f:
                downloaded_data = f.read()

            assert downloaded_data == test_data

    def test_decompress_backup(self):
        """Test decompressing gzipped backup."""
        service = RecoveryService()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create compressed file
            original_data = b"SELECT * FROM users;"
            gz_file = os.path.join(temp_dir, "backup.sql.gz")

            with gzip.open(gz_file, "wb") as f:
                f.write(original_data)

            # Decompress
            output_file = os.path.join(temp_dir, "backup.sql")
            result_path = service.decompress_backup(gz_file, output_file)

            # Verify
            assert result_path == output_file
            assert os.path.exists(output_file)

            with open(output_file, "rb") as f:
                decompressed_data = f.read()

            assert decompressed_data == original_data


# =============================================================================
# BackupStatus Model Tests (AC #6)
# =============================================================================


@pytest.mark.django_db
class TestBackupStatusModel:
    """Test BackupStatus model for backup tracking."""

    def test_backup_status_creation(self):
        """Test creating backup status record."""
        backup_status = BackupStatus.objects.create(
            backup_date=datetime.now(UTC),
            status="success",
            file_size_mb=150.5,
            duration_seconds=300,
            checksum="abc123",
            s3_key="production/2025-11-06/db_backup.sql.gz.enc",
            error_message=None,
        )

        assert backup_status.is_success is True
        assert backup_status.status == "success"

    def test_get_last_successful_backup(self):
        """Test retrieving last successful backup."""
        # Create multiple backups
        for i in range(3):
            BackupStatus.objects.create(
                backup_date=datetime.now(UTC) - timedelta(days=i),
                status="success",
                file_size_mb=100.0,
                duration_seconds=200,
                checksum=f"checksum{i}",
                s3_key=f"production/backup_{i}.enc",
            )

        last_backup = BackupStatus.get_last_successful_backup()

        assert last_backup is not None
        assert last_backup.status == "success"

    def test_get_success_rate(self):
        """Test calculating backup success rate."""
        # Create 7 successful and 3 failed backups in past 30 days
        for i in range(7):
            BackupStatus.objects.create(
                backup_date=datetime.now(UTC) - timedelta(days=i),
                status="success",
                file_size_mb=100.0,
                duration_seconds=200,
                checksum=f"checksum{i}",
                s3_key=f"production/backup_{i}.enc",
            )

        for i in range(3):
            BackupStatus.objects.create(
                backup_date=datetime.now(UTC) - timedelta(days=i + 10),
                status="failed",
                file_size_mb=0.0,
                duration_seconds=50,
                checksum="",
                s3_key="",
                error_message="Test failure",
            )

        success_rate = BackupStatus.get_success_rate(days=30)

        assert success_rate == 70.0  # 7 out of 10 = 70%


# =============================================================================
# Celery Tasks Tests (AC #1, #6, #7)
# =============================================================================


@pytest.mark.django_db
class TestCeleryBackupTasks:
    """Test Celery backup tasks."""

    @mock_s3
    @mock_kms
    @patch("backend.core.services.backup.BackupService._execute_pg_dump")
    def test_daily_backup_task_executes(self, mock_pg_dump):
        """Test daily backup task runs end-to-end."""
        from backend.core.tasks import run_daily_backup

        # Mock pg_dump to create a fake backup file
        def create_fake_backup(output_file):
            with open(output_file, "w") as f:
                f.write("-- PostgreSQL database dump\n" * 100)

        mock_pg_dump.side_effect = create_fake_backup

        # Create mock S3 bucket and KMS key
        import boto3

        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="quran-backend-backups-production")

        kms = boto3.client("kms", region_name="us-east-1")
        kms.create_key(
            Description="Test backup key",
            KeyId="alias/quran-backend-backup-key",
        )

        # Execute task
        result = run_daily_backup()

        # Verify task completed successfully
        assert result["status"] == "success"
        assert "backup_size_mb" in result
        assert "s3_key" in result
        assert "checksum" in result

        # Verify backup status was recorded in database
        backup_status = BackupStatus.objects.last()
        assert backup_status is not None
        assert backup_status.status == "success"

    @mock_s3
    def test_retention_policy_deletes_old_backups(self):
        """Test retention policy deletes backups older than 30 days."""
        # Create mock S3 bucket
        import boto3

        from backend.core.tasks import enforce_backup_retention_policy

        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="quran-backend-backups-production")

        # Create old backups (should be deleted)
        for i in range(35, 40):  # 35-39 days old (beyond 30-day retention)
            date = (datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
            s3_key = f"production/{date}/db_backup.sql.gz.enc"
            s3.put_object(
                Bucket="quran-backend-backups-production",
                Key=s3_key,
                Body=b"old backup",
            )

        # Create recent backups (should be kept)
        for i in range(5):  # 0-4 days old (within 30-day retention)
            date = (datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
            s3_key = f"production/{date}/db_backup.sql.gz.enc"
            s3.put_object(
                Bucket="quran-backend-backups-production",
                Key=s3_key,
                Body=b"recent backup",
            )

        # Run retention policy
        result = enforce_backup_retention_policy()

        # Verify old backups were deleted
        assert result["status"] == "success"
        assert result["deleted_count"] == 5  # 5 old backups deleted

        # Verify recent backups still exist
        objects = s3.list_objects_v2(Bucket="quran-backend-backups-production")
        assert objects["KeyCount"] == 5  # Only recent backups remain
