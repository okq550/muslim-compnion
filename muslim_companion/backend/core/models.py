"""Core infrastructure models.

Contains models for backup status tracking and other infrastructure operations.
"""

from django.db import models


class BackupStatus(models.Model):
    """
    Track backup task execution status and metadata.

    Implements AC #6 from US-API-006:
    - Record backup status in database
    - Track backup size, duration, checksum
    - Store error messages for failed backups
    - Enable monitoring dashboard queries
    """

    STATUS_CHOICES = [
        ("success", "Success"),
        ("failed", "Failed"),
        ("in_progress", "In Progress"),
    ]

    backup_date = models.DateTimeField(
        help_text="Date/time when backup was initiated",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        help_text="Backup execution status",
    )
    file_size_mb = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Backup file size in megabytes",
    )
    duration_seconds = models.IntegerField(
        help_text="Backup duration in seconds",
    )
    checksum = models.CharField(
        max_length=64,
        help_text="SHA-256 checksum of backup file",
    )
    s3_key = models.CharField(
        max_length=500,
        help_text="S3 object key where backup is stored",
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Error message if backup failed",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when record was created",
    )

    class Meta:
        db_table = "core_backup_status"
        verbose_name = "Backup Status"
        verbose_name_plural = "Backup Statuses"
        ordering = ["-backup_date"]
        indexes = [
            models.Index(fields=["-backup_date"], name="idx_backup_date"),
            models.Index(fields=["status"], name="idx_backup_status"),
        ]

    def __str__(self):
        return f"Backup {self.backup_date.strftime('%Y-%m-%d')} - {self.status}"

    @property
    def is_success(self):
        """Check if backup was successful."""
        return self.status == "success"

    @classmethod
    def get_last_successful_backup(cls):
        """Get the most recent successful backup."""
        return cls.objects.filter(status="success").first()

    @classmethod
    def get_success_rate(cls, days=30):
        """
        Calculate backup success rate for the past N days.

        Args:
            days: Number of days to analyze (default: 30)

        Returns:
            float: Success rate as percentage (0-100)
        """
        from datetime import UTC
        from datetime import datetime
        from datetime import timedelta

        cutoff = datetime.now(UTC) - timedelta(days=days)
        total = cls.objects.filter(backup_date__gte=cutoff).count()

        if total == 0:
            return 0.0

        successful = cls.objects.filter(
            backup_date__gte=cutoff,
            status="success",
        ).count()

        return (successful / total) * 100
