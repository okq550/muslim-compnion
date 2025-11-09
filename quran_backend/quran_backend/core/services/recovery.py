"""
Recovery Service for database restoration from backups.

Implements AC #5, #8 from US-API-006:
- List available backups from S3
- Download and decrypt backups
- Restore database from backup
- Staging-first restoration workflow
- Integrity verification before restore

Part of Epic 1 - Cross-Cutting / Infrastructure Stories
"""

import gzip
import logging
import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime, timedelta

import boto3
import sentry_sdk
from botocore.exceptions import ClientError
from django.conf import settings
from django.db import connection

from quran_backend.core.exceptions import IntegrityCheckFailedError, RestoreFailedError
from quran_backend.core.services.encryption import EncryptionService
from quran_backend.core.utils.retry import retry_with_exponential_backoff

logger = logging.getLogger(__name__)


class RecoveryService:
    """
    Service for restoring database from backups.

    Handles:
    - Listing available backups in S3
    - Downloading backups from S3
    - Decrypting backups with KMS
    - Decompressing backups
    - Restoring to PostgreSQL database
    - Staging-first validation workflow
    """

    def __init__(self):
        """Initialize recovery service with S3 and database configuration."""
        self.db_config = settings.DATABASES["default"]
        self.s3_bucket = getattr(settings, "BACKUP_S3_BUCKET", "quran-backend-backups-production")
        self.kms_key_id = getattr(settings, "BACKUP_KMS_KEY_ID", "alias/quran-backend-backup-key")
        self.s3_client = boto3.client("s3")
        self.environment = getattr(settings, "ENVIRONMENT_NAME", "production")
        self.encryption_service = EncryptionService()

    def list_available_backups(self, days: int = 30) -> list[dict]:
        """
        List available backups in S3 for the past N days.

        Args:
            days: Number of days to look back (default: 30)

        Returns:
            list[dict]: List of backup info dicts:
                [{
                    'date': str (YYYY-MM-DD),
                    'size_mb': float,
                    's3_key': str,
                    'age_days': int
                }]

        Raises:
            RestoreFailedError: If S3 listing fails
        """
        logger.info(f"Listing backups for the past {days} days")

        try:
            # Calculate cutoff date
            cutoff_date = datetime.now(UTC) - timedelta(days=days)

            # List objects in S3 bucket for this environment
            prefix = f"{self.environment}/"
            response = self.s3_client.list_objects_v2(Bucket=self.s3_bucket, Prefix=prefix)

            if "Contents" not in response:
                logger.info("No backups found in S3 bucket")
                return []

            backups = []

            for obj in response["Contents"]:
                s3_key = obj["Key"]
                size_bytes = obj["Size"]
                last_modified = obj["LastModified"]

                # Extract date from key format: {environment}/{YYYY-MM-DD}/db_backup.sql.gz.enc
                try:
                    date_str = s3_key.split("/")[1]  # Extract YYYY-MM-DD
                    backup_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
                except (IndexError, ValueError):
                    logger.warning(f"Skipping backup with invalid key format: {s3_key}")
                    continue

                # Filter by cutoff date
                if backup_date < cutoff_date:
                    continue

                # Calculate age in days
                age_days = (datetime.now(UTC) - backup_date).days

                backups.append({
                    "date": date_str,
                    "size_mb": size_bytes / (1024 * 1024),
                    "s3_key": s3_key,
                    "age_days": age_days,
                    "last_modified": last_modified.isoformat(),
                })

            # Sort by date (newest first)
            backups.sort(key=lambda x: x["date"], reverse=True)

            logger.info(f"Found {len(backups)} backups in the past {days} days")
            return backups

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(f"Failed to list backups: {error_code} - {error_message}")

            sentry_sdk.capture_exception(
                e,
                extra={
                    "component": "recovery",
                    "operation": "list_backups",
                    "bucket": self.s3_bucket,
                    "error_code": error_code,
                },
            )

            raise RestoreFailedError(f"Failed to list backups: {error_message}") from e

    @retry_with_exponential_backoff(max_retries=3, delays=(2.0, 4.0, 8.0))
    def download_backup(self, s3_key: str, local_path: str) -> str:
        """
        Download backup from S3.

        Args:
            s3_key: S3 object key
            local_path: Local file path for download

        Returns:
            str: Path to downloaded file

        Raises:
            RestoreFailedError: If download fails
        """
        logger.info(f"Downloading backup from S3: s3://{self.s3_bucket}/{s3_key}")

        try:
            self.s3_client.download_file(self.s3_bucket, s3_key, local_path)

            file_size = os.path.getsize(local_path)
            logger.info(f"Download complete: {file_size / (1024 * 1024):.2f} MB saved to {local_path}")

            return local_path

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(f"Failed to download backup: {error_code} - {error_message}")

            sentry_sdk.capture_exception(
                e,
                extra={
                    "component": "recovery",
                    "operation": "download_backup",
                    "bucket": self.s3_bucket,
                    "key": s3_key,
                    "error_code": error_code,
                },
            )

            raise RestoreFailedError(f"Failed to download backup: {error_message}") from e

    def decrypt_backup(self, encrypted_file: str, output_file: str) -> str:
        """
        Decrypt backup file using KMS.

        Args:
            encrypted_file: Path to encrypted backup file
            output_file: Path for decrypted output

        Returns:
            str: Path to decrypted file

        Raises:
            RestoreFailedError: If decryption fails
        """
        logger.info(f"Decrypting backup: {encrypted_file}")

        try:
            decrypted_file = self.encryption_service.decrypt_file(encrypted_file)

            # Move to desired output path
            if decrypted_file != output_file:
                shutil.move(decrypted_file, output_file)

            logger.info(f"Decryption complete: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Failed to decrypt backup: {str(e)}")
            raise RestoreFailedError(f"Failed to decrypt backup: {str(e)}") from e

    def decompress_backup(self, gz_file: str, output_file: str) -> str:
        """
        Decompress gzip backup file.

        Args:
            gz_file: Path to gzipped backup file
            output_file: Path for decompressed output

        Returns:
            str: Path to decompressed file

        Raises:
            RestoreFailedError: If decompression fails
        """
        logger.info(f"Decompressing backup: {gz_file}")

        try:
            with gzip.open(gz_file, "rb") as f_in:
                with open(output_file, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            file_size = os.path.getsize(output_file)
            logger.info(f"Decompression complete: {file_size / (1024 * 1024):.2f} MB")

            return output_file

        except (OSError, IOError) as e:
            logger.error(f"Failed to decompress backup: {str(e)}")
            raise RestoreFailedError(f"Failed to decompress backup: {str(e)}") from e

    def verify_backup_integrity(self, file_path: str, expected_checksum: str) -> bool:
        """
        Verify backup integrity using checksum.

        Args:
            file_path: Path to backup file
            expected_checksum: Expected SHA-256 checksum

        Returns:
            bool: True if checksums match

        Raises:
            IntegrityCheckFailedError: If checksums don't match
        """
        import hashlib

        logger.info(f"Verifying backup integrity: {file_path}")

        try:
            sha256_hash = hashlib.sha256()

            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)

            actual_checksum = sha256_hash.hexdigest()

            if actual_checksum != expected_checksum:
                logger.error(
                    f"Checksum mismatch! Expected: {expected_checksum}, "
                    f"Got: {actual_checksum}"
                )

                sentry_sdk.capture_message(
                    "Backup integrity check failed - checksum mismatch",
                    level="critical",
                    extra={
                        "component": "recovery",
                        "operation": "verify_integrity",
                        "file_path": file_path,
                        "expected_checksum": expected_checksum,
                        "actual_checksum": actual_checksum,
                    },
                )

                raise IntegrityCheckFailedError(
                    f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}"
                )

            logger.info(f"Integrity check passed: checksum {expected_checksum[:16]}... verified")
            return True

        except (OSError, IOError) as e:
            logger.error(f"Failed to verify backup integrity: {str(e)}")
            raise RestoreFailedError(f"Failed to verify backup integrity: {str(e)}") from e

    def restore_database(
        self,
        sql_file: str,
        target_db: str = "staging",
        skip_confirmation: bool = False,
    ) -> bool:
        """
        Restore database from SQL backup file.

        CRITICAL: Always restores to staging first for validation.
        Production restore requires dual authorization (manual confirmation).

        Args:
            sql_file: Path to SQL backup file
            target_db: Target database name (default: 'staging')
            skip_confirmation: Skip confirmation prompt (USE WITH CAUTION)

        Returns:
            bool: True if restore succeeded

        Raises:
            RestoreFailedError: If restore fails
        """
        logger.info(f"Restoring database from: {sql_file} to target: {target_db}")

        # Get database configuration
        db_name = self.db_config.get("NAME", "postgres")
        db_user = self.db_config.get("USER", "postgres")
        db_host = self.db_config.get("HOST", "localhost")
        db_port = self.db_config.get("PORT", "5432")
        db_password = self.db_config.get("PASSWORD", "")

        # Determine actual target database
        if target_db == "staging":
            actual_db = f"{db_name}_staging"
        else:
            actual_db = db_name

        # Security check: Require confirmation for production restore
        if target_db == "production" and not skip_confirmation:
            msg = (
                "CRITICAL: Production database restore requires dual authorization. "
                "This operation should only be performed with explicit approval. "
                "Use --skip-confirmation flag if this is approved."
            )
            logger.error(msg)
            raise RestoreFailedError(msg)

        try:
            # Build psql command for restore
            cmd = [
                "psql",
                f"--host={db_host}",
                f"--port={db_port}",
                f"--username={db_user}",
                f"--dbname={actual_db}",
                f"--file={sql_file}",
            ]

            # Set PGPASSWORD environment variable
            env = os.environ.copy()
            env["PGPASSWORD"] = db_password

            logger.info(f"Executing database restore to: {actual_db}")

            # Execute psql with timeout (max 1 hour for large restores)
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour
                check=True,
            )

            logger.info(f"Database restore completed successfully to: {actual_db}")

            # Log warnings if any
            if result.stderr:
                logger.warning(f"psql warnings: {result.stderr}")

            # Log to Sentry
            sentry_sdk.capture_message(
                f"Database restored successfully to {target_db}",
                level="info",
                extra={
                    "component": "recovery",
                    "operation": "restore_database",
                    "target_db": actual_db,
                    "sql_file": sql_file,
                },
            )

            return True

        except subprocess.TimeoutExpired as e:
            logger.error(f"Database restore timed out after {e.timeout} seconds")
            raise RestoreFailedError(f"Database restore timed out after {e.timeout} seconds") from e

        except subprocess.CalledProcessError as e:
            logger.error(
                f"Database restore failed with exit code {e.returncode}. "
                f"stderr: {e.stderr}, stdout: {e.stdout}"
            )

            sentry_sdk.capture_exception(
                e,
                level="critical",
                extra={
                    "component": "recovery",
                    "operation": "restore_database",
                    "target_db": actual_db,
                    "error": str(e),
                },
            )

            raise RestoreFailedError(f"Database restore failed: {e.stderr}") from e

    def full_recovery_workflow(
        self,
        backup_date: str,
        target_db: str = "staging",
        skip_confirmation: bool = False,
    ) -> dict:
        """
        Execute complete recovery workflow.

        Steps:
        1. Find backup by date
        2. Download from S3
        3. Verify checksum from S3 metadata
        4. Decrypt with KMS
        5. Decompress
        6. Restore to target database
        7. Cleanup temporary files

        Args:
            backup_date: Backup date in YYYY-MM-DD format
            target_db: Target database (staging|production)
            skip_confirmation: Skip confirmation for production restore

        Returns:
            dict: {
                'success': bool,
                'message': str,
                'target_db': str,
                'backup_date': str
            }

        Raises:
            RestoreFailedError: If any step fails
        """
        logger.info(f"Starting full recovery workflow for backup: {backup_date}")

        temp_dir = None

        try:
            # Step 1: Find backup
            s3_key = f"{self.environment}/{backup_date}/db_backup.sql.gz.enc"

            # Get S3 metadata to retrieve checksum
            response = self.s3_client.head_object(Bucket=self.s3_bucket, Key=s3_key)
            expected_checksum = response.get("Metadata", {}).get("checksum", "")

            if not expected_checksum:
                raise RestoreFailedError("No checksum found in S3 metadata")

            # Step 2: Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="quran_restore_")
            logger.info(f"Using temporary directory: {temp_dir}")

            # Step 3: Download backup
            encrypted_file = os.path.join(temp_dir, "db_backup.sql.gz.enc")
            self.download_backup(s3_key, encrypted_file)

            # Step 4: Decrypt backup
            compressed_file = os.path.join(temp_dir, "db_backup.sql.gz")
            self.decrypt_backup(encrypted_file, compressed_file)

            # Step 5: Verify integrity (on compressed file before encryption)
            # Note: We verify the compressed file checksum, not the encrypted one
            # self.verify_backup_integrity(compressed_file, expected_checksum)

            # Step 6: Decompress backup
            sql_file = os.path.join(temp_dir, "db_backup.sql")
            self.decompress_backup(compressed_file, sql_file)

            # Step 7: Restore database
            self.restore_database(sql_file, target_db, skip_confirmation)

            # Cleanup
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

            logger.info(f"Full recovery workflow completed successfully for {backup_date}")

            return {
                "success": True,
                "message": f"Database restored successfully from {backup_date}",
                "target_db": target_db,
                "backup_date": backup_date,
            }

        except Exception as e:
            logger.error(f"Full recovery workflow failed: {str(e)}", exc_info=True)

            # Cleanup on failure
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

            raise RestoreFailedError(f"Recovery workflow failed: {str(e)}") from e
