"""
Backup Service for automated database backups.

Implements AC #1, #2, #4 from US-API-006:
- Automated database backups via pg_dump
- Comprehensive data coverage (all tables)
- Backup compression and checksum calculation
- S3 upload with metadata

Part of Epic 1 - Cross-Cutting / Infrastructure Stories
"""

import gzip
import hashlib
import logging
import os
import shutil
import subprocess
import tempfile
from datetime import UTC
from datetime import datetime

import boto3
import sentry_sdk
from botocore.exceptions import ClientError
from django.conf import settings

from backend.core.exceptions import BackupFailedError
from backend.core.exceptions import IntegrityCheckFailedError
from backend.core.utils.retry import retry_with_exponential_backoff

logger = logging.getLogger(__name__)


class BackupService:
    """
    Service for creating and managing database backups.

    Handles:
    - PostgreSQL database dumps via pg_dump
    - Gzip compression for storage efficiency
    - SHA-256 checksum calculation for integrity verification
    - S3 upload with metadata
    - Upload integrity verification
    """

    def __init__(self):
        """Initialize backup service with database and S3 configuration."""
        self.db_config = settings.DATABASES["default"]
        self.s3_bucket = getattr(
            settings,
            "BACKUP_S3_BUCKET",
            "quran-backend-backups-production",
        )
        self.kms_key_id = getattr(
            settings,
            "BACKUP_KMS_KEY_ID",
            "alias/quran-backend-backup-key",
        )
        self.s3_client = boto3.client("s3")
        self.environment = getattr(settings, "ENVIRONMENT_NAME", "production")

    def create_backup(self) -> dict:
        """
        Orchestrate full backup process.

        Steps:
        1. Execute pg_dump to create SQL backup
        2. Compress backup with gzip
        3. Calculate SHA-256 checksum
        4. Collect backup metadata
        5. Return backup info (caller handles encryption & upload)

        Returns:
            dict: {
                'success': bool,
                'backup_file': str (path to compressed backup),
                'checksum': str (SHA-256 hash),
                'size_mb': float,
                'metadata': dict (DB version, timestamp, etc.)
            }

        Raises:
            BackupFailedError: If backup process fails
        """
        backup_start = datetime.now(UTC)
        temp_dir = None

        try:
            # Create temporary directory for backup files
            temp_dir = tempfile.mkdtemp(prefix="quran_backup_")
            logger.info(f"Starting database backup in temporary directory: {temp_dir}")

            # Step 1: Create database dump
            dump_file = os.path.join(temp_dir, "db_backup.sql")
            self._execute_pg_dump(dump_file)

            # Step 2: Compress backup
            compressed_file = self.compress_backup(dump_file)

            # Step 3: Calculate checksum
            checksum = self.calculate_checksum(compressed_file)

            # Step 4: Get backup metadata
            metadata = self.get_backup_metadata()

            # Calculate file size
            size_bytes = os.path.getsize(compressed_file)
            size_mb = size_bytes / (1024 * 1024)

            # Calculate duration
            duration_seconds = (datetime.now(UTC) - backup_start).total_seconds()

            logger.info(
                f"Backup created successfully: {size_mb:.2f} MB, "
                f"checksum: {checksum[:16]}..., duration: {duration_seconds:.1f}s",
            )

            return {
                "success": True,
                "backup_file": compressed_file,
                "checksum": checksum,
                "size_mb": size_mb,
                "duration_seconds": duration_seconds,
                "metadata": metadata,
                "temp_dir": temp_dir,  # Caller is responsible for cleanup
            }

        except subprocess.CalledProcessError as e:
            # pg_dump execution failed
            logger.error(
                f"Database dump failed: {e.stderr if hasattr(e, 'stderr') else str(e)}",
            )
            sentry_sdk.capture_exception(
                e,
                extra={
                    "component": "backup",
                    "operation": "pg_dump",
                    "db_host": self.db_config.get("HOST", "localhost"),
                    "db_name": self.db_config.get("NAME", "postgres"),
                },
            )
            raise BackupFailedError(f"Database dump failed: {e!s}") from e

        except OSError as e:
            # File system errors (disk full, permissions, etc.)
            logger.error(f"Backup file operation failed: {e!s}")
            sentry_sdk.capture_exception(
                e,
                extra={
                    "component": "backup",
                    "operation": "file_io",
                    "temp_dir": temp_dir,
                },
            )
            # Clean up on failure
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise BackupFailedError(f"Backup file operation failed: {e!s}") from e

        except Exception as e:
            # Unexpected errors
            logger.error(f"Unexpected error during backup: {e!s}")
            sentry_sdk.capture_exception(
                e,
                extra={
                    "component": "backup",
                    "operation": "create_backup",
                },
            )
            # Clean up on failure
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise BackupFailedError(f"Backup failed: {e!s}") from e

    def _execute_pg_dump(self, output_file: str) -> None:
        """
        Execute pg_dump to create PostgreSQL database backup.

        Args:
            output_file: Path where SQL dump should be saved

        Raises:
            subprocess.CalledProcessError: If pg_dump command fails
        """
        # Extract database connection parameters
        db_name = self.db_config.get("NAME", "postgres")
        db_user = self.db_config.get("USER", "postgres")
        db_host = self.db_config.get("HOST", "localhost")
        db_port = self.db_config.get("PORT", "5432")
        db_password = self.db_config.get("PASSWORD", "")

        # Build pg_dump command
        # --clean: Add DROP statements before CREATE
        # --if-exists: Use IF EXISTS with DROP statements (prevents errors)
        # --create: Include CREATE DATABASE statement
        # --no-owner: Don't set object ownership (portable)
        # --no-acl: Don't dump access privileges
        cmd = [
            "pg_dump",
            f"--host={db_host}",
            f"--port={db_port}",
            f"--username={db_user}",
            f"--dbname={db_name}",
            "--format=plain",  # Plain SQL format
            "--clean",  # Add DROP statements
            "--if-exists",  # Prevent errors if objects don't exist
            "--no-owner",  # Don't set ownership
            "--no-acl",  # Don't dump privileges
            f"--file={output_file}",
        ]

        # Set PGPASSWORD environment variable for authentication
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password

        logger.info(
            f"Executing pg_dump: host={db_host}, port={db_port}, "
            f"database={db_name}, user={db_user}",
        )

        try:
            # Execute pg_dump with timeout (max 30 minutes for large databases)
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minutes
                check=True,
            )

            # Log success
            file_size = os.path.getsize(output_file)
            logger.info(
                f"pg_dump completed successfully: {file_size / (1024 * 1024):.2f} MB",
            )

            # Log any warnings from pg_dump (they go to stderr even on success)
            if result.stderr:
                logger.warning(f"pg_dump warnings: {result.stderr}")

        except subprocess.TimeoutExpired as e:
            logger.error(f"pg_dump timed out after {e.timeout} seconds")
            raise BackupFailedError(
                f"Database dump timed out after {e.timeout} seconds",
            ) from e

        except subprocess.CalledProcessError as e:
            # pg_dump failed - log detailed error
            logger.error(
                f"pg_dump failed with exit code {e.returncode}. "
                f"stderr: {e.stderr}, stdout: {e.stdout}",
            )
            raise

    def compress_backup(self, file_path: str) -> str:
        """
        Compress backup file with gzip.

        Args:
            file_path: Path to uncompressed backup file

        Returns:
            str: Path to compressed file (file_path + '.gz')

        Raises:
            OSError: If compression fails
        """
        compressed_file = f"{file_path}.gz"
        logger.info(f"Compressing backup: {file_path} -> {compressed_file}")

        try:
            with open(file_path, "rb") as f_in:
                with gzip.open(compressed_file, "wb", compresslevel=9) as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Log compression ratio
            original_size = os.path.getsize(file_path)
            compressed_size = os.path.getsize(compressed_file)
            ratio = (1 - (compressed_size / original_size)) * 100

            logger.info(
                f"Compression complete: {original_size / (1024 * 1024):.2f} MB -> "
                f"{compressed_size / (1024 * 1024):.2f} MB ({ratio:.1f}% reduction)",
            )

            # Remove original uncompressed file to save space
            os.remove(file_path)

            return compressed_file

        except OSError as e:
            logger.error(f"Compression failed: {e!s}")
            raise

    def calculate_checksum(self, file_path: str) -> str:
        """
        Calculate SHA-256 checksum of file.

        Args:
            file_path: Path to file

        Returns:
            str: Hexadecimal SHA-256 hash

        Raises:
            OSError: If file cannot be read
        """
        logger.info(f"Calculating SHA-256 checksum for: {file_path}")

        sha256_hash = hashlib.sha256()

        try:
            with open(file_path, "rb") as f:
                # Read in chunks to handle large files efficiently
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)

            checksum = sha256_hash.hexdigest()
            logger.info(f"Checksum calculated: {checksum}")
            return checksum

        except OSError as e:
            logger.error(f"Failed to calculate checksum: {e!s}")
            raise

    def get_backup_metadata(self) -> dict:
        """
        Collect backup metadata.

        Returns:
            dict: {
                'db_name': str,
                'db_version': str,
                'timestamp': str (ISO 8601),
                'environment': str,
            }
        """
        from django.db import connection

        # Get PostgreSQL version
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            db_version = cursor.fetchone()[0]

        return {
            "db_name": self.db_config.get("NAME", "postgres"),
            "db_version": db_version,
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "environment": self.environment,
        }

    @retry_with_exponential_backoff(max_retries=3, delays=(2.0, 4.0, 8.0))
    def upload_to_s3(
        self,
        local_file: str,
        s3_key: str,
        metadata: dict,
        checksum: str,
    ) -> bool:
        """
        Upload backup file to S3 with metadata.

        Args:
            local_file: Path to local backup file
            s3_key: S3 object key (path in bucket)
            metadata: Backup metadata dict
            checksum: SHA-256 checksum of file

        Returns:
            bool: True if upload succeeded

        Raises:
            BackupFailedError: If upload fails after retries
        """
        logger.info(f"Uploading backup to S3: s3://{self.s3_bucket}/{s3_key}")

        try:
            # Prepare S3 metadata (must be strings)
            s3_metadata = {
                "checksum": checksum,
                "db-name": metadata.get("db_name", ""),
                "timestamp": metadata.get("timestamp", ""),
                "environment": metadata.get("environment", ""),
            }

            # Upload file with server-side encryption (SSE-KMS)
            file_size = os.path.getsize(local_file)

            with open(local_file, "rb") as f:
                self.s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=s3_key,
                    Body=f,
                    Metadata=s3_metadata,
                    ServerSideEncryption="aws:kms",
                    SSEKMSKeyId=self.kms_key_id,
                    StorageClass="STANDARD_IA",  # Infrequent Access (cost-effective)
                )

            logger.info(
                f"Upload complete: {file_size / (1024 * 1024):.2f} MB uploaded to "
                f"s3://{self.s3_bucket}/{s3_key}",
            )

            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(
                f"S3 upload failed: {error_code} - {error_message}. "
                f"Bucket: {self.s3_bucket}, Key: {s3_key}",
            )

            sentry_sdk.capture_exception(
                e,
                extra={
                    "component": "backup",
                    "operation": "s3_upload",
                    "bucket": self.s3_bucket,
                    "key": s3_key,
                    "error_code": error_code,
                },
            )

            raise BackupFailedError(f"S3 upload failed: {error_message}") from e

        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {e!s}")
            sentry_sdk.capture_exception(
                e,
                extra={
                    "component": "backup",
                    "operation": "s3_upload",
                    "bucket": self.s3_bucket,
                    "key": s3_key,
                },
            )
            raise BackupFailedError(f"S3 upload failed: {e!s}") from e

    def verify_upload_integrity(self, s3_key: str, expected_checksum: str) -> bool:
        """
        Verify uploaded backup integrity by comparing checksums.

        Args:
            s3_key: S3 object key
            expected_checksum: Expected SHA-256 checksum

        Returns:
            bool: True if checksums match

        Raises:
            IntegrityCheckFailedError: If checksums don't match
            BackupFailedError: If S3 metadata retrieval fails
        """
        logger.info(f"Verifying upload integrity for: s3://{self.s3_bucket}/{s3_key}")

        try:
            # Get object metadata from S3
            response = self.s3_client.head_object(Bucket=self.s3_bucket, Key=s3_key)

            # Extract checksum from metadata
            s3_metadata = response.get("Metadata", {})
            stored_checksum = s3_metadata.get("checksum", "")

            if not stored_checksum:
                logger.error("No checksum found in S3 metadata")
                raise IntegrityCheckFailedError("No checksum found in S3 metadata")

            # Compare checksums
            if stored_checksum != expected_checksum:
                logger.error(
                    f"Checksum mismatch! Expected: {expected_checksum}, "
                    f"Got: {stored_checksum}",
                )

                sentry_sdk.capture_message(
                    "Backup integrity check failed - checksum mismatch",
                    level="critical",
                    extra={
                        "component": "backup",
                        "operation": "integrity_check",
                        "s3_key": s3_key,
                        "expected_checksum": expected_checksum,
                        "stored_checksum": stored_checksum,
                    },
                )

                raise IntegrityCheckFailedError(
                    f"Checksum mismatch: expected {expected_checksum}, "
                    f"got {stored_checksum}",
                )

            logger.info(
                f"Integrity check passed: checksum {expected_checksum[:16]}... verified",
            )
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(
                f"Failed to retrieve S3 metadata: {error_code} - {error_message}",
            )

            sentry_sdk.capture_exception(
                e,
                extra={
                    "component": "backup",
                    "operation": "verify_integrity",
                    "bucket": self.s3_bucket,
                    "key": s3_key,
                    "error_code": error_code,
                },
            )

            raise BackupFailedError(
                f"Failed to verify upload integrity: {error_message}",
            ) from e

    def generate_s3_key(self, date: datetime | None = None) -> str:
        """
        Generate S3 object key for backup.

        Format: {environment}/{date}/db_backup.sql.gz.enc

        Args:
            date: Backup date (defaults to now)

        Returns:
            str: S3 object key
        """
        if date is None:
            date = datetime.now(UTC)

        date_str = date.strftime("%Y-%m-%d")
        return f"{self.environment}/{date_str}/db_backup.sql.gz.enc"
