"""Celery tasks for core infrastructure operations.

This module contains background tasks for cache warming, health checks,
backup/recovery, and other infrastructure maintenance operations.
"""

import logging
import os
import shutil
from datetime import UTC
from datetime import datetime

import sentry_sdk
from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(
    name="quran_backend.core.warm_quran_cache",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def warm_quran_cache(self) -> dict[str, any]:
    """Celery task to warm the cache with frequently accessed content.

    This task runs on a schedule (daily at 1:00 AM UTC) to refresh
    cached static content and ensure optimal performance.

    Scheduled in config/settings/base.py CELERY_BEAT_SCHEDULE.

    Returns:
        Dictionary with task execution status:
        {
            "status": "success" | "failed",
            "message": str,
            "items_cached": int
        }

    Example schedule configuration (add to base.py):
        CELERY_BEAT_SCHEDULE = {
            'warm-cache-daily': {
                'task': 'quran_backend.core.warm_quran_cache',
                'schedule': crontab(hour=1, minute=0),  # 1:00 AM UTC daily
            },
        }
    """
    try:
        logger.info("Starting scheduled cache warming task")

        # Call the management command programmatically
        # This ensures we reuse the same logic and avoid duplication
        call_command("warm_cache", content_types=["all"], verbosity=1)

        logger.info("Cache warming task completed successfully")

        return {
            "status": "success",
            "message": "Cache warming completed",
        }

    except Exception as e:
        logger.error(f"Cache warming task failed: {e}", exc_info=True)

        # Retry the task if it fails (max 3 attempts)
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(
                "Cache warming task failed after maximum retries. "
                "Manual intervention may be required.",
            )
            return {
                "status": "failed",
                "message": f"Cache warming failed: {e}",
            }


@shared_task(name="quran_backend.core.check_cache_health")
def check_cache_health_task() -> dict[str, any]:
    """Celery task to check cache health and report metrics.

    Can be scheduled to run periodically for monitoring purposes.

    Returns:
        Dictionary with cache health status
    """
    try:
        from quran_backend.core.health import check_cache_health

        health_status = check_cache_health()

        # Log warning if cache is degraded or unavailable
        if health_status["status"] == "degraded":
            logger.warning(
                f"Cache health degraded: {health_status['details']}, "
                f"latency: {health_status['latency_ms']}ms",
            )
        elif health_status["status"] == "unavailable":
            logger.error(f"Cache unavailable: {health_status['details']}")
        else:
            logger.info(
                f"Cache health check passed (latency: {health_status['latency_ms']}ms)",
            )

        return health_status

    except Exception as e:
        logger.error(f"Cache health check task failed: {e}", exc_info=True)
        return {
            "status": "error",
            "details": f"Health check failed: {e}",
        }


@shared_task(name="quran_backend.core.log_cache_metrics")
def log_cache_metrics_task() -> dict[str, any]:
    """Celery task to collect and log cache metrics to Sentry.

    Should be scheduled to run periodically (e.g., every hour)
    for continuous cache performance monitoring.

    Returns:
        Dictionary with collected metrics
    """
    try:
        from quran_backend.core.metrics import CacheMetrics

        # Collect all metrics
        metrics = CacheMetrics.get_all_metrics()

        # Log to Sentry
        CacheMetrics.log_metrics_to_sentry()

        logger.info(
            f"Cache metrics logged: "
            f"Hit ratio: {metrics['hit_ratio']['hit_ratio']:.2%}, "
            f"Memory: {metrics['memory']['usage_percent']:.2f}%",
        )

        return {
            "status": "success",
            "metrics": metrics,
        }

    except Exception as e:
        logger.error(f"Cache metrics logging task failed: {e}", exc_info=True)
        return {
            "status": "error",
            "details": f"Metrics logging failed: {e}",
        }


# =============================================================================
# Backup Tasks (US-API-006)
# =============================================================================


@shared_task(
    name="quran_backend.core.run_daily_backup",
    bind=True,
    max_retries=1,
    default_retry_delay=1800,  # 30 minutes
)
def run_daily_backup(self) -> dict:
    """
    Celery task to run automated daily database backup.

    Implements AC #1, #6 from US-API-006:
    - Daily backups at 2:00 AM UTC via Celery Beat
    - Full backup process: dump, compress, encrypt, upload to S3
    - Verify integrity after upload
    - Log success/failure to Sentry
    - Retry once on failure, alert on critical failure

    Scheduled in config/settings/base.py CELERY_BEAT_SCHEDULE:
        CELERY_BEAT_SCHEDULE = {
            'daily-database-backup': {
                'task': 'quran_backend.core.run_daily_backup',
                'schedule': crontab(hour=2, minute=0),  # 2:00 AM UTC daily
            },
        }

    Returns:
        dict: {
            'status': 'success' | 'failed',
            'message': str,
            'backup_size_mb': float,
            'duration_seconds': float,
            's3_key': str,
            'checksum': str
        }
    """
    from quran_backend.core.services.backup import BackupService
    from quran_backend.core.services.encryption import EncryptionService

    backup_start = datetime.now(UTC)
    temp_dir = None

    try:
        logger.info("Starting daily database backup task")

        # Step 1: Create backup service and initiate backup
        backup_service = BackupService()
        backup_result = backup_service.create_backup()

        if not backup_result["success"]:
            raise Exception("Backup creation failed")

        temp_dir = backup_result["temp_dir"]
        compressed_file = backup_result["backup_file"]
        checksum = backup_result["checksum"]
        metadata = backup_result["metadata"]

        # Step 2: Encrypt backup
        encryption_service = EncryptionService()
        encrypted_file = encryption_service.encrypt_file(compressed_file)

        # Step 3: Upload to S3
        s3_key = backup_service.generate_s3_key()
        backup_service.upload_to_s3(
            local_file=encrypted_file,
            s3_key=s3_key,
            metadata=metadata,
            checksum=checksum,
        )

        # Step 4: Verify upload integrity
        backup_service.verify_upload_integrity(s3_key, checksum)

        # Step 5: Record backup status in database
        from quran_backend.core.models import BackupStatus

        BackupStatus.objects.create(
            backup_date=backup_start,
            status="success",
            file_size_mb=backup_result["size_mb"],
            duration_seconds=backup_result["duration_seconds"],
            checksum=checksum,
            s3_key=s3_key,
            error_message=None,
        )

        # Step 6: Log success to Sentry
        sentry_sdk.capture_message(
            f"Daily backup completed successfully: {backup_result['size_mb']:.2f} MB",
            level="info",
            extra={
                "component": "backup",
                "operation": "daily_backup",
                "backup_size_mb": backup_result["size_mb"],
                "duration_seconds": backup_result["duration_seconds"],
                "s3_key": s3_key,
                "checksum": checksum,
            },
        )

        logger.info(
            f"Daily backup completed successfully: "
            f"{backup_result['size_mb']:.2f} MB uploaded to {s3_key}",
        )

        # Cleanup temporary directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

        return {
            "status": "success",
            "message": "Backup completed successfully",
            "backup_size_mb": backup_result["size_mb"],
            "duration_seconds": backup_result["duration_seconds"],
            "s3_key": s3_key,
            "checksum": checksum,
        }

    except Exception as e:
        logger.error(f"Daily backup task failed: {e}", exc_info=True)

        # Record backup failure in database
        try:
            from quran_backend.core.models import BackupStatus

            BackupStatus.objects.create(
                backup_date=backup_start,
                status="failed",
                file_size_mb=0,
                duration_seconds=(datetime.now(UTC) - backup_start).total_seconds(),
                checksum="",
                s3_key="",
                error_message=str(e)[:500],  # Limit error message length
            )
        except Exception as db_error:
            logger.error(f"Failed to record backup failure: {db_error}")

        # Log failure to Sentry with CRITICAL severity
        sentry_sdk.capture_exception(
            e,
            level="critical",
            extra={
                "component": "backup",
                "operation": "daily_backup",
                "error": str(e),
            },
        )

        # Cleanup temporary directory on failure
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

        # Retry the task if it fails (max 1 retry)
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(
                "Daily backup failed after maximum retries. "
                "Critical alert sent. Manual intervention required.",
            )

            # Send critical alert (PagerDuty via Sentry integration)
            sentry_sdk.capture_message(
                "CRITICAL: Daily backup failed after all retries",
                level="critical",
                extra={
                    "component": "backup",
                    "operation": "daily_backup",
                    "error": str(e),
                    "retry_count": self.request.retries,
                },
            )

            return {
                "status": "failed",
                "message": f"Backup failed: {e}",
                "backup_size_mb": 0,
                "duration_seconds": (datetime.now(UTC) - backup_start).total_seconds(),
                "s3_key": "",
                "checksum": "",
            }


@shared_task(
    name="quran_backend.core.enforce_backup_retention_policy",
    bind=True,
)
def enforce_backup_retention_policy(self) -> dict:
    """
    Celery task to enforce backup retention policy.

    Implements AC #7 from US-API-006:
    - Delete daily backups older than 30 days
    - Keep Sunday backups for 90 days
    - Keep 1st-of-month backups for 1 year
    - Automated cleanup removes expired backups

    Scheduled in config/settings/base.py CELERY_BEAT_SCHEDULE:
        CELERY_BEAT_SCHEDULE = {
            'weekly-backup-cleanup': {
                'task': 'quran_backend.core.enforce_backup_retention_policy',
                'schedule': crontab(hour=3, minute=0, day_of_week=1),  # Monday 3:00 AM
            },
        }

    Returns:
        dict: {
            'status': 'success' | 'failed',
            'message': str,
            'deleted_count': int,
            'reclaimed_space_mb': float
        }
    """

    import boto3
    from botocore.exceptions import ClientError
    from django.conf import settings

    try:
        logger.info("Starting backup retention policy enforcement")

        s3_bucket = getattr(
            settings, "BACKUP_S3_BUCKET", "quran-backend-backups-production"
        )
        environment = getattr(settings, "ENVIRONMENT_NAME", "production")

        retention_days_daily = getattr(settings, "BACKUP_RETENTION_DAYS_DAILY", 30)
        retention_days_weekly = getattr(settings, "BACKUP_RETENTION_DAYS_WEEKLY", 90)
        retention_days_monthly = getattr(settings, "BACKUP_RETENTION_DAYS_MONTHLY", 365)

        s3_client = boto3.client("s3")

        # Get current date for comparison
        now = datetime.now(UTC)

        # List all backups in S3 bucket for this environment
        prefix = f"{environment}/"
        response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=prefix)

        if "Contents" not in response:
            logger.info("No backups found in S3 bucket")
            return {
                "status": "success",
                "message": "No backups to clean up",
                "deleted_count": 0,
                "reclaimed_space_mb": 0,
            }

        deleted_count = 0
        reclaimed_space = 0
        backups_to_delete = []

        for obj in response["Contents"]:
            s3_key = obj["Key"]
            size_bytes = obj["Size"]

            # Extract date from key format: {environment}/{YYYY-MM-DD}/db_backup.sql.gz.enc
            try:
                date_str = s3_key.split("/")[1]  # Extract YYYY-MM-DD
                backup_date = datetime.strptime(date_str, "%Y-%m-%d").replace(
                    tzinfo=UTC
                )
            except (IndexError, ValueError):
                logger.warning(f"Skipping backup with invalid key format: {s3_key}")
                continue

            # Calculate age in days
            age_days = (now - backup_date).days

            # Determine if backup should be deleted
            should_delete = False

            # Rule 1: Keep 1st-of-month backups for 1 year
            if backup_date.day == 1:
                if age_days > retention_days_monthly:
                    should_delete = True
                    logger.info(
                        f"Monthly backup expired: {s3_key} (age: {age_days} days, "
                        f"retention: {retention_days_monthly} days)",
                    )

            # Rule 2: Keep Sunday backups for 90 days
            elif backup_date.weekday() == 6:  # Sunday = 6
                if age_days > retention_days_weekly:
                    should_delete = True
                    logger.info(
                        f"Weekly backup expired: {s3_key} (age: {age_days} days, "
                        f"retention: {retention_days_weekly} days)",
                    )

            # Rule 3: Delete daily backups older than 30 days
            elif age_days > retention_days_daily:
                should_delete = True
                logger.info(
                    f"Daily backup expired: {s3_key} (age: {age_days} days, "
                    f"retention: {retention_days_daily} days)",
                )

            if should_delete:
                backups_to_delete.append((s3_key, size_bytes))

        # Delete expired backups
        for s3_key, size_bytes in backups_to_delete:
            try:
                s3_client.delete_object(Bucket=s3_bucket, Key=s3_key)
                deleted_count += 1
                reclaimed_space += size_bytes
                logger.info(f"Deleted expired backup: {s3_key}")
            except ClientError as e:
                logger.error(f"Failed to delete backup {s3_key}: {e}")

        reclaimed_space_mb = reclaimed_space / (1024 * 1024)

        logger.info(
            f"Backup retention policy enforced: {deleted_count} backups deleted, "
            f"{reclaimed_space_mb:.2f} MB reclaimed",
        )

        # Log to Sentry
        sentry_sdk.capture_message(
            f"Backup retention policy enforced: {deleted_count} backups deleted",
            level="info",
            extra={
                "component": "backup",
                "operation": "retention_policy",
                "deleted_count": deleted_count,
                "reclaimed_space_mb": reclaimed_space_mb,
            },
        )

        return {
            "status": "success",
            "message": "Retention policy enforced successfully",
            "deleted_count": deleted_count,
            "reclaimed_space_mb": reclaimed_space_mb,
        }

    except Exception as e:
        logger.error(f"Backup retention policy enforcement failed: {e}", exc_info=True)

        sentry_sdk.capture_exception(
            e,
            extra={
                "component": "backup",
                "operation": "retention_policy",
            },
        )

        return {
            "status": "failed",
            "message": f"Retention policy enforcement failed: {e}",
            "deleted_count": 0,
            "reclaimed_space_mb": 0,
        }
